"""The KPI dashboard is a module of its own, so it carries its own Vietnamese catalogue.

`xyz_service_core/tests/test_i18n.py` pins the core terms. These cases keep the reporting
module honest too: without them the director could open a Vietnamese system and find an
English dashboard, because each addon ships a separate .po file.
"""
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestXYZReportingLanguages(TransactionCase):
    def label(self, lang, field, model='xyz.service.report'):
        return self.env[model].with_context(lang=lang).fields_get([field])[field]['string']

    def test_field_labels_follow_the_language(self):
        self.assertEqual(self.label('en_US', 'overdue'), 'Overdue AR')
        self.assertEqual(self.label('vi_VN', 'overdue'), 'Công nợ quá hạn')
        self.assertEqual(self.label('vi_VN', 'current_amount'), 'Công nợ trong hạn')
        self.assertEqual(self.label('vi_VN', 'on_time_rate'), 'Tỷ lệ đúng hạn (%)')
        self.assertEqual(self.label('vi_VN', 'revenue'), 'Doanh thu')
        self.assertEqual(self.label('vi_VN', 'employee_id'), 'Kỹ thuật viên')

    def model_name(self, lang, model):
        # `_description` is a plain Python attribute; the translatable copy of it is
        # `ir.model.name`, which is what the interface reads (many2one labels, settings).
        record = self.env['ir.model'].search([('model', '=', model)])
        return record.with_context(lang=lang).name

    def test_model_and_menu_names_follow_the_language(self):
        self.assertEqual(self.model_name('en_US', 'xyz.service.report'), 'Service performance report')
        self.assertEqual(self.model_name('vi_VN', 'xyz.service.report'), 'Báo cáo hiệu quả dịch vụ')
        menu = self.env.ref('xyz_service_reporting.menu_report')
        self.assertEqual(menu.with_context(lang='en_US').name, 'Management reports')
        self.assertEqual(menu.with_context(lang='vi_VN').name, 'Báo cáo quản trị')

    def test_chart_titles_follow_the_language(self):
        revenue = self.env.ref('xyz_service_reporting.report_graph_revenue')
        self.assertIn('Revenue and material cost', revenue.with_context(lang='en_US').arch)
        # The arch is XML: ampersands come back escaped, exactly as the browser renders them.
        self.assertIn('Doanh thu &amp; Chi phí vật tư', revenue.with_context(lang='vi_VN').arch)
        receivable = self.env.ref('xyz_service_reporting.report_graph_receivable')
        self.assertIn('Receivables by customer', receivable.with_context(lang='en_US').arch)
        self.assertIn('Công nợ theo khách hàng', receivable.with_context(lang='vi_VN').arch)
