"""Run inside `odoo shell -d xyz_demo`; creates repeatable educational fixtures."""
import os
import secrets
from datetime import datetime, timedelta

from odoo import fields

company = env.company
env.ref('xyz_service_core.project_service').company_id = company
company.write({'name': 'XYZ Industrial Services', 'country_id': env.ref('base.vn').id,
               'currency_id': env.ref('base.VND').id, 'email': 'service@xyz.example.test',
               'phone': '+84 28 5555 0100', 'street': 'Khu công nghiệp XYZ, TP. Hồ Chí Minh'})
if not company.chart_template:
    env['account.chart.template'].try_loading('generic_coa', company, install_demo=False)
env['ir.config_parameter'].sudo().set_param('web.base.url', 'http://localhost:8069')
env['ir.config_parameter'].sudo().set_param('report.url', 'http://odoo:8069')
lang_vi = env['res.lang'].search([('code', '=', 'vi_VN')], limit=1)
if lang_vi and not lang_vi.active:
    env['res.lang']._activate_lang('vi_VN')
env.ref('base.user_admin').write({'tz': 'Asia/Ho_Chi_Minh', 'lang': 'vi_VN'})
company.resource_calendar_id.tz = 'Asia/Ho_Chi_Minh'

def fixture(model, key, values):
    identifier = 'xyz_seed.' + key
    record = env.ref(identifier, raise_if_not_found=False)
    if not record:
        record = env[model].create(values)
        env['ir.model.data'].create({'module': 'xyz_seed', 'name': key, 'model': model, 'res_id': record.id, 'noupdate': True})
    return record

password = os.environ.get('XYZ_DEMO_PASSWORD')
if not password:
    raise RuntimeError('XYZ_DEMO_PASSWORD must be supplied to seed demo accounts')
roles = {
    'director': ['xyz_service_core.group_director'],
    'manager': ['xyz_service_core.group_manager', 'stock.group_stock_manager', 'purchase.group_purchase_manager', 'account.group_account_manager'],
    'sale': ['sales_team.group_sale_salesman'],
    'dispatch': ['xyz_service_core.group_dispatcher'],
    'warehouse': ['stock.group_stock_manager', 'purchase.group_purchase_manager', 'xyz_service_core.group_dispatcher'],
    'accountant': ['account.group_account_manager'],
}
users = {}
for login, groups in roles.items():
    users[login] = fixture('res.users', 'user_' + login, {
        'name': 'XYZ ' + login.title(), 'login': login + '@xyz.test', 'password': password,
        'email': login + '@xyz.test', 'tz': 'Asia/Ho_Chi_Minh', 'lang': 'vi_VN',
        'groups_id': [fields.Command.set([env.ref(group).id for group in groups])],
    })
# The demo team works in Vietnamese; every user can still switch to English from the top bar.
for user in users.values():
    user.write({'lang': 'vi_VN'})
env.ref('base.user_admin').write({'password': password})
users['accountant'].write({'groups_id': [fields.Command.set([env.ref('account.group_account_manager').id])]})
env['ir.config_parameter'].sudo().set_param('xyz.salesperson_id', users['sale'].id)
skill_type = fixture('hr.skill.type', 'skill_type', {'name': 'Bảo dưỡng công nghiệp'})
level = fixture('hr.skill.level', 'skill_level', {'name': 'Đạt chuẩn', 'skill_type_id': skill_type.id, 'level_progress': 100})
skill = fixture('hr.skill', 'skill_mechanical', {'name': 'Bảo dưỡng cơ khí', 'skill_type_id': skill_type.id})
for index in range(1, 5):
    user = fixture('res.users', 'tech_user_' + str(index), {
        'name': 'Thợ bảo dưỡng %s' % index, 'login': 'tech%s@xyz.test' % index,
        'password': password, 'tz': 'Asia/Ho_Chi_Minh', 'lang': 'vi_VN',
        'groups_id': [fields.Command.set([env.ref('xyz_service_core.group_technician').id])],
    })
    user.write({'lang': 'vi_VN'})
    employee = fixture('hr.employee', 'tech_' + str(index), {
        'name': user.name, 'user_id': user.id, 'company_id': company.id,
        'xyz_area': 'TP. Hồ Chí Minh' if index < 3 else 'Bình Dương',
        'resource_calendar_id': company.resource_calendar_id.id,
        'xyz_location_id': env.ref('xyz_service_stock_billing.truck_%s' % index).id if index <= 2 else False,
    })
    fixture('hr.employee.skill', 'tech_skill_' + str(index), {
        'employee_id': employee.id, 'skill_id': skill.id, 'skill_type_id': skill_type.id, 'skill_level_id': level.id,
    })

retail = fixture('product.pricelist', 'retail', {'name': 'XYZ Khách lẻ', 'currency_id': company.currency_id.id})
env['ir.default'].set('res.partner', 'property_product_pricelist', retail.id, company_id=company.id)
env['ir.config_parameter'].sudo().set_param('xyz.retail_pricelist_id', retail.id)
env['product.pricelist'].search([('company_id', 'in', [False, company.id])]).write({'currency_id': company.currency_id.id})
b2b = fixture('product.pricelist', 'b2b', {'name': 'XYZ B2B (-10%)', 'currency_id': company.currency_id.id,
    'item_ids': [fields.Command.create({'applied_on': '3_global', 'compute_price': 'percentage', 'percent_price': 10})]})
