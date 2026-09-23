"""The module data is loaded with noupdate="1", so the English source names introduced for
bilingual support would never reach a database that was created before them. Write them once.
"""

from odoo import SUPERUSER_ID, api

RENAMES = {
    'xyz_service_core.project_service': 'XYZ · Field service',
    'xyz_service_core.service_compressor': 'Compressor maintenance',
    'xyz_service_core.service_cooling': 'Cooling system maintenance',
    'xyz_service_core.website_menu_service': 'Book a maintenance visit',
}


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xmlid, name in RENAMES.items():
        record = env.ref(xmlid, raise_if_not_found=False)
        if record and record.name != name:
            record.write({'name': name})
