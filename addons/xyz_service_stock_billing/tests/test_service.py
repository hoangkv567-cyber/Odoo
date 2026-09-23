import base64
from datetime import datetime, timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import AccessError, UserError, ValidationError


@tagged('post_install', '-at_install')
class TestXYZService(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test customer', 'email': 'test@example.test'})
        cls.equipment = cls.env['xyz.equipment'].create({'name': 'Test compressor', 'partner_id': cls.partner.id})
        cls.product = cls.env.ref('xyz_service_core.service_compressor').product_variant_id
        cls.user = cls.env['res.users'].create({'name': 'Test mechanic', 'login': 'test-mechanic', 'groups_id': [fields.Command.set([cls.env.ref('xyz_service_core.group_technician').id])]})
        cls.employee = cls.env['hr.employee'].create({'name': 'Test mechanic', 'user_id': cls.user.id, 'resource_calendar_id': cls.env.company.resource_calendar_id.id})
        # Fixed Monday 09:00 UTC in the calendar timezone UTC.
        cls.employee.resource_calendar_id.tz = 'UTC'
        cls.env.ref('xyz_service_core.project_service').company_id = cls.env.company

    def booking(self, token='test-booking'):
        return self.env['xyz.booking'].create({'token': token, 'partner_id': self.partner.id, 'equipment_id': self.equipment.id, 'product_id': self.product.id, 'requested_start': datetime(2027, 1, 4, 9)})

    def task(self):
        booking = self.booking()
        booking.sale_id.action_confirm()
        task = booking.sale_id.xyz_task_id
        task.write({'xyz_employee_id': self.employee.id})
        task.action_xyz_schedule()
        return task

    def test_booking_has_crm_and_priced_labor(self):
        booking = self.booking()
        self.assertTrue(booking.lead_id)
        self.assertEqual(len(booking.sale_id.order_line), 2)
        self.assertGreater(booking.sale_id.amount_total, 0)

    def test_confirm_is_idempotent(self):
        booking = self.booking()
        booking.sale_id.action_confirm()
        task = booking.sale_id.xyz_task_id
        booking.sale_id.action_confirm()
        self.assertEqual(booking.sale_id.xyz_task_id, task)
        self.assertEqual(self.env['project.task'].search_count([('xyz_booking_id', '=', booking.id)]), 1)

    def test_gantt_rejects_overlap(self):
        self.task()
        second = self.booking('second')
        second.sale_id.action_confirm()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            second.sale_id.xyz_task_id.write({'xyz_employee_id': self.employee.id})

    def test_gantt_rejects_outside_shift(self):
        task = self.task()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            task.write({'xyz_start': datetime(2027, 1, 4, 1), 'xyz_end': datetime(2027, 1, 4, 2)})

    def test_timer_is_idempotent(self):
        task = self.task()
        task.with_user(self.user).action_xyz_check_in()
        start = task.xyz_timer_start
        task.with_user(self.user).action_xyz_check_in()
        self.assertEqual(start, task.xyz_timer_start)
        task.with_user(self.user).action_xyz_check_out()
        task.with_user(self.user).action_xyz_check_out()
        self.assertEqual(len(task.timesheet_ids), 1)

    def test_missing_acceptance_rejected(self):
        task = self.task()
        task.action_xyz_check_in()
        task.action_xyz_check_out()
        with self.assertRaises(UserError), self.cr.savepoint():
            task.action_xyz_accept()
        self.assertNotEqual(task.xyz_state, 'done')

    def test_technician_cannot_forge_state(self):
        task = self.task()
        with self.assertRaises(AccessError):
            task.with_user(self.user).write({'xyz_state': 'done'})

    def test_technician_cannot_reassign(self):
        task = self.task()
        with self.assertRaises(AccessError):
            task.with_user(self.user).write({'xyz_employee_id': False})

    def test_technician_cannot_see_other_task(self):
        task = self.task()
        other = self.booking('other')
        other.sale_id.action_confirm()
        visible = self.env['project.task'].with_user(self.user).search([('xyz_booking_id', '!=', False)])
        self.assertIn(task, visible)
        self.assertNotIn(other.sale_id.xyz_task_id, visible)

    def test_material_positive(self):
        task = self.task()
        product = self.env['product.product'].create({'name': 'Oil', 'type': 'consu', 'is_storable': True})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env['xyz.material'].create({'task_id': task.id, 'product_id': product.id, 'quantity': -1})

    def test_material_evidence_not_client_writable(self):
        task = self.task()
        product = self.env['product.product'].create({'name': 'Oil', 'type': 'consu', 'is_storable': True})
        with self.assertRaises(AccessError):
            self.env['xyz.material'].with_user(self.user).create({'task_id': task.id, 'product_id': product.id, 'quantity': 1, 'cost': 1})

    def test_non_dispatcher_cannot_read_board(self):
        with self.assertRaises(AccessError):
            self.env['project.task'].with_user(self.user).xyz_dispatch_data()

    def test_technician_can_record_actual_material(self):
        task = self.task()
        product = self.env['product.product'].create({'name': 'Oil', 'type': 'consu', 'is_storable': True})
        line = self.env['xyz.material'].with_user(self.user).create({'task_id': task.id, 'product_id': product.id, 'quantity': 1})
        self.assertEqual(line.task_id, task)

    def test_cancel_releases_job(self):
        task = self.task()
        task.action_xyz_cancel()
        self.assertEqual(task.xyz_state, 'cancel')
        self.assertEqual(task.xyz_booking_id.sale_id.state, 'cancel')

    def test_cancel_working_job_rejected(self):
        task = self.task()
        task.action_xyz_check_in()
        with self.assertRaises(UserError), self.cr.savepoint():
            task.action_xyz_cancel()

    def test_unassigned_gantt_destination_rejected(self):
        task = self.task()
        with self.assertRaises(UserError), self.cr.savepoint():
            task.xyz_dispatch_move(0, task.xyz_start, task.xyz_end)

    def test_accountant_cannot_sign_for_customer(self):
        task = self.task()
        accountant = self.env['res.users'].create({'name': 'Accountant test', 'login': 'xyz-accountant-test', 'groups_id': [fields.Command.set([self.env.ref('account.group_account_invoice').id])]})
        with self.assertRaises(AccessError):
            task.with_user(accountant).write({'xyz_signer': 'Forged approval'})

    def test_other_technician_cannot_read_pdf(self):
        task = self.task()
        acceptance = self.env['xyz.acceptance'].create({'name': 'Signed evidence', 'task_id': task.id, 'signed_at': fields.Datetime.now(), 'snapshot': '{}'})
        attachment = self.env['ir.attachment'].create({'name': 'evidence.pdf', 'datas': base64.b64encode(b'%PDF-test'), 'res_model': 'xyz.acceptance', 'res_id': acceptance.id})
        other = self.env['res.users'].create({'name': 'Other mechanic', 'login': 'other-mechanic', 'groups_id': [fields.Command.set([self.env.ref('xyz_service_core.group_technician').id])]})
        attachment.read(['datas'])  # Warm privileged cache before testing the unprivileged read.
        self.assertTrue(attachment.with_user(self.user).read(['datas']))
        with self.assertRaises(AccessError):
            attachment.with_user(other).read(['datas'])
