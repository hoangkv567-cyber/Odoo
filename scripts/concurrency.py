"""Two independent database transactions contend for one technician (test DB only)."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Barrier
import uuid

import psycopg2
from odoo import api, fields, SUPERUSER_ID
from odoo.exceptions import ValidationError

assert env.cr.dbname == 'xyz_test', 'Concurrency fixtures belong only in xyz_test'
key = uuid.uuid4().hex[:10]
partner = env['res.partner'].create({'name': 'Concurrency ' + key})
equipment = env['xyz.equipment'].create({'name': 'Concurrent equipment', 'partner_id': partner.id})
user = env['res.users'].with_context(no_reset_password=True).create({'name': 'Concurrent technician', 'login': 'concurrency-' + key})
employee = env['hr.employee'].create({'name': 'Concurrent technician', 'user_id': user.id, 'resource_calendar_id': env.company.resource_calendar_id.id})
employee.resource_calendar_id.tz = 'UTC'
tasks = env['project.task']
for index in (1, 2):
    booking = env['xyz.booking'].create({
        'token': key + str(index), 'partner_id': partner.id, 'equipment_id': equipment.id,
        'product_id': env.ref('xyz_service_core.service_compressor').product_variant_id.id,
        'requested_start': datetime(2027, 1, 4, 9),
    })
    booking.sale_id.action_confirm()
    tasks |= booking.sale_id.xyz_task_id
ids, employee_id = tasks.ids, employee.id
env.cr.commit()
barrier = Barrier(2)

def attempt(task_id):
    try:
        with env.registry.cursor() as cr:
            worker = api.Environment(cr, SUPERUSER_ID, {})
            task = worker['project.task'].browse(task_id)
            # Establish both snapshots before either assignment commits.
            task.read(['xyz_state'])
            barrier.wait(timeout=15)
            task.xyz_dispatch_move(employee_id, datetime(2027, 1, 4, 9), datetime(2027, 1, 4, 11))
            cr.commit()
            return 'committed'
    except psycopg2.errors.SerializationFailure:
        # This is what Odoo's request retry layer does after a concurrent write.
        with env.registry.cursor() as cr:
            worker = api.Environment(cr, SUPERUSER_ID, {})
            try:
                worker['project.task'].browse(task_id).xyz_dispatch_move(employee_id, datetime(2027, 1, 4, 9), datetime(2027, 1, 4, 11))
                cr.commit()
                return 'committed'
            except ValidationError:
                return 'rejected'
    except ValidationError:
        return 'rejected'

with ThreadPoolExecutor(max_workers=2) as pool:
    results = list(pool.map(attempt, ids))
assert sorted(results) == ['committed', 'rejected'], results
print('CONCURRENCY PASS: one assignment committed; the conflicting assignment was rejected after retry')
