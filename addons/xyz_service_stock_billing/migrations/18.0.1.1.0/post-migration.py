"""The module data is loaded with noupdate="1", so the English source names introduced for
bilingual support would never reach a database that was created before them. Write them once.
"""

from odoo import SUPERUSER_ID, api

RENAMES = {
    'xyz_service_stock_billing.product_labor': 'Maintenance labour / hour',
    'xyz_service_stock_billing.truck_1': 'Technician truck 1',
    'xyz_service_stock_billing.truck_2': 'Technician truck 2',
}


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xmlid, name in RENAMES.items():
        record = env.ref(xmlid, raise_if_not_found=False)
        if record and record.name != name:
            record.write({'name': name})
