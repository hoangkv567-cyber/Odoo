"""Exercise the backend as restricted users using actual browser sessions."""
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_support import wait_for_odoo

root = Path(__file__).resolve().parents[1]
password = (root / 'local-credentials.txt').read_text().splitlines()[0].removeprefix('Demo password: ')
base = 'http://127.0.0.1:8069'
wait_for_odoo(base)

with sync_playwright() as p:
    browser = p.chromium.launch()
    for login in ('sale', 'tech1', 'accountant', 'director'):
        context = browser.new_context(viewport={'width': 1366, 'height': 900})
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        auth = context.request.post(base + '/web/session/authenticate', data=json.dumps({
            'jsonrpc': '2.0', 'params': {'db': 'xyz_demo', 'login': login + '@xyz.test', 'password': password},
        }), headers={'Content-Type': 'application/json'}).json()
        assert auth.get('result', {}).get('uid'), login
        uid = auth['result']['uid']
        task_action = context.request.post(base + '/web/action/load', data=json.dumps({'jsonrpc': '2.0', 'params': {'action_id': 'xyz_service_core.action_service_tasks'}}), headers={'Content-Type': 'application/json'}).json()['result']['id']

        def rpc(model, method, args, kwargs=None):
            response = context.request.post(base + '/web/dataset/call_kw', data=json.dumps({
                'jsonrpc': '2.0', 'params': {'model': model, 'method': method, 'args': args, 'kwargs': kwargs or {}},
            }), headers={'Content-Type': 'application/json'}).json()
            return response

        if login == 'sale':
            response = rpc('res.partner', 'search_count', [[['customer_rank', '>', 0], ['user_id', '!=', uid]]])
            assert response.get('result') == 0, response
        if login == 'tech1':
            response = rpc('project.task', 'search_read', [[['xyz_booking_id', '!=', False]]], {'fields': ['id', 'user_ids']})
            jobs = response['result']
            assert jobs and all(uid in job['user_ids'] for job in jobs)
            denied = rpc('project.task', 'write', [[jobs[0]['id']], {'xyz_state': 'done'}])
            assert 'error' in denied
            page.set_viewport_size({'width': 390, 'height': 844})
            page.goto(base + '/odoo/action-' + str(task_action) + '/' + str(jobs[0]['id']), wait_until='domcontentloaded')
            page.locator('.o_form_view').wait_for(timeout=30000)
            page.get_by_role('tab', name=re.compile(r'Chi tiết dịch vụ XYZ|XYZ service details')).click()
            page.screenshot(path=str(root / 'docs/evidence/technician-mobile.png'), full_page=True)
        if login == 'accountant':
            assert 'error' in rpc('project.task', 'xyz_dispatch_data', [])
            response = rpc('project.task', 'search', [[['xyz_booking_id', '!=', False]]], {'limit': 1})
            page.goto(base + '/odoo/action-' + str(task_action) + '/' + str(response['result'][0]), wait_until='domcontentloaded')
            page.locator('.o_form_view').wait_for(timeout=30000)
            page.get_by_role('tab', name=re.compile(r'Chi tiết dịch vụ XYZ|XYZ service details')).click()
            page.screenshot(path=str(root / 'docs/evidence/accountant.png'), full_page=True)
        if login == 'director':
            response = context.request.post(base + '/web/action/load', data=json.dumps({
                'jsonrpc': '2.0', 'params': {'action_id': 'xyz_service_reporting.action_report'},
            }), headers={'Content-Type': 'application/json'}).json()
            page.goto(base + '/odoo/action-' + str(response['result']['id']), wait_until='domcontentloaded')
            page.locator('div.o_pivot').wait_for(timeout=30000)
            page.screenshot(path=str(root / 'docs/evidence/director-report.png'), full_page=True)
            assert 'error' in rpc('xyz.service.report', 'create', [{'name': 'Forbidden'}])
        assert not errors, (login, errors)
        context.close()
    print('ROLES PASS: Sales customer ownership, technician mobile and state protection, accountant without dispatch rights, director read-only report')
    browser.close()
