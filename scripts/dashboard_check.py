"""Capture the reporting dashboard (pivot, revenue chart, receivables chart) as evidence.

Read-only: the script signs in as the demo director and screenshots the three
reporting actions, so the images match what the role sees in a real session.
"""
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright
from browser_support import wait_for_odoo

root = Path(__file__).resolve().parents[1]
password = (root / 'local-credentials.txt').read_text().splitlines()[0].removeprefix('Demo password: ')
base = 'http://127.0.0.1:8069'
evidence = root / 'docs' / 'evidence'
evidence.mkdir(exist_ok=True)
wait_for_odoo(base)

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    auth = context.request.post(base + '/web/session/authenticate', data=json.dumps({
        'jsonrpc': '2.0', 'params': {'db': 'xyz_demo', 'login': 'director@xyz.test', 'password': password},
    }), headers={'Content-Type': 'application/json'}).json()
    assert auth.get('result', {}).get('uid'), auth

    def read_group(fields, groupby):
        """Call the same grouped read the charts are drawn from."""
        response = context.request.post(base + '/web/dataset/call_kw', data=json.dumps({
            'jsonrpc': '2.0', 'params': {'model': 'xyz.service.report', 'method': 'web_read_group',
                                         'args': [[], fields, groupby], 'kwargs': {'limit': 80}},
        }), headers={'Content-Type': 'application/json'}).json()
        assert 'result' in response, response
        return response['result']['groups']

    def open_report(xmlid, container, name):
        response = context.request.post(base + '/web/action/load', data=json.dumps({
            'jsonrpc': '2.0', 'params': {'action_id': xmlid},
        }), headers={'Content-Type': 'application/json'}).json()
        assert 'result' in response, response
        page.goto(base + '/odoo/action-' + str(response['result']['id']), wait_until='domcontentloaded')
        page.locator(container).first.wait_for(timeout=30000)
        page.wait_for_timeout(2000)  # let the chart animation settle before the screenshot
        panel = page.locator('.o_control_panel').inner_text()
        assert any(n in panel for n in (name if isinstance(name, tuple) else (name,))), panel

    open_report('xyz_service_reporting.action_report', 'div.o_pivot', ('Bảng điều khiển dịch vụ', 'Service dashboard'))
    assert page.locator('div.o_pivot table tbody tr').count() >= 3
    # Pivot cells print raw VND amounts, so a four digit group proves the figures are present.
    assert re.search(r'\d{4,}', page.locator('div.o_pivot').inner_text())
    page.screenshot(path=str(evidence / 'dashboard-pivot.png'), full_page=True)

    monthly = read_group(['revenue', 'material_cost'], ['date:month'])
    assert sum(group['revenue'] or 0 for group in monthly) > 0, monthly
    open_report('xyz_service_reporting.action_report_revenue', '.o_graph_canvas_container canvas', ('Doanh thu & Chi phí vật tư', 'Revenue and material cost'))
    # The line mode proves this chart is the monthly revenue view, not the technician bar chart.
    assert 'active' in (page.locator('.o_graph_button[data-mode=line]').get_attribute('class') or '')
    page.screenshot(path=str(evidence / 'dashboard-revenue.png'), full_page=True)

    receivable = read_group(['current_amount', 'overdue'], ['partner_id'])
    assert sum(group['overdue'] or 0 for group in receivable) > 0, receivable
    open_report('xyz_service_reporting.action_report_receivable', '.o_graph_canvas_container canvas', ('Công nợ theo khách hàng', 'Receivables by customer'))
    assert 'active' in (page.locator('.o_graph_button[data-mode=bar]').get_attribute('class') or '')
    page.screenshot(path=str(evidence / 'dashboard-receivables.png'), full_page=True)

    assert not errors, errors
    print('DASHBOARD PASS: pivot, revenue chart and receivables chart captured as the demo director')
    context.close()
    browser.close()
