from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class Employee(models.Model):
    _inherit = 'hr.employee'

    xyz_location_id = fields.Many2one('stock.location', domain=[('usage', '=', 'internal')], string='Truck stock location', groups='hr.group_hr_user')


class Booking(models.Model):
    _inherit = 'xyz.booking'

    def _xyz_order_lines(self):
        lines = super()._xyz_order_lines()
        labor = self.env.ref('xyz_service_stock_billing.product_labor').product_variant_id
        lines.append(fields.Command.create({'product_id': labor.id, 'product_uom_qty': self.product_id.xyz_expected_hours or 2}))
        return lines


class Material(models.Model):
    _name = 'xyz.material'
    _description = 'Actual service material'

    task_id = fields.Many2one('project.task', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', required=True, domain=[('type', '=', 'consu'), ('is_storable', '=', True)])
    quantity = fields.Float(required=True, default=1)
    cost = fields.Float(readonly=True, copy=False)
    move_id = fields.Many2one('stock.move', readonly=True, copy=False)
    company_id = fields.Many2one(related='task_id.company_id', store=True)

    @api.constrains('quantity', 'product_id')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0 or not line.product_id.is_storable:
                raise ValidationError(_('Use positive quantities of tracked goods.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if {'move_id', 'cost'}.intersection(vals) and not self.env.su:
                raise AccessError(_('Stock evidence is managed by the system.'))
            task = self.env['project.task'].browse(vals.get('task_id'))
            task._xyz_lock()
            if task.xyz_state in ('done', 'cancel'):
                raise UserError(_('Cannot change materials on closed jobs.'))
        return super().create(vals_list)

    def write(self, vals):
        self.mapped('task_id')._xyz_lock()
        if any(line.task_id.xyz_state in ('done', 'cancel') for line in self):
            raise UserError(_('Accepted materials are immutable.'))
        if {'task_id', 'move_id', 'cost'}.intersection(vals) and not self.env.su:
            raise AccessError(_('Material ownership and stock evidence are managed by the system.'))
        return super().write(vals)

    def unlink(self):
        self.mapped('task_id')._xyz_lock()
        if any(line.task_id.xyz_state in ('done', 'cancel') for line in self):
            raise UserError(_('Accepted materials are immutable.'))
        return super().unlink()


class Task(models.Model):
    _inherit = 'project.task'

    xyz_material_ids = fields.One2many('xyz.material', 'task_id', string='Actual materials')
    xyz_invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True, copy=False)
    xyz_transfer_id = fields.Many2one('stock.picking', string='Truck transfer', readonly=True, copy=False)
    xyz_cash_reported = fields.Monetary('Cash reported by technician', currency_field='company_currency_id')
    company_currency_id = fields.Many2one(related='company_id.currency_id')
    xyz_cash_confirmed = fields.Boolean('Cash confirmed by accounting', readonly=True, copy=False)
    xyz_actual_amount = fields.Monetary('Actual total for customer approval', currency_field='company_currency_id', compute='_compute_xyz_actual_amount', compute_sudo=True)

    def _xyz_commercial_lines(self):
        self.ensure_one()
        order = self._xyz_order()
        labor = self.env.ref('xyz_service_stock_billing.product_labor').product_variant_id
        rows = []
        for line in order.order_line.filtered(lambda line: not line.display_type and line.product_id.type == 'service'):
            quantity = sum(self.timesheet_ids.mapped('unit_amount')) if line.product_id == labor else line.product_uom_qty
            total = line.tax_id.compute_all(line.price_unit * (1 - line.discount / 100), currency=order.currency_id, quantity=quantity, product=line.product_id, partner=order.partner_id)['total_included']
            rows.append({'product': line.name, 'quantity': quantity, 'uom': line.product_uom.name, 'total': total})
        for material in self.xyz_material_ids:
            line = order.order_line.filtered(lambda line: line.product_id == material.product_id)[:1]
            price = line.price_unit * (1 - line.discount / 100) if line else order.pricelist_id._get_product_price(material.product_id, material.quantity)
            taxes = line.tax_id if line else order.fiscal_position_id.map_tax(material.product_id.taxes_id.filtered(lambda tax: tax.company_id == order.company_id))
            quantity = material.product_id.uom_id._compute_quantity(material.quantity, line.product_uom) if line else material.quantity
            total = taxes.compute_all(price, currency=order.currency_id, quantity=quantity, product=material.product_id, partner=order.partner_id)['total_included']
            rows.append({'product': material.product_id.display_name, 'quantity': material.quantity, 'uom': material.product_id.uom_id.name, 'total': total})
        return rows

    @api.depends('timesheet_ids.unit_amount', 'xyz_material_ids.quantity', 'xyz_material_ids.product_id', 'xyz_booking_id.sale_id.order_line.price_unit', 'xyz_booking_id.sale_id.order_line.discount', 'xyz_booking_id.sale_id.order_line.tax_id')
    def _compute_xyz_actual_amount(self):
        for task in self:
            task.xyz_actual_amount = sum(row['total'] for row in task._xyz_commercial_lines()) if task.xyz_booking_id else 0

    def write(self, vals):
        if {'xyz_invoice_id', 'xyz_cash_confirmed', 'xyz_transfer_id'}.intersection(vals) and not self.env.su:
            raise AccessError(_('Billing and warehouse evidence is managed by workflow actions.'))
        if 'xyz_cash_reported' in vals:
            if vals['xyz_cash_reported'] < 0 or any(t.xyz_cash_confirmed for t in self):
                raise UserError(_('Cash must be nonnegative and cannot change after confirmation.'))
        if {'xyz_employee_id', 'xyz_material_ids'}.intersection(vals) and any(t.xyz_state == 'done' for t in self):
            raise UserError(_('Accepted jobs cannot be reassigned or have materials changed.'))
        if 'xyz_employee_id' in vals and any(t.xyz_transfer_id and t.xyz_employee_id.id != vals['xyz_employee_id'] for t in self):
            raise UserError(_('Handle the existing truck transfer before changing technicians.'))
        return super().write(vals)

    def _xyz_order(self):
        return self.xyz_booking_id.sudo().sale_id

    def _xyz_validate_cancellation(self):
        super()._xyz_validate_cancellation()
        for task in self:
            for move in task.xyz_transfer_id.sudo().move_ids.filtered(lambda m: m.state == 'done'):
                returned = sum(move.returned_move_ids.filtered(lambda m: m.state == 'done').mapped('quantity'))
                if returned + 0.000001 < move.quantity:
                    raise UserError(_('Return the prepared truck materials before cancelling this job.'))

    def action_xyz_revise(self):
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group('xyz_service_core.group_manager'):
            raise AccessError(_('Service manager access required.'))
        self._xyz_lock()
        if self.xyz_state != 'done' or self.xyz_invoice_id.state != 'draft':
            raise UserError(_('Revision is only available before the invoice is posted. Use a separate follow-up job after posting.'))
        for line in self.xyz_material_ids:
            move = line.move_id.sudo()
            if move and move.state == 'done':
                reverse = self.env['stock.move'].sudo().create({
                    'name': 'Acceptance revision: ' + self.name, 'product_id': move.product_id.id,
                    'product_uom_qty': move.quantity, 'product_uom': move.product_uom.id,
                    'location_id': move.location_dest_id.id, 'location_dest_id': move.location_id.id,
                    'origin_returned_move_id': move.id, 'sale_line_id': move.sale_line_id.id,
                    'to_refund': True,
                })
                reverse._action_confirm()
                reverse.quantity = move.quantity
                reverse.picked = True
                reverse._action_done()
        self.xyz_invoice_id.sudo().button_cancel()
        self._xyz_system_write({'xyz_state': 'acceptance', 'xyz_finished_at': False})
        self.sudo().write({'xyz_invoice_id': False, 'xyz_signature': False, 'xyz_signer': False})
        self.xyz_material_ids.sudo().write({'move_id': False, 'cost': 0})
        self.message_post(body=_('Acceptance revision opened. Previous signed evidence is retained; previous stock consumption has been reversed.'))
        return True

    def action_xyz_prepare_materials(self):
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group('stock.group_stock_user'):
            raise AccessError(_('Warehouse access required.'))
        self._xyz_lock()
        order = self._xyz_order()
        location = self.xyz_employee_id.xyz_location_id
        if not location:
            raise UserError(_('Assign a technician with a truck location.'))
        if self.xyz_transfer_id:
            return {'type': 'ir.actions.act_window', 'res_model': 'stock.picking', 'res_id': self.xyz_transfer_id.id, 'views': [(False, 'form')]}
        moves = order.picking_ids.move_ids.filtered(lambda m: m.state not in ('done', 'cancel') and m.product_id.is_storable)
        if not moves:
            raise UserError(_('Add stock products to the sales order before preparing the truck.'))
        moves._do_unreserve()
        # The customer leg must draw from the truck, not independently from the main warehouse.
        moves.write({'location_id': location.id})
        transfer = self.env['stock.picking'].create({
            'picking_type_id': order.warehouse_id.int_type_id.id,
            'location_id': order.warehouse_id.lot_stock_id.id, 'location_dest_id': location.id,
            'origin': order.name,
            'move_ids': [fields.Command.create({
                'name': move.product_id.display_name, 'product_id': move.product_id.id,
                'product_uom': move.product_uom.id, 'product_uom_qty': move.product_uom_qty,
                'location_id': order.warehouse_id.lot_stock_id.id, 'location_dest_id': location.id,
            }) for move in moves],
        })
        transfer.action_confirm()
        transfer.action_assign()
        self.sudo().xyz_transfer_id = transfer
        return {'type': 'ir.actions.act_window', 'res_model': 'stock.picking', 'res_id': transfer.id, 'views': [(False, 'form')]}

    def _xyz_acceptance_payload(self):
        data = super()._xyz_acceptance_payload()
        data['materials'] = [{'product': line.product_id.display_name, 'quantity': line.quantity, 'uom': line.product_id.uom_id.name} for line in self.xyz_material_ids]
        data['sale_order'] = self._xyz_order().name
        data['charges'] = self._xyz_commercial_lines()
        data['total'] = sum(row['total'] for row in data['charges'])
        data['currency'] = self._xyz_order().currency_id.name
        return data

    def action_xyz_accept(self):
        self.ensure_one()
        self._xyz_require_technician()
        self._xyz_lock()
        if self.xyz_state == 'done':
            return True
        order = self._xyz_order()
        location = self.xyz_employee_id.sudo().xyz_location_id
        if any(line.product_id.is_storable and line.product_id.invoice_policy != 'delivery' for line in order.order_line):
            raise UserError(_('Service materials must be invoiced on delivered quantities. Correct the product invoicing policy first.'))
        if self.xyz_material_ids and not location:
            raise UserError(_('A truck stock location is required.'))
        # Serialize consumption for a location; quants remain handled by stock APIs.
        if location:
            self.env.cr.execute("UPDATE stock_location SET write_date=timezone('UTC', now()) WHERE id=%s", [location.id])
        pending = order.picking_ids.move_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
        pending._do_unreserve()
        pending._action_cancel()
        if self.xyz_material_ids:
            picking = self.env['stock.picking'].sudo().create({
                'picking_type_id': order.warehouse_id.out_type_id.id,
                'partner_id': order.partner_shipping_id.id, 'origin': order.name,
                'location_id': location.id,
                'location_dest_id': order.partner_shipping_id.property_stock_customer.id,
            })
            for line in self.xyz_material_ids:
                available = self.env['stock.quant'].sudo()._get_available_quantity(line.product_id, location)
                if available + 0.000001 < line.quantity:
                    raise UserError(_('Insufficient truck stock for %s.', line.product_id.display_name))
                sale_line = order.order_line.filtered(lambda l: l.product_id == line.product_id)[:1]
                if not sale_line:
                    sale_line = self.env['sale.order.line'].sudo().with_context(skip_procurement=True).create({'order_id': order.id, 'product_id': line.product_id.id, 'product_uom_qty': line.quantity})
                move = self.env['stock.move'].sudo().create({
                    'name': line.product_id.display_name, 'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity, 'product_uom': line.product_id.uom_id.id,
                    'picking_id': picking.id, 'sale_line_id': sale_line.id,
                    'location_id': location.id, 'location_dest_id': picking.location_dest_id.id,
                })
                move._action_confirm()
                move._action_assign()
                move.quantity = line.quantity
                move.picked = True
                move._action_done()
                line.sudo().write({'move_id': move.id, 'cost': line.product_id.standard_price * line.quantity})
        labor = self.env.ref('xyz_service_stock_billing.product_labor').product_variant_id
        hours = sum(self.timesheet_ids.mapped('unit_amount'))
        labor_line = order.order_line.filtered(lambda l: l.product_id == labor)[:1]
        if labor_line:
            labor_line.qty_delivered = hours
        result = super().action_xyz_accept()
        invoice = order._create_invoices()
        if len(invoice) != 1:
            raise UserError(_('Expected one invoice for the service order.'))
        self.sudo().xyz_invoice_id = invoice
        return result

    def action_xyz_confirm_cash(self):
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group('account.group_account_invoice'):
            raise AccessError(_('Accounting access required.'))
        self._xyz_lock()
        if self.xyz_cash_confirmed:
            return True
        invoice = self.xyz_invoice_id
        if invoice.state != 'posted' or self.xyz_cash_reported <= 0 or self.xyz_cash_reported > invoice.amount_residual:
            raise UserError(_('Post the invoice and enter a positive cash amount no greater than the balance.'))
        journal = self.env['account.journal'].search([('type', '=', 'cash'), ('company_id', '=', self.company_id.id)], limit=1)
        if not journal:
            raise UserError(_('Configure a cash journal first.'))
        wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'amount': self.xyz_cash_reported, 'journal_id': journal.id,
        })
        wizard.action_create_payments()
        self.sudo().xyz_cash_confirmed = True
        return True


