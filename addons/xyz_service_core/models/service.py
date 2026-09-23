import base64
import json
from datetime import timedelta
from urllib.parse import quote

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError, UserError


class Equipment(models.Model):
    _name = 'xyz.equipment'
    _description = 'Customer equipment'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, tracking=True)
    serial = fields.Char()
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    address = fields.Char('Address')
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)


class Employee(models.Model):
    _inherit = 'hr.employee'

    xyz_area = fields.Char('Service area', groups='hr.group_hr_user')


class Product(models.Model):
    _inherit = 'product.template'

    xyz_booking_service = fields.Boolean('XYZ booking service')
    xyz_expected_hours = fields.Float('Expected hours', default=2)
    xyz_required_skill_ids = fields.Many2many('hr.skill', string='Required skills')


class Booking(models.Model):
    _name = 'xyz.booking'
    _description = 'Service booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(default=lambda self: _('New'), readonly=True)
    token = fields.Char(required=True, copy=False, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    equipment_id = fields.Many2one('xyz.equipment', string='Equipment', required=True)
    product_id = fields.Many2one('product.product', string='Service', required=True)
    requested_start = fields.Datetime('Requested start', required=True)
    description = fields.Text('Issue description')
    lead_id = fields.Many2one('crm.lead', readonly=True)
    sale_id = fields.Many2one('sale.order', readonly=True)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    _sql_constraints = [('token_unique', 'unique(token)', 'This booking was already submitted.')]

    def _xyz_order_lines(self):
        self.ensure_one()
        return [fields.Command.create({'product_id': self.product_id.id, 'product_uom_qty': 1})]

    def write(self, vals):
        result = super().write(vals)
        if 'user_id' in vals:
            for booking in self:
                booking.lead_id.user_id = booking.user_id
                booking.sale_id.user_id = booking.user_id
                booking.equipment_id.user_id = booking.user_id
                booking.partner_id.user_id = booking.user_id
        return result

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('xyz.booking') or _('New')
        records = super().create(vals_list)
        for booking in records:
            if not booking.product_id.xyz_booking_service or booking.product_id.type != 'service':
                raise ValidationError(_('Select a published booking service.'))
            lead = self.env['crm.lead'].create({
                'name': booking.name, 'partner_id': booking.partner_id.id,
                'type': 'opportunity', 'description': booking.description,
                'user_id': booking.user_id.id,
            })
            order = self.env['sale.order'].create({
                'partner_id': booking.partner_id.id, 'origin': booking.name,
                'user_id': booking.user_id.id, 'opportunity_id': lead.id,
                'require_signature': True,
                'order_line': booking._xyz_order_lines(),
            })
            booking.write({'lead_id': lead.id, 'sale_id': order.id})
            template = self.env.ref('sale.email_template_edi_sale', raise_if_not_found=False)
            if template:
                template.send_mail(order.id, force_send=False)
                order.action_quotation_sent()
        return records


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    xyz_task_id = fields.Many2one('project.task', copy=False, readonly=True)

    def action_confirm(self):
        if not self:
            return True
        # Lock before the state transition so concurrent confirmations cannot create two tasks.
        self.env.cr.execute('SELECT id FROM sale_order WHERE id IN %s ORDER BY id FOR UPDATE', [tuple(self.ids)])
        self.invalidate_recordset(['state', 'xyz_task_id'])
        pending = self.filtered(lambda order: order.state in ('draft', 'sent'))
        result = super(SaleOrder, pending).action_confirm() if pending else True
        for order in self.filtered(lambda sale: sale.state == 'sale'):
            booking = self.env['xyz.booking'].search([('sale_id', '=', order.id)], limit=1)
            if booking and not order.xyz_task_id:
                task = self.env['project.task'].sudo().create({
                    'name': '%s — %s' % (order.name, booking.equipment_id.name),
                    'project_id': self.env.ref('xyz_service_core.project_service').id,
                    'partner_id': order.partner_id.id,
                    'sale_line_id': order.order_line.filtered(lambda line: line.product_id == booking.product_id)[:1].id,
                    'xyz_booking_id': booking.id, 'xyz_equipment_id': booking.equipment_id.id,
                    'xyz_start': booking.requested_start,
                    'xyz_end': booking.requested_start + timedelta(hours=booking.product_id.xyz_expected_hours or 2),
                    'xyz_required_skill_ids': [fields.Command.set(booking.product_id.xyz_required_skill_ids.ids)],
                    'user_ids': [fields.Command.clear()],
                })
                order.xyz_task_id = task
        return result


class Task(models.Model):
    _inherit = 'project.task'

    xyz_booking_id = fields.Many2one('xyz.booking', readonly=True, copy=False)
    xyz_equipment_id = fields.Many2one('xyz.equipment')
    xyz_state = fields.Selection([
        ('new', 'Awaiting dispatch'), ('scheduled', 'Scheduled'), ('working', 'In progress'),
        ('acceptance', 'Awaiting acceptance'), ('done', 'Completed'), ('cancel', 'Cancelled'),
    ], default='new', required=True, tracking=True)
    xyz_employee_id = fields.Many2one('hr.employee', string='Technician', tracking=True)
    xyz_required_skill_ids = fields.Many2many('hr.skill', string='Required skills')
    xyz_start = fields.Datetime('Planned start', tracking=True)
    xyz_end = fields.Datetime('Planned end', tracking=True)
    xyz_timer_start = fields.Datetime(readonly=True, copy=False)
    xyz_finished_at = fields.Datetime(readonly=True, copy=False)
    xyz_checked_safety = fields.Boolean('Safety checked')
    xyz_checked_service = fields.Boolean('Service completed')
    xyz_checked_test = fields.Boolean('Test run passed')
    xyz_before = fields.Binary('Before photo', attachment=True)
    xyz_after = fields.Binary('After photo', attachment=True)
    xyz_signature = fields.Binary('Customer signature', attachment=True)
    xyz_signer = fields.Char('Signed by')
    xyz_acceptance_ids = fields.One2many('xyz.acceptance', 'task_id', string='Acceptance records', readonly=True)
    xyz_map_url = fields.Char(compute='_compute_map_url')
    xyz_can_dispatch = fields.Boolean(compute='_compute_xyz_permissions')
    xyz_can_work = fields.Boolean(compute='_compute_xyz_permissions')

    @api.depends_context('uid')
    def _compute_xyz_permissions(self):
        for task in self:
            task.xyz_can_dispatch = self.env.su or self.env.user.has_group('xyz_service_core.group_dispatcher')
            task.xyz_can_work = task.xyz_can_dispatch or task.xyz_employee_id.sudo().user_id == self.env.user

    @api.depends('partner_id', 'xyz_equipment_id.address')
    def _compute_map_url(self):
        for task in self:
            address = task.xyz_equipment_id.address or task.partner_id.contact_address or ''
            task.xyz_map_url = 'https://www.openstreetmap.org/search?query=' + quote(address)

    def _xyz_lock(self):
        if not self:
            return
        self.check_access('write')
        self.env.cr.execute("UPDATE project_task SET write_date=timezone('UTC', now()) WHERE id IN %s", [tuple(sorted(self.ids))])
        self.invalidate_recordset()

    def _xyz_require_technician(self):
        if self.env.su or self.env.user.has_group('xyz_service_core.group_dispatcher'):
            return
        if any(task.xyz_employee_id.sudo().user_id != self.env.user for task in self):
            raise AccessError(_('Only the assigned technician may perform this action.'))

    def _xyz_system_write(self, vals):
        return super(Task, self).write(vals)

    def write(self, vals):
        internal = {'xyz_state', 'xyz_timer_start', 'xyz_finished_at', 'xyz_acceptance_ids'}
        if internal.intersection(vals) and not self.env.su:
            raise AccessError(_('Use the service workflow buttons to change progress.'))
        if not self.env.su and self.env.user.has_group('xyz_service_core.group_technician') and not self.env.user.has_group('xyz_service_core.group_dispatcher'):
            allowed = {'xyz_before', 'xyz_after', 'xyz_signature', 'xyz_signer', 'xyz_checked_safety', 'xyz_checked_service', 'xyz_checked_test', 'xyz_material_ids', 'xyz_cash_reported'}
            if any(t.xyz_booking_id for t in self) and set(vals) - allowed:
                raise AccessError(_('Technicians can only update on-site evidence and material usage.'))
        protected = {'xyz_employee_id', 'xyz_start', 'xyz_end', 'xyz_required_skill_ids', 'user_ids', 'xyz_booking_id'}
        if not self.env.su and protected.intersection(vals) and any(t.xyz_booking_id for t in self) and not self.env.user.has_group('xyz_service_core.group_dispatcher'):
            raise AccessError(_('Only dispatchers can change assignments.'))
        snapshot_fields = {'xyz_before', 'xyz_after', 'xyz_signature', 'xyz_signer', 'xyz_checked_safety', 'xyz_checked_service', 'xyz_checked_test'}
        if snapshot_fields.intersection(vals):
            self._xyz_require_technician()
        if snapshot_fields.intersection(vals) and any(t.xyz_state == 'done' for t in self):
            raise UserError(_('Completed acceptance data is immutable.'))
        result = super().write(vals)
        if 'xyz_employee_id' in vals:
            for task in self:
                super(Task, task).write({'user_ids': [fields.Command.set(task.xyz_employee_id.user_id.ids)]})
        return result

    @api.constrains('xyz_start', 'xyz_end', 'xyz_employee_id', 'xyz_state', 'xyz_required_skill_ids')
    def _check_xyz_schedule(self):
        for task in self.filtered(lambda t: t.xyz_booking_id and t.xyz_employee_id and t.xyz_state != 'cancel'):
            employee = task.xyz_employee_id.sudo()
            # A write also forces a stale REPEATABLE READ transaction to retry after contention.
            self.env.cr.execute("UPDATE hr_employee SET write_date=timezone('UTC', now()) WHERE id=%s", [employee.id])
            if not employee.user_id:
                raise ValidationError(_('The technician needs an internal user account.'))
            if not task.xyz_start or not task.xyz_end or task.xyz_end <= task.xyz_start:
                raise ValidationError(_('The planned end must follow the start.'))
            if task.xyz_required_skill_ids - employee.skill_ids:
                raise ValidationError(_('The technician does not have every required skill.'))
            if self.sudo().search_count([
                ('id', '!=', task.id), ('xyz_booking_id', '!=', False),
                ('xyz_employee_id', '=', employee.id), ('xyz_state', 'not in', ['cancel', 'done']),
                ('xyz_start', '<', task.xyz_end), ('xyz_end', '>', task.xyz_start),
            ]):
                raise ValidationError(_('This technician already has a job in this time range.'))
            import pytz
            start = pytz.UTC.localize(task.xyz_start)
            end = pytz.UTC.localize(task.xyz_end)
            calendar = employee.resource_calendar_id
            intervals = calendar._work_intervals_batch(start, end, resources=employee.resource_id)[employee.resource_id.id]
            covered = sum((stop - begin).total_seconds() for begin, stop, _meta in intervals)
            if covered + 1 < (end - start).total_seconds():
                raise ValidationError(_('The job must be entirely inside the technician working hours.'))

    def action_xyz_schedule(self):
        if not self.env.su and not self.env.user.has_group('xyz_service_core.group_dispatcher'):
            raise AccessError(_('Dispatcher access required.'))
        if any(not task.xyz_employee_id or task.xyz_state not in ('new', 'scheduled') for task in self):
            raise UserError(_('Assign a technician to an unstarted job first.'))
        self._xyz_system_write({'xyz_state': 'scheduled'})

    def _xyz_validate_cancellation(self):
        if any(task.xyz_state not in ('new', 'scheduled', 'cancel') or task.timesheet_ids for task in self):
            raise UserError(_('Only unstarted jobs without time entries can be cancelled.'))

    def action_xyz_cancel(self):
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group('xyz_service_core.group_dispatcher'):
            raise AccessError(_('Dispatcher access required.'))
        self._xyz_lock()
        self._xyz_validate_cancellation()
        order = self.xyz_booking_id.sudo().sale_id
        order.with_context(disable_cancel_warning=True).action_cancel()
        self._xyz_system_write({'xyz_state': 'cancel'})
        return True

    def action_xyz_check_in(self):
        self.ensure_one()
        self._xyz_require_technician()
        self._xyz_lock()
        # Employee lock serializes simultaneous starts on different jobs.
        self.env.cr.execute("UPDATE hr_employee SET write_date=timezone('UTC', now()) WHERE id=%s", [self.xyz_employee_id.id])
        if self.xyz_timer_start:
            return True
        if self.xyz_state not in ('scheduled', 'working'):
            raise UserError(_('Schedule the job before checking in.'))
        if self.sudo().search_count([('xyz_employee_id', '=', self.xyz_employee_id.id), ('xyz_timer_start', '!=', False)]):
            raise UserError(_('Stop the other running timer first.'))
        self._xyz_system_write({'xyz_state': 'working', 'xyz_timer_start': fields.Datetime.now()})

    def action_xyz_check_out(self):
        self.ensure_one()
        self._xyz_require_technician()
        self._xyz_lock()
        if not self.xyz_timer_start:
            return True
        hours = (fields.Datetime.now() - self.xyz_timer_start).total_seconds() / 3600
        self.env['account.analytic.line'].create({
            'name': _('XYZ on-site service'), 'project_id': self.project_id.id, 'task_id': self.id,
            'employee_id': self.xyz_employee_id.id, 'unit_amount': max(hours, 0),
            'date': fields.Date.context_today(self),
        })
        self._xyz_system_write({'xyz_timer_start': False, 'xyz_state': 'acceptance'})

    def _xyz_acceptance_payload(self):
        return {
            'task': self.name, 'equipment': self.xyz_equipment_id.name,
            'customer': self.partner_id.display_name, 'signer': self.xyz_signer,
            'hours': sum(self.timesheet_ids.mapped('unit_amount')),
            'checklist': [self.xyz_checked_safety, self.xyz_checked_service, self.xyz_checked_test],
        }

    def action_xyz_accept(self):
        self.ensure_one()
        self._xyz_require_technician()
        self._xyz_lock()
        if self.xyz_state == 'done':
            return True
        if self.xyz_state != 'acceptance' or self.xyz_timer_start:
            raise UserError(_('Check out before accepting the service.'))
        if not all([self.xyz_checked_safety, self.xyz_checked_service, self.xyz_checked_test,
                    self.xyz_before, self.xyz_after, self.xyz_signature, self.xyz_signer]):
            raise UserError(_('Complete the checklist, photos, signature and signatory.'))
        acceptance = self.env['xyz.acceptance'].sudo().create({
            'task_id': self.id, 'name': self.name, 'signed_at': fields.Datetime.now(),
            'snapshot': json.dumps(self._xyz_acceptance_payload(), ensure_ascii=False),
            'signature': self.xyz_signature, 'before': self.xyz_before, 'after': self.xyz_after,
        })
        self._xyz_system_write({'xyz_state': 'done', 'xyz_finished_at': fields.Datetime.now()})
        pdf, _format = self.env['ir.actions.report'].sudo()._render_qweb_pdf('xyz_service_core.report_acceptance', res_ids=acceptance.ids)
        self.env['ir.attachment'].sudo().create({
            'name': self.name.replace('/', '-') + '-acceptance.pdf',
            'type': 'binary', 'datas': base64.b64encode(pdf), 'mimetype': 'application/pdf',
            'res_model': 'xyz.acceptance', 'res_id': acceptance.id,
        })
        return True

    @api.model
    def xyz_dispatch_data(self):
        if not self.env.su and not self.env.user.has_group('xyz_service_core.group_dispatcher'):
            raise AccessError(_('Dispatcher access required.'))
        tasks = self.search([('xyz_booking_id', '!=', False), ('xyz_state', 'not in', ['done', 'cancel'])])
        employees = self.env['hr.employee'].search([('user_id', '!=', False), ('company_id', '=', self.env.company.id)])
        return {
            'form_view_id': self.env.ref('xyz_service_core.view_field_job_form').id,
            'groups': [{'id': e.id, 'content': e.name, 'area': e.xyz_area or '', 'skills': e.skill_ids.ids} for e in employees],
            'skills': [{'id': skill.id, 'name': skill.name} for skill in employees.mapped('skill_ids')],
            'items': [{'id': t.id, 'content': t.name, 'group': t.xyz_employee_id.id or 0,
                       'start': fields.Datetime.to_string(t.xyz_start), 'end': fields.Datetime.to_string(t.xyz_end),
                       'state': t.xyz_state} for t in tasks if t.xyz_start and t.xyz_end],
        }

    def xyz_dispatch_move(self, employee_id, start, end):
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group('xyz_service_core.group_dispatcher'):
            raise AccessError(_('Dispatcher access required.'))
        self._xyz_lock()
        employee = self.env['hr.employee'].search([('id', '=', int(employee_id)), ('company_id', '=', self.env.company.id), ('user_id', '!=', False)], limit=1)
        if not employee:
            raise UserError(_('Select an active technician in this company.'))
        if self.xyz_state not in ('new', 'scheduled'):
            raise UserError(_('Only unstarted jobs may be rescheduled.'))
        self.write({'xyz_employee_id': int(employee_id), 'xyz_start': start, 'xyz_end': end})
        self._xyz_system_write({'xyz_state': 'scheduled'})
        return True


class Acceptance(models.Model):
    _name = 'xyz.acceptance'
    _description = 'Service acceptance'
    _order = 'id desc'

    name = fields.Char(required=True)
    task_id = fields.Many2one('project.task', required=True, ondelete='restrict')
    signed_at = fields.Datetime(required=True)
    snapshot = fields.Text(required=True)
    signature = fields.Binary(attachment=True)
    before = fields.Binary(attachment=True)
    after = fields.Binary(attachment=True)
    company_id = fields.Many2one(related='task_id.company_id', store=True)

    def _snapshot_data(self):
        self.ensure_one()
        return json.loads(self.snapshot)

    def write(self, vals):
        raise AccessError(_('Acceptance records cannot be modified.'))

    def unlink(self):
        raise AccessError(_('Acceptance records cannot be deleted.'))