term = fixture('account.payment.term', 'net30', {'name': 'XYZ B2B 30 ngày',
    'line_ids': [fields.Command.create({'value': 'percent', 'value_amount': 100, 'nb_days': 30})]})
website = env['website'].search([], limit=1)
website.write({'name': 'XYZ Industrial Services', 'company_id': company.id})
for index in range(1, 11):
    partner = fixture('res.partner', 'customer_' + str(index), {
        'name': 'Khách hàng XYZ %02d' % index, 'email': 'customer%s@example.test' % index, 'customer_rank': 1,
        'street': '%s Đường Công nghiệp, TP. Hồ Chí Minh' % index, 'user_id': users['sale'].id,
        'property_product_pricelist': b2b.id if index <= 5 else retail.id,
        'property_payment_term_id': term.id if index <= 5 else False,
    })
    partner.write({'customer_rank': 1, 'user_id': users['sale'].id})
    fixture('xyz.equipment', 'equipment_' + str(index), {
        'name': 'Thiết bị XYZ %02d' % index, 'serial': 'XYZ-%04d' % index,
        'partner_id': partner.id, 'address': partner.street, 'user_id': users['sale'].id,
    })
    if index in (1, 6):
        portal = fixture('res.users', 'portal_' + str(index), {
            'name': partner.name, 'partner_id': partner.id, 'login': 'customer%s@xyz.test' % index,
            'password': password, 'groups_id': [fields.Command.set([env.ref('base.group_portal').id])],
            'tz': 'Asia/Ho_Chi_Minh', 'lang': 'vi_VN',
        })
        portal.write({'lang': 'vi_VN'})
suppliers = [fixture('res.partner', 'vendor_' + str(i), {'name': 'Nhà cung cấp %s' % i, 'supplier_rank': 1, 'email': 'vendor%s@example.test' % i}) for i in range(1, 4)]
warehouse = env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)
warehouse.write({'name': 'XYZ Kho tổng', 'code': 'XYZ'})
for index in range(1, 16):
    product = fixture('product.product', 'material_' + str(index), {
        'name': ['Lọc dầu', 'Dầu máy', 'Gioăng', 'Dây đai', 'Lọc gió'][(index - 1) % 5] + ' %02d' % index,
        'type': 'consu', 'is_storable': True, 'list_price': 100000 + 10000 * index,
        'standard_price': 50000 + 5000 * index, 'invoice_policy': 'delivery',
        'seller_ids': [fields.Command.create({'partner_id': suppliers[(index - 1) % 3].id, 'price': 50000 + 5000 * index})],
    })
    if not env.ref('xyz_seed.stock_' + str(index), raise_if_not_found=False):
        quant = env['stock.quant']._update_available_quantity(product, warehouse.lot_stock_id, 20)[0]
        # Mark initialization separately; repeat seeding must not replenish sold stock.
        env['ir.model.data'].create({'module': 'xyz_seed', 'name': 'stock_' + str(index), 'model': 'product.product', 'res_id': product.id, 'noupdate': True})
    fixture('stock.warehouse.orderpoint', 'reorder_' + str(index), {
        'product_id': product.id, 'location_id': warehouse.lot_stock_id.id,
        'product_min_qty': 5, 'product_max_qty': 20, 'route_id': env.ref('purchase_stock.route_warehouse0_buy').id,
    })
for xmlid in ('xyz_service_core.service_compressor', 'xyz_service_core.service_cooling'):
    env.ref(xmlid).write({'xyz_required_skill_ids': [fields.Command.set(skill.ids)], 'taxes_id': [fields.Command.clear()]})
env.ref('xyz_service_stock_billing.product_labor').write({'taxes_id': [fields.Command.clear()]})
provider = env['payment.provider'].search([('code', '=', 'demo')], limit=1)
if provider:
    provider.write({'state': 'test', 'is_published': True})
for index in range(1, 5):
    desired = datetime.utcnow().replace(hour=2, minute=0, second=0, microsecond=0) + timedelta(days=index)
    while desired.weekday() >= 5:
        desired += timedelta(days=1)
    booking = fixture('xyz.booking', 'booking_' + str(index), {
        'token': 'xyz-seed-booking-' + str(index),
        'partner_id': env.ref('xyz_seed.customer_' + str(index)).id,
        'equipment_id': env.ref('xyz_seed.equipment_' + str(index)).id,
        'product_id': env.ref('xyz_service_core.service_compressor' if index % 2 else 'xyz_service_core.service_cooling').product_variant_id.id,
        'requested_start': desired, 'user_id': users['sale'].id,
    })
    if booking.sale_id.state in ('draft', 'sent'):
        booking.sale_id.action_confirm()
    if index <= 2 and booking.sale_id.xyz_task_id.xyz_state == 'new':
        employee = env.ref('xyz_seed.tech_' + str(index))
        booking.sale_id.xyz_task_id.xyz_dispatch_move(employee.id, desired, desired + timedelta(hours=2))

