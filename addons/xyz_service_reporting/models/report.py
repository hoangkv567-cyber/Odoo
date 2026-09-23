from odoo import fields, models, tools


class ServiceReport(models.Model):
    _name = 'xyz.service.report'
    _description = 'Service performance report'
    _auto = False
    _rec_name = 'name'

    name = fields.Char(readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Technician', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)
    date = fields.Datetime(readonly=True)
    state = fields.Char(readonly=True)
    hours = fields.Float(readonly=True)
    material_cost = fields.Float(readonly=True)
    revenue = fields.Float(readonly=True)
    residual = fields.Float(readonly=True, string='Outstanding AR')
    current_amount = fields.Float(readonly=True, string='Current AR (not yet due)')
    overdue = fields.Float(readonly=True, string='Overdue AR')
    completed = fields.Integer(readonly=True)
    on_time = fields.Integer(readonly=True)
    on_time_rate = fields.Float(readonly=True, aggregator='avg', string='On-time rate (%)')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute('''
            CREATE VIEW xyz_service_report AS
            SELECT t.id, t.name, t.xyz_employee_id employee_id, t.company_id, b.partner_id,
                   t.xyz_start date, t.xyz_state state,
                   COALESCE(h.hours, 0) hours, COALESCE(m.cost, 0) material_cost,
                   COALESCE(a.revenue, 0) revenue, COALESCE(a.residual, 0) residual,
                   COALESCE(a.residual, 0) - COALESCE(a.overdue, 0) current_amount,
                   COALESCE(a.overdue, 0) overdue,
                   CASE WHEN t.xyz_state = 'done' THEN 1 ELSE 0 END completed,
                   CASE WHEN t.xyz_state = 'done' AND t.xyz_finished_at <= t.xyz_end THEN 1 ELSE 0 END on_time,
                   CASE WHEN t.xyz_state = 'done' THEN CASE WHEN t.xyz_finished_at <= t.xyz_end THEN 100.0 ELSE 0.0 END ELSE NULL END on_time_rate
            FROM project_task t
            LEFT JOIN xyz_booking b ON b.id = t.xyz_booking_id
            LEFT JOIN (
                SELECT COALESCE(reversed_entry_id, id) invoice_id,
                    SUM(CASE WHEN move_type = 'out_refund' THEN -amount_untaxed ELSE amount_untaxed END) revenue,
                    SUM(CASE WHEN move_type = 'out_refund' THEN -amount_residual ELSE amount_residual END) residual,
                    SUM(CASE WHEN invoice_date_due < CURRENT_DATE THEN CASE WHEN move_type = 'out_refund' THEN -amount_residual ELSE amount_residual END ELSE 0 END) overdue
                FROM account_move WHERE state = 'posted' AND move_type IN ('out_invoice', 'out_refund')
                GROUP BY COALESCE(reversed_entry_id, id)
            ) a ON a.invoice_id = t.xyz_invoice_id
            LEFT JOIN (SELECT task_id, SUM(unit_amount) hours FROM account_analytic_line GROUP BY task_id) h ON h.task_id = t.id
            LEFT JOIN (
                SELECT material.task_id, SUM(material.cost * (1 - LEAST(1, COALESCE(returns.qty, 0) / NULLIF(material.quantity, 0)))) cost
                FROM xyz_material material LEFT JOIN (
                    SELECT origin_returned_move_id, SUM(quantity) qty FROM stock_move
                    WHERE state = 'done' GROUP BY origin_returned_move_id
                ) returns ON returns.origin_returned_move_id = material.move_id
                GROUP BY material.task_id
            ) m ON m.task_id = t.id
            WHERE t.xyz_booking_id IS NOT NULL
        ''')
