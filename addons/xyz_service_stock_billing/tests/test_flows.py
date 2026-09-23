"""Acceptance, stock and reporting criteria listed in plan.md.

These cases complement `test_service.py`: it covers the guards (states, timers,
record rules) while this module walks the commercial and warehouse flow with real
documents — quotation pricing, truck transfer, actual consumption, invoicing,
reminders, cash confirmation and the KPI view.
"""
import base64
from datetime import datetime, timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import AccessError, UserError, ValidationError


@tagged('post_install', '-at_install')
class TestXYZServiceFlows(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        if not company.chart_template:
            cls.env['account.chart.template'].try_loading('generic_coa', company, install_demo=False)
        company.resource_calendar_id.tz = 'UTC'
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)
        cls.env.ref('xyz_service_core.project_service').company_id = company
        cls.partner = cls.env['res.partner'].create({'name': 'Flow customer', 'email': 'flow-service@example.test'})
        cls.equipment = cls.env['xyz.equipment'].create({'name': 'Flow compressor', 'partner_id': cls.partner.id})
        cls.product = cls.env.ref('xyz_service_core.service_compressor').product_variant_id
        cls.labor = cls.env.ref('xyz_service_stock_billing.product_labor').product_variant_id
        cls.user = cls.env['res.users'].create({'name': 'Flow mechanic', 'login': 'flow-mechanic', 'email': 'flow-mechanic@example.test',
                                                'groups_id': [fields.Command.set([cls.env.ref('xyz_service_core.group_technician').id])]})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Flow mechanic', 'user_id': cls.user.id, 'company_id': company.id,
            'resource_calendar_id': company.resource_calendar_id.id,
            'xyz_location_id': cls.env.ref('xyz_service_stock_billing.truck_1').id,
        })
        cls.accountant = cls.env['res.users'].create({'name': 'Flow accountant', 'login': 'flow-accountant', 'email': 'flow-accountant@example.test',
                                                     'groups_id': [fields.Command.set([cls.env.ref('account.group_account_invoice').id])]})

    # ------------------------------------------------------------------ helpers
    def make_booking(self, token, partner=None, product=None, equipment=None):
        return self.env['xyz.booking'].create({
            'token': token, 'partner_id': (partner or self.partner).id,
            'equipment_id': (equipment or self.equipment).id,
            'product_id': (product or self.product).id,
            'requested_start': datetime(2027, 1, 4, 9),
        })

    def make_task(self, token, materials=(), stock=0):
        """Booking → confirmed order → scheduled job, optionally with quoted materials on hand."""
        order = self.make_booking(token).sale_id
        for product, quantity in materials:
            if stock:
                self.env['stock.quant']._update_available_quantity(product, self.warehouse.lot_stock_id, stock)
            self.env['sale.order.line'].create({'order_id': order.id, 'product_id': product.id, 'product_uom_qty': quantity})
        order.action_confirm()
        task = order.xyz_task_id
        task.write({'xyz_employee_id': self.employee.id})
        task.action_xyz_schedule()
        return task

    def material_product(self, name):
        return self.env['product.product'].create({
            'name': name, 'type': 'consu', 'is_storable': True, 'list_price': 150000,
            'standard_price': 90000, 'invoice_policy': 'delivery',
        })

    def truck_quantity(self, product):
        """Physical quantity on the truck; the quoted delivery may still reserve it."""
        quants = self.env['stock.quant'].search([
            ('product_id', '=', product.id), ('location_id', 'child_of', self.employee.xyz_location_id.id),
        ])
        return sum(quants.mapped('quantity'))

    def prepare_truck(self, task):
        task.action_xyz_prepare_materials()
        transfer = task.xyz_transfer_id
        self.assertTrue(transfer)
        for move in transfer.move_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        transfer.button_validate()
        self.assertEqual(transfer.state, 'done')
        return transfer

    def consume(self, task):
        """One hour of work, checklist, photos and customer signature."""
        proof = base64.b64encode(b'flow-evidence')
        task.action_xyz_check_in()
        task._xyz_system_write({'xyz_timer_start': fields.Datetime.now() - timedelta(hours=1)})
        task.action_xyz_check_out()
        task.write({'xyz_checked_safety': True, 'xyz_checked_service': True, 'xyz_checked_test': True,
                    'xyz_before': proof, 'xyz_after': proof, 'xyz_signature': proof, 'xyz_signer': 'Customer flow'})
        return task

    def accepted_task(self, token, materials=(), stock=0):
        task = self.make_task(token, materials=materials, stock=stock)
        self.consume(task)
        task.action_xyz_accept()
        return task

    # ------------------------------------------------------------ quotation
    def test_pricing_follows_partner_pricelist(self):
        company = self.env.company
        retail = self.env['product.pricelist'].create({'name': 'Flow retail', 'currency_id': company.currency_id.id})
        b2b = self.env['product.pricelist'].create({
            'name': 'Flow B2B -10%', 'currency_id': company.currency_id.id,
            'item_ids': [fields.Command.create({'applied_on': '3_global', 'compute_price': 'percentage', 'percent_price': 10})],
        })
        b2b_partner = self.env['res.partner'].create({'name': 'Flow B2B customer', 'property_product_pricelist': b2b.id})
        retail_partner = self.env['res.partner'].create({'name': 'Flow retail customer', 'property_product_pricelist': retail.id})
        retail_booking = self.make_booking('flow-price-retail', partner=retail_partner)
        b2b_booking = self.make_booking('flow-price-b2b', partner=b2b_partner, equipment=self.env['xyz.equipment'].create({'name': 'Flow B2B compressor', 'partner_id': b2b_partner.id}))
        retail_line = retail_booking.sale_id.order_line.filtered(lambda line: line.product_id == self.product)
        b2b_line = b2b_booking.sale_id.order_line.filtered(lambda line: line.product_id == self.product)
        self.assertAlmostEqual(retail_line.price_unit, self.product.list_price, places=2)
        self.assertAlmostEqual(b2b_line.price_unit, self.product.list_price * 0.9, places=2)
        # Booking has no price field at all, so a browser cannot post its own amount.
        self.assertNotIn('price_unit', self.env['xyz.booking']._fields)
        self.assertNotIn('list_price', self.env['xyz.booking']._fields)

    # ------------------------------------------------------------ dispatch guard
    def test_gantt_rejects_technician_without_skill(self):
        task = self.make_task('flow-skill')
        skill_type = self.env['hr.skill.type'].create({'name': 'Flow skills'})
        level = self.env['hr.skill.level'].create({'name': 'Flow level', 'skill_type_id': skill_type.id, 'level_progress': 100})
        skill = self.env['hr.skill'].create({'name': 'Cold room service', 'skill_type_id': skill_type.id})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            task.write({'xyz_required_skill_ids': [fields.Command.set(skill.ids)]})
        self.env['hr.employee.skill'].create({'employee_id': self.employee.id, 'skill_type_id': skill_type.id,
                                              'skill_id': skill.id, 'skill_level_id': level.id})
        task.write({'xyz_required_skill_ids': [fields.Command.set(skill.ids)]})
        self.assertEqual(task.xyz_required_skill_ids, skill)

    # ------------------------------------------------------------ invoicing
    def test_acceptance_creates_exactly_one_invoice(self):
        task = self.accepted_task('flow-invoice')
        invoice = task.xyz_invoice_id
        self.assertTrue(invoice)
        self.assertEqual(invoice.state, 'draft')
        self.assertEqual(task.xyz_state, 'done')
        self.assertEqual(len(task.xyz_acceptance_ids), 1)
        self.assertAlmostEqual(invoice.amount_untaxed, self.product.list_price + self.labor.list_price, delta=1000)
        task.action_xyz_accept()
        self.assertEqual(task.xyz_invoice_id, invoice)
        self.assertEqual(len(task.xyz_acceptance_ids), 1)
        self.assertEqual(self.env['account.move'].search_count([('invoice_origin', '=', task._xyz_order().name)]), 1)

    # ------------------------------------------------------------ warehouse flow
    def test_truck_transfer_delivers_actual_quantity(self):
        material = self.material_product('Flow truck filter')
        task = self.make_task('flow-truck', materials=[(material, 3)], stock=3)
        order = task._xyz_order()
        delivery = self.env['stock.picking'].search([('sale_id', '=', order.id), ('picking_type_code', '=', 'outgoing')], limit=1)
        self.assertTrue(delivery)
        # The quoted delivery is never validated before the customer signs.
        with self.assertRaises(UserError), self.cr.savepoint():
            delivery.button_validate()
        self.prepare_truck(task)
        self.assertAlmostEqual(self.truck_quantity(material), 3, places=2)
        self.env['xyz.material'].create({'task_id': task.id, 'product_id': material.id, 'quantity': 1})
        self.consume(task)
        task.action_xyz_accept()
        self.assertEqual(task.xyz_material_ids.move_id.state, 'done')
        self.assertAlmostEqual(task.xyz_material_ids.cost, material.standard_price, places=2)
        # Only the actual quantity reaches the customer; the excess stays on the truck.
        self.assertAlmostEqual(self.truck_quantity(material), 2, places=2)
        invoice_line = task.xyz_invoice_id.invoice_line_ids.filtered(lambda line: line.product_id == material)
        self.assertAlmostEqual(invoice_line.quantity, 1, places=2)

    def test_shortage_blocks_acceptance_without_negative_stock(self):
        material = self.material_product('Flow shortage filter')
        task = self.make_task('flow-shortage', materials=[(material, 2)], stock=2)
        self.prepare_truck(task)
        self.env['xyz.material'].create({'task_id': task.id, 'product_id': material.id, 'quantity': 3})
        self.consume(task)
        with self.assertRaises(UserError), self.cr.savepoint():
            task.action_xyz_accept()
        self.assertEqual(task.xyz_state, 'acceptance')
        self.assertFalse(task.xyz_invoice_id)
        self.assertFalse(task.xyz_material_ids.move_id)
        self.assertAlmostEqual(self.truck_quantity(material), 2, places=2)
        self.assertEqual(self.env['stock.move'].search_count([('product_id', '=', material.id), ('state', '=', 'done')]), 1)

    def test_cancel_requires_returning_truck_stock(self):
        material = self.material_product('Flow return filter')
        task = self.make_task('flow-return', materials=[(material, 1)], stock=1)
        self.prepare_truck(task)
        with self.assertRaises(UserError), self.cr.savepoint():
            task.action_xyz_cancel()
        self.assertEqual(task.xyz_state, 'scheduled')
        self.assertAlmostEqual(self.truck_quantity(material), 1, places=2)

    def test_cancel_releases_reservation(self):
        material = self.material_product('Flow release filter')
        task = self.make_task('flow-release', materials=[(material, 2)], stock=5)
        move = task._xyz_order().picking_ids.move_ids.filtered(lambda line: line.product_id == material)
        self.assertEqual(move.state, 'assigned')
        self.assertAlmostEqual(self.env['stock.quant']._get_available_quantity(material, self.warehouse.lot_stock_id), 3, places=2)
        task.action_xyz_cancel()
        self.assertEqual(task.xyz_state, 'cancel')
        self.assertEqual(move.state, 'cancel')
        self.assertAlmostEqual(self.env['stock.quant']._get_available_quantity(material, self.warehouse.lot_stock_id), 5, places=2)

    # ------------------------------------------------------------ documents after delivery
    def test_reminders_are_sent_once_per_milestone(self):
        task = self.accepted_task('flow-remind')
        invoice = task.xyz_invoice_id
        invoice.action_post()
        invoice.invoice_date_due = fields.Date.today() - timedelta(days=15)
        reminder = self.env['xyz.payment.reminder']
        reminder._cron_remind()
        reminder._cron_remind()
        self.assertEqual(reminder.search_count([('move_id', '=', invoice.id)]), 3)
        reminder._cron_remind()
        self.assertEqual(reminder.search_count([('move_id', '=', invoice.id)]), 3)

    def test_accountant_confirms_cash_and_technician_cannot(self):
        task = self.accepted_task('flow-cash')
        invoice = task.xyz_invoice_id
        invoice.action_post()
        task.with_user(self.user).write({'xyz_cash_reported': invoice.amount_residual})
        with self.assertRaises(AccessError):
            task.with_user(self.user).action_xyz_confirm_cash()
        self.assertFalse(task.xyz_cash_confirmed)
        journal = self.env['account.journal'].search([('type', '=', 'cash'), ('company_id', '=', self.env.company.id)], limit=1)
        if not journal:
            journal = self.env['account.journal'].create({'name': 'Flow cash', 'code': 'FLOWC', 'type': 'cash', 'company_id': self.env.company.id})
        task.with_user(self.accountant).action_xyz_confirm_cash()
        self.assertTrue(task.xyz_cash_confirmed)
        self.assertAlmostEqual(invoice.amount_residual, 0, places=2)

    # ------------------------------------------------------------ KPI view
    def test_report_matches_invoices_timesheets_and_materials(self):
        material = self.material_product('Flow KPI filter')
        task = self.make_task('flow-report', materials=[(material, 2)], stock=5)
        self.prepare_truck(task)
        self.env['xyz.material'].create({'task_id': task.id, 'product_id': material.id, 'quantity': 2})
        self.consume(task)
        task.action_xyz_accept()
        invoice = task.xyz_invoice_id
        invoice.action_post()

        def report():
            self.env.flush_all()
            record = self.env['xyz.service.report'].browse(task.id)
            record.invalidate_recordset()
            return record

        data = report()
        self.assertEqual(data.partner_id, self.partner)
        self.assertEqual(data.employee_id, self.employee)
        self.assertEqual(data.completed, 1)
        self.assertEqual(data.on_time, 1)
        self.assertAlmostEqual(data.hours, sum(task.timesheet_ids.mapped('unit_amount')), places=2)
        self.assertAlmostEqual(data.revenue, invoice.amount_untaxed, places=2)
        self.assertAlmostEqual(data.material_cost, material.standard_price * 2, places=2)
        self.assertAlmostEqual(data.residual, invoice.amount_residual, places=2)
        self.assertAlmostEqual(data.current_amount, invoice.amount_residual, places=2)
        self.assertAlmostEqual(data.overdue, 0, places=2)

        invoice.invoice_date_due = fields.Date.today() - timedelta(days=1)
        self.assertAlmostEqual(report().current_amount, 0, places=2)
        self.assertAlmostEqual(report().overdue, invoice.amount_residual, places=2)

        refund = invoice._reverse_moves(default_values_list=[{'invoice_date': fields.Date.today()}], cancel=False)
        refund.action_post()
        refunded = report()
        self.assertAlmostEqual(refunded.revenue, 0, places=2)
        self.assertAlmostEqual(refunded.residual, 0, places=2)
        self.assertAlmostEqual(refunded.overdue, 0, places=2)
        self.assertAlmostEqual(refunded.material_cost, material.standard_price * 2, places=2)

        move = task.xyz_material_ids.move_id
        returned = self.env['stock.move'].create({
            'name': 'Flow material return', 'product_id': move.product_id.id, 'product_uom_qty': move.quantity,
            'product_uom': move.product_uom.id, 'location_id': move.location_dest_id.id,
            'location_dest_id': move.location_id.id, 'origin_returned_move_id': move.id, 'to_refund': True,
        })
        returned._action_confirm()
        returned.quantity = move.quantity
        returned.picked = True
        returned._action_done()
        self.assertAlmostEqual(report().material_cost, 0, places=2)