# Completed, invoiced service history: the KPI dashboard and the director demo need real figures.
# Every job below runs through the normal workflow, so stock, timesheets, acceptance and
# invoicing stay consistent with what the application produces live.
photo = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg=='
payment_journal = env['account.journal'].search([('company_id', '=', company.id), ('type', 'in', ('bank', 'cash'))], limit=1)
history = [
    {'key': 'history_paid', 'customer': 1, 'technician': 1, 'service': 'xyz_service_core.service_compressor', 'quantity': 2, 'worked': 3, 'planned': 3, 'weeks_ago': 6, 'due_days': -21, 'payment': 'full'},
    {'key': 'history_overdue', 'customer': 5, 'technician': 2, 'service': 'xyz_service_core.service_cooling', 'quantity': 1, 'worked': 3, 'planned': 2, 'weeks_ago': 3, 'due_days': -14, 'payment': 'none'},
    {'key': 'history_partial', 'customer': 7, 'technician': 1, 'service': 'xyz_service_core.service_compressor', 'quantity': 2, 'worked': 2, 'planned': 3, 'weeks_ago': 1, 'due_days': 21, 'payment': 'half'},
]
for spec in history:
    start = (datetime.utcnow() - timedelta(weeks=spec['weeks_ago'])).replace(hour=2, minute=0, second=0, microsecond=0)
    while start.weekday() >= 5:
        start += timedelta(days=1)
    booking = fixture('xyz.booking', spec['key'], {
        'token': 'xyz-seed-' + spec['key'],
        'partner_id': env.ref('xyz_seed.customer_%s' % spec['customer']).id,
        'equipment_id': env.ref('xyz_seed.equipment_%s' % spec['customer']).id,
        'product_id': env.ref(spec['service']).product_variant_id.id,
        'requested_start': start, 'user_id': users['sale'].id,
    })
    order = booking.sale_id
    material = env.ref('xyz_seed.material_1')
    if order.state in ('draft', 'sent'):
        env['stock.quant']._update_available_quantity(material, warehouse.lot_stock_id, spec['quantity'])
        env['sale.order.line'].create({'order_id': order.id, 'product_id': material.id, 'product_uom_qty': spec['quantity']})
        order.action_confirm()
    task = order.xyz_task_id
    if task.xyz_state != 'new':
        continue  # An earlier seed run already completed this job.
    task.xyz_dispatch_move(env.ref('xyz_seed.tech_%s' % spec['technician']).id, start, start + timedelta(hours=spec['planned']))
    task.action_xyz_prepare_materials()
    transfer = task.xyz_transfer_id
    for move in transfer.move_ids:
        move.quantity = move.product_uom_qty
        move.picked = True
    transfer.button_validate()
    task.action_xyz_check_in()
    task._xyz_system_write({'xyz_timer_start': fields.Datetime.now() - timedelta(hours=spec['worked'])})
    task.action_xyz_check_out()
    env['xyz.material'].create({'task_id': task.id, 'product_id': material.id, 'quantity': spec['quantity']})
    task.write({'xyz_checked_safety': True, 'xyz_checked_service': True, 'xyz_checked_test': True,
                'xyz_before': photo, 'xyz_after': photo, 'xyz_signature': photo, 'xyz_signer': 'Đại diện khách hàng'})
    task.action_xyz_accept()
    # Backdate the finish so the on-time KPI reflects when the work really ended.
    task._xyz_system_write({'xyz_finished_at': start + timedelta(hours=spec['worked'])})
    invoice = task.xyz_invoice_id
    invoice.write({'invoice_date': (start + timedelta(hours=spec['planned'])).date()})
    invoice.action_post()
    invoice.invoice_date_due = fields.Date.today() + timedelta(days=spec['due_days'])
    if spec['payment'] != 'none' and payment_journal:
        amount = invoice.amount_total if spec['payment'] == 'full' else invoice.currency_id.round(invoice.amount_total / 2)
        env['account.payment.register'].with_user(users['accountant']).with_context(
            active_model='account.move', active_ids=invoice.ids,
        ).create({'amount': amount, 'journal_id': payment_journal.id}).action_create_payments()
for spec in history:
    booking = env.ref('xyz_seed.' + spec['key'], raise_if_not_found=False)
    if booking and booking.sale_id and booking.sale_id.xyz_task_id and booking.sale_id.xyz_task_id.xyz_invoice_id:
        due = fields.Date.today() + timedelta(days=spec['due_days'])
        inv = booking.sale_id.xyz_task_id.xyz_invoice_id
        env.cr.execute("UPDATE account_move SET invoice_date_due=%s WHERE id=%s", [due, inv.id])
        env.cr.execute("UPDATE account_move_line SET date_maturity=%s WHERE move_id=%s AND date_maturity IS NOT NULL", [due, inv.id])
env.cr.commit()
print('XYZ demo fixtures created. Account passwords are in local-credentials.txt.')
