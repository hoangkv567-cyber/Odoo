"""Exercise real Odoo models as demo users; rollback leaves demo fixtures unchanged."""
import base64
import io
from PIL import Image
from datetime import datetime, timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.exceptions import AccessError
import json

try:
    env.ref('xyz_service_core.project_service').company_id = env.company
    technician = env.ref('xyz_seed.tech_user_1')
    employee = env.ref('xyz_seed.tech_1')
    employee.resource_calendar_id.tz = 'Asia/Ho_Chi_Minh'
    desired = datetime.utcnow().replace(hour=2, minute=0, second=0, microsecond=0) + timedelta(days=1)
    while desired.weekday() != 0:
        desired += timedelta(days=1)
    desired += timedelta(days=14)
    booking = env['xyz.booking'].create({
        'token': 'e2e-integration-run', 'partner_id': env.ref('xyz_seed.customer_1').id,
        'equipment_id': env.ref('xyz_seed.equipment_1').id,
        'product_id': env.ref('xyz_service_core.service_compressor').product_variant_id.id,
        'requested_start': desired, 'user_id': env.ref('xyz_seed.user_sale').id,
    })
    product = env.ref('xyz_seed.material_1')
    order = booking.sale_id
    env['sale.order.line'].create({'order_id': order.id, 'product_id': product.id, 'product_uom_qty': 2})
    order.with_user(env.ref('xyz_seed.user_sale')).action_confirm()
    try:
        order.picking_ids.with_user(env.ref('xyz_seed.user_warehouse')).button_validate()
        raise AssertionError('Quoted delivery was validated before service acceptance')
    except UserError:
        pass
    task = order.xyz_task_id
    task.with_user(env.ref('xyz_seed.user_dispatch')).xyz_dispatch_move(employee.id, desired, desired + timedelta(hours=2))
    task.with_user(env.ref('xyz_seed.user_warehouse')).action_xyz_prepare_materials()
    transfer = task.xyz_transfer_id
    assert transfer.state == 'assigned', transfer.state
    for move in transfer.move_ids:
        move.quantity = move.product_uom_qty
        move.picked = True
    transfer.button_validate()
    assert transfer.state == 'done'
    task.with_user(technician).action_xyz_check_in()
    task._xyz_system_write({'xyz_timer_start': fields.Datetime.now() - timedelta(hours=1)})
    task.with_user(technician).action_xyz_check_out()
    env['xyz.material'].with_user(technician).create({'task_id': task.id, 'product_id': product.id, 'quantity': 1})
    # Valid one-pixel PNG; the automated test checks attachments, UAT supplies equipment photos.
    buffer = io.BytesIO()
    Image.new('RGB', (100, 50), 'white').save(buffer, format='PNG')
    png = base64.b64encode(buffer.getvalue())
    task.with_user(technician).write({'xyz_checked_safety': True, 'xyz_checked_service': True, 'xyz_checked_test': True,
                                    'xyz_before': png, 'xyz_after': png, 'xyz_signature': png, 'xyz_signer': 'Customer test'})
    try:
        with env.cr.savepoint():
            task.xyz_material_ids.with_user(technician).quantity = 3
            task.with_user(technician).action_xyz_accept()
            raise AssertionError('Insufficient stock was accepted')
    except UserError:
        pass
    assert task.xyz_state == 'acceptance' and not task.xyz_invoice_id
    task.with_user(technician).action_xyz_accept()
    invoice = task.xyz_invoice_id
    task.with_user(technician).action_xyz_accept()
    assert task.xyz_invoice_id == invoice
    assert len(task.xyz_acceptance_ids) == 1
    signed_total = json.loads(task.xyz_acceptance_ids.snapshot)['total']
    assert abs(signed_total - invoice.amount_total) < 0.01, (signed_total, invoice.amount_total)
    pdf = env['ir.attachment'].search([('res_model', '=', 'xyz.acceptance'), ('res_id', '=', task.xyz_acceptance_ids.id), ('mimetype', '=', 'application/pdf')], limit=1)
    assert base64.b64decode(pdf.datas).startswith(b'%PDF')
    try:
        pdf.with_user(env.ref('xyz_seed.tech_user_2')).read(['datas'])
        raise AssertionError('Another technician could read the signed PDF')
    except AccessError:
        pass
    assert task.xyz_material_ids.move_id.state == 'done'
    assert abs(env['stock.quant']._get_available_quantity(product, employee.xyz_location_id) - 1) < 0.0001
    assert invoice.state == 'draft'
    material_line = invoice.invoice_line_ids.filtered(lambda line: line.product_id == product)
    assert material_line.quantity == 1, material_line.quantity
    first_acceptance = task.xyz_acceptance_ids
    task.with_user(env.ref('xyz_seed.user_manager')).action_xyz_revise()
    assert invoice.state == 'cancel'
    assert first_acceptance.exists()
    assert not task.xyz_signature
    assert abs(env['stock.quant']._get_available_quantity(product, employee.xyz_location_id) - 2) < 0.0001
    task.with_user(technician).write({'xyz_signature': png, 'xyz_signer': 'Customer revised'})
    task.with_user(technician).action_xyz_accept()
    invoice = task.xyz_invoice_id
    assert len(task.xyz_acceptance_ids) == 2
    invoice.with_user(env.ref('xyz_seed.user_accountant')).action_post()
    assert invoice.state == 'posted'
    invoice.invoice_date_due = fields.Date.today() - timedelta(days=15)
    reminders = env['xyz.payment.reminder']
    reminders._cron_remind()
    reminders._cron_remind()
    assert reminders.search_count([('move_id', '=', invoice.id)]) == 3
    balance = invoice.amount_residual
    provider = env['payment.provider'].search([('code', '=', 'demo')], limit=1)
    def transaction(reference, amount):
        return env['payment.transaction'].create({
            'provider_id': provider.id, 'payment_method_id': provider.payment_method_ids[:1].id,
            'reference': reference, 'amount': amount, 'currency_id': invoice.currency_id.id,
            'partner_id': invoice.partner_id.id, 'operation': 'online_direct',
            'invoice_ids': [fields.Command.set(invoice.ids)],
        })
    failed = transaction('XYZ-E2E-FAIL', balance)
    failed.action_demo_set_error()
    assert failed.state == 'error' and invoice.amount_residual == balance
    partial = transaction('XYZ-E2E-PARTIAL', invoice.currency_id.round(balance / 2))
    partial.action_demo_set_done()
    partial._post_process()
    assert partial.state == 'done'
    assert 0 < invoice.amount_residual < balance
    task.with_user(technician).write({'xyz_cash_reported': invoice.amount_residual})
    task.with_user(env.ref('xyz_seed.user_accountant')).action_xyz_confirm_cash()
    assert task.xyz_cash_confirmed
    assert invoice.amount_residual == 0, invoice.amount_residual
    env.flush_all()
    report = env['xyz.service.report'].browse(task.id)
    assert report.completed == 1
    assert abs(report.revenue - invoice.amount_untaxed) < 0.01
    refund = invoice._reverse_moves(default_values_list=[{'invoice_date': fields.Date.today()}], cancel=False)
    refund.action_post()
    env.flush_all()
    report.invalidate_recordset()
    assert abs(report.revenue) < 0.01, report.revenue
    reorder = env.ref('xyz_seed.reorder_15')
    env['stock.quant']._update_available_quantity(reorder.product_id, reorder.location_id, -20)
    env.flush_all()
    reorder.invalidate_recordset()
    reorder._procure_orderpoint_confirm()
    assert env['purchase.order.line'].search_count([('product_id', '=', reorder.product_id.id), ('order_id.state', '=', 'draft')])
    print('E2E PASS: booking, Sales, Gantt, truck, shortage rollback, technician, PDF, revision, invoicing, reminders dedup, failed/partial demo payment, cash, report, replenishment RFQ')
finally:
    env.cr.rollback()
