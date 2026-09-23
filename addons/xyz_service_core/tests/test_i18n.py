"""Bilingual interface: English is the source language, Vietnamese comes from i18n/vi_VN.po.

The plan asks for a system that can be switched between English and Vietnamese, so these
cases pin down the two halves of that promise: both languages are installed and selectable,
and the same term really renders differently per language — model labels, selection values,
view arch (including the website pages) and the menus.
"""
from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestXYZLanguages(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.task = cls.env['project.task']

    def labels(self, lang, model='project.task', names=('xyz_checked_safety',)):
        return self.env[model].with_context(lang=lang).fields_get(list(names))

    def test_both_languages_are_installed_and_selectable(self):
        languages = self.env['res.lang'].search([('code', 'in', ('en_US', 'vi_VN'))])
        self.assertEqual(set(languages.mapped('code')), {'en_US', 'vi_VN'})
        self.assertTrue(all(languages.mapped('active')), languages.mapped('active'))

    def test_field_label_follows_the_language(self):
        self.assertEqual(self.labels('en_US')['xyz_checked_safety']['string'], 'Safety checked')
        self.assertEqual(self.labels('vi_VN')['xyz_checked_safety']['string'], 'Đã kiểm tra an toàn')

    def test_selection_labels_follow_the_language(self):
        selection = lambda lang: dict(
            self.env['project.task'].with_context(lang=lang).fields_get(['xyz_state'])['xyz_state']['selection']
        )
        self.assertEqual(selection('en_US')['new'], 'Awaiting dispatch')
        self.assertEqual(selection('vi_VN')['new'], 'Chờ điều phối')
        self.assertEqual(selection('vi_VN')['acceptance'], 'Chờ nghiệm thu')

    def test_view_terms_follow_the_language(self):
        view = self.env.ref('xyz_service_core.view_field_job_form')
        english = view.with_context(lang='en_US').arch
        vietnamese = view.with_context(lang='vi_VN').arch
        self.assertIn('Sign acceptance and create draft invoice', english)
        self.assertIn('Ký nghiệm thu và lập hóa đơn nháp', vietnamese)
        self.assertIn('Xác nhận lịch', vietnamese)

    def test_menu_and_action_names_follow_the_language(self):
        menu = self.env.ref('xyz_service_core.menu_jobs')
        self.assertEqual(menu.with_context(lang='en_US').name, 'Field jobs')
        self.assertEqual(menu.with_context(lang='vi_VN').name, 'Công việc hiện trường')
        self.assertEqual(
            self.env.ref('xyz_service_core.group_technician').with_context(lang='vi_VN').name, 'Kỹ thuật viên'
        )

    def test_website_pages_follow_the_language(self):
        thanks = self.env.ref('xyz_service_core.booking_thanks')
        self.assertIn('Maintenance request received', thanks.with_context(lang='en_US').arch)
        self.assertIn('Đã nhận yêu cầu bảo dưỡng', thanks.with_context(lang='vi_VN').arch)
        booking = self.env.ref('xyz_service_core.booking_page')
        self.assertIn('Send the request and get a quotation', booking.with_context(lang='en_US').arch)
        self.assertIn('Gửi yêu cầu và nhận báo giá', booking.with_context(lang='vi_VN').arch)

    def test_python_messages_follow_the_language(self):
        english = self.env['xyz.booking'].with_context(lang='en_US')._fields['token'].string
        self.assertEqual(english, 'Token')
        self.assertEqual(self.labels('vi_VN', 'xyz.booking', ('token',))['token']['string'], 'Mã xác thực')

    def test_technician_can_switch_their_own_language(self):
        """The top-bar switcher writes res.users.lang as the current user, not as an admin."""
        technician = self.env['res.users'].create({
            'name': 'Language tester', 'login': 'language-tester', 'email': 'language-tester@example.test',
            'groups_id': [fields.Command.set([self.env.ref('xyz_service_core.group_technician').id])],
        })
        technician.with_user(technician).write({'lang': 'vi_VN'})
        self.assertEqual(technician.lang, 'vi_VN')
        self.assertEqual(self.env['res.users'].browse(technician.id).lang, 'vi_VN')
        technician.with_user(technician).write({'lang': 'en_US'})
        self.assertEqual(technician.lang, 'en_US')

    def test_pdf_report_uses_the_requested_language(self):
        self.env.ref('xyz_service_core.project_service').company_id = self.env.company
        partner = self.env['res.partner'].create({'name': 'Bilingual customer', 'email': 'bilingual@example.test'})
        equipment = self.env['xyz.equipment'].create({'name': 'Bilingual compressor', 'partner_id': partner.id})
        booking = self.env['xyz.booking'].create({
            'token': 'i18n-booking', 'partner_id': partner.id, 'equipment_id': equipment.id,
            'product_id': self.env.ref('xyz_service_core.service_compressor').product_variant_id.id,
            'requested_start': fields.Datetime.now(),
        })
        booking.sale_id.action_confirm()
        acceptance = self.env['xyz.acceptance'].sudo().create({
            'task_id': booking.sale_id.xyz_task_id.id, 'name': booking.name,
            'signed_at': fields.Datetime.now(), 'snapshot': '{"hours": 1}',
        })
        english, _ = self.env['ir.actions.report'].sudo().with_context(lang='en_US')._render_qweb_pdf(
            'xyz_service_core.report_acceptance', res_ids=acceptance.ids
        )
        vietnamese, _ = self.env['ir.actions.report'].sudo().with_context(lang='vi_VN')._render_qweb_pdf(
            'xyz_service_core.report_acceptance', res_ids=acceptance.ids
        )
        self.assertNotEqual(english, vietnamese)