class Timesheet(models.Model):
    _inherit = 'account.analytic.line'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            task = self.env['project.task'].browse(vals.get('task_id'))
            if task and task.xyz_booking_id:
                task._xyz_lock()
            if task and task.xyz_booking_id and task.xyz_state in ('done', 'cancel'):
                raise UserError(_('Cannot add time to a closed service job.'))
        return super().create(vals_list)

    def write(self, vals):
        tasks = self.mapped('task_id') | self.env['project.task'].browse(vals.get('task_id'))
        tasks.filtered('xyz_booking_id')._xyz_lock()
        if any(t.xyz_booking_id and t.xyz_state in ('done', 'cancel') for t in tasks):
            raise UserError(_('Accepted service timesheets are immutable.'))
        return super().write(vals)

    def unlink(self):
        self.mapped('task_id').filtered('xyz_booking_id')._xyz_lock()
        if any(t.xyz_booking_id and t.xyz_state in ('done', 'cancel') for t in self.mapped('task_id')):
            raise UserError(_('Accepted service timesheets are immutable.'))
        return super().unlink()


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _action_cancel(self):
        tasks = self.sudo().mapped('xyz_task_id')
        tasks._xyz_validate_cancellation()
        result = super()._action_cancel()
        tasks._xyz_system_write({'xyz_state': 'cancel'})
        return result


class SaleLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            order = self.env['sale.order'].browse(vals.get('order_id'))
            if order.sudo().xyz_task_id.xyz_state == 'done':
                raise UserError(_('Revise the acceptance before changing its commercial terms.'))
        return super().create(vals_list)

    def write(self, vals):
        if {'price_unit', 'discount', 'product_id', 'product_uom_qty', 'tax_id', 'order_id'}.intersection(vals):
            if any(line.order_id.sudo().xyz_task_id.xyz_state == 'done' for line in self):
                raise UserError(_('Accepted commercial terms are immutable.'))
        return super().write(vals)

    def unlink(self):
        if any(line.order_id.sudo().xyz_task_id.xyz_state == 'done' for line in self):
            raise UserError(_('Accepted commercial terms are immutable.'))
        return super().unlink()


class Reminder(models.Model):
    _name = 'xyz.payment.reminder'
    _description = 'Invoice reminder delivery log'

    move_id = fields.Many2one('account.move', required=True, ondelete='cascade')
    milestone = fields.Integer(required=True)
    _sql_constraints = [('unique_reminder', 'unique(move_id, milestone)', 'Reminder already queued.')]

    @api.model
    def _cron_remind(self):
        today = fields.Date.today()
        invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('amount_residual', '>', 0),
            ('invoice_date_due', '<', today), ('invoice_origin', '!=', False),
        ])
        for invoice in invoices:
            if not self.env['project.task'].search_count([('xyz_invoice_id', '=', invoice.id)]):
                continue
            self.env.cr.execute('SELECT id FROM account_move WHERE id=%s FOR UPDATE', [invoice.id])
            days = (today - invoice.invoice_date_due).days
            for milestone in (1, 7, 14):
                if days < milestone or self.search_count([('move_id', '=', invoice.id), ('milestone', '=', milestone)]):
                    continue
                if invoice.partner_id.email:
                    self.env['mail.mail'].create({
                        'subject': _('XYZ · Payment reminder %s') % invoice.name,
                        'body_html': _('<p>Please review the outstanding invoice in your customer portal.</p>'),
                        'email_to': invoice.partner_id.email,
                        'email_from': self.env.company.email or 'xyz@example.test',
                    })
                    self.create({'move_id': invoice.id, 'milestone': milestone})


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        for picking in self:
            if picking.sale_id.sudo().xyz_task_id and picking.picking_type_code == 'outgoing' and picking.state != 'done':
                raise UserError(_('XYZ customer deliveries are validated by service acceptance using actual quantities.'))
            task = self.env['project.task'].sudo().search([('xyz_transfer_id', '=', picking.id)], limit=1)
            if task and picking.state not in ('done', 'cancel'):
                self.env.cr.execute("UPDATE stock_location SET write_date=timezone('UTC', now()) WHERE id=%s", [picking.location_id.id])
                for product in picking.move_ids.product_id.filtered('is_storable'):
                    moves = picking.move_ids.filtered(lambda move: move.product_id == product and move.state not in ('done', 'cancel'))
                    quantity = sum(move.product_uom._compute_quantity(move.quantity, product.uom_id) for move in moves)
                    quants = self.env['stock.quant'].sudo()._gather(product, picking.location_id)
                    if sum(quants.mapped('quantity')) + 0.000001 < quantity:
                        raise UserError(_('Cannot transfer more %s than physically available.', product.display_name))
        return super().button_validate()
