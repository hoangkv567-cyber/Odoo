"""Local browser smoke test; no external services or real transactions."""
from pathlib import Path
import json
import re
from datetime import datetime, timedelta
import uuid
from playwright.sync_api import sync_playwright
from browser_support import wait_for_odoo

root = Path(__file__).resolve().parents[1]
password = (root / 'local-credentials.txt').read_text().splitlines()[0].removeprefix('Demo password: ')
evidence = root / 'docs' / 'evidence'
evidence.mkdir(exist_ok=True)
wait_for_odoo()
with sync_playwright() as p:
    browser = p.chromium.launch()
    # A Vietnamese visitor: without this, Odoo serves the English source language of the site.
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, locale='vi-VN',
                                  extra_http_headers={'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.5'},
                                  record_video_dir=str(evidence / 'raw-video'), record_video_size={'width': 1280, 'height': 900})
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:8069/maintenance', wait_until='networkidle')
    assert page.locator('form[action="/maintenance/book"]').count() == 1
    assert page.locator('select[name=product_id] option').count() == 2
    page.screenshot(path=str(evidence / 'website-desktop.png'), full_page=True)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.screenshot(path=str(evidence / 'website-mobile.png'), full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.locator('#name').fill('Browser UAT customer')
    page.locator('#email').fill('uat-' + uuid.uuid4().hex[:8] + '@example.test')
    page.locator('#equipment').fill('Browser test compressor')
    page.locator('#address').fill('XYZ industrial park, Ho Chi Minh City')
    page.locator('#requested_start').fill((datetime.now() + timedelta(days=21)).strftime('%Y-%m-%dT09:00'))
    page.locator('form[action="/maintenance/book"] button[type=submit]').click()
    page.wait_for_url('**/maintenance/thanks', timeout=60000)
    assert page.get_by_role('heading', name='Đã nhận yêu cầu bảo dưỡng').is_visible()
    page.set_viewport_size({'width': 1440, 'height': 1000})
    page.goto('http://127.0.0.1:8069/web/login')
    page.locator('input[name=login]').fill('dispatch@xyz.test')
    page.locator('input[name=password]').fill(password)
    page.locator('form.oe_login_form button[type=submit]').click()
    page.wait_for_url('**/odoo**', timeout=60000)
    page.wait_for_timeout(3000)
    # Resolve the action through the authenticated session instead of hardcoding database IDs.
    response = page.request.post('http://127.0.0.1:8069/web/action/load', data=json.dumps({
        'jsonrpc': '2.0', 'method': 'call', 'params': {'action_id': 'xyz_service_core.action_dispatch'}}), headers={'Content-Type': 'application/json'})
    assert 'result' in response.json(), response.json()
    action_id = response.json()['result']['id']
    page.goto(f'http://127.0.0.1:8069/odoo/action-{action_id}', wait_until='domcontentloaded')
    page.locator('.vis-timeline').wait_for(timeout=30000)
    page.screenshot(path=str(evidence / 'dispatch.png'), full_page=True)
    assert page.locator('.vis-item-content').count() >= 4
    # Unassigned jobs pile up on the same lane and can overlap, so open an assigned one.
    # Unassigned jobs share one lane and can overlap, so the double-click is triggered through
    # the DOM: the timeline handles the bubbling event exactly as it does for a real click.
    page.evaluate("""() => {
        const item = document.querySelector('.vis-item-content');
        item.dispatchEvent(new MouseEvent('dblclick', {bubbles: true, cancelable: true, view: window}));
    }""")
    page.locator('.o_form_view').wait_for(timeout=30000)
    page.get_by_role('tab', name=re.compile(r'Chi tiết dịch vụ XYZ|XYZ service details')).click()
    page.screenshot(path=str(evidence / 'service-form.png'), full_page=True)
    assert not errors, errors
    print('BROWSER PASS: booking desktop/mobile and submit, authentication, Gantt and task form, no JS errors')
    video = page.video
    context.close()
    video.save_as(str(evidence / 'demo-booking-dispatch.webm'))
    video.delete()
    browser.close()
