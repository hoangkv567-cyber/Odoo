from pathlib import Path
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from browser_support import wait_for_odoo

root = Path(__file__).resolve().parents[1]
password = (root / 'local-credentials.txt').read_text().splitlines()[0].removeprefix('Demo password: ')
base = 'http://127.0.0.1:8069'
wait_for_odoo(base)
with sync_playwright() as p:
    browser = p.chromium.launch()
    # Vietnamese visitor: without this the site follows the browser language (Accept-Language).
    context = browser.new_context(viewport={'width': 1366, 'height': 900}, locale='vi-VN',
                                  extra_http_headers={'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.5'},
                                  record_video_dir=str(root / 'docs/evidence/raw-video'), record_video_size={'width': 1280, 'height': 900})
    page = context.new_page()
    page.goto(base + '/web/login')
    page.locator('input[name=login]').fill('customer1@xyz.test')
    page.locator('input[name=password]').fill(password)
    page.locator('form.oe_login_form button[type=submit]').click()
    page.wait_for_url('**/my**')
    page.goto(base + '/maintenance')
    page.locator('#name').fill('Portal customer UAT')
    page.locator('#email').fill('customer1@example.test')
    page.locator('#equipment').fill('Portal signed quotation test')
    page.locator('#address').fill('XYZ industrial park')
    page.locator('#requested_start').fill((datetime.now() + timedelta(days=35)).strftime('%Y-%m-%dT09:00'))
    page.locator('form[action="/maintenance/book"] button[type=submit]').click()
    page.wait_for_url('**/maintenance/thanks', timeout=60000)
    page.goto(base + '/my/quotes', wait_until='networkidle')
    page.locator('a[href^="/my/orders/"]').first.click()
    page.locator('a[data-bs-target="#modalaccept"]').first.click()
    page.locator('#modalaccept.show input[name=signer]').fill('XYZ Customer UAT')
    page.locator('#modalaccept.show .o_web_sign_auto_button').click()
    page.wait_for_timeout(800)
    page.screenshot(path=str(root / 'docs/evidence/portal-signature.png'), full_page=True)
    page.locator('#modalaccept.show button[type=submit]').click()
    page.wait_for_url('**/*message=sign_ok*', timeout=60000)
    assert page.locator('#signature img').count() == 1
    page.screenshot(path=str(root / 'docs/evidence/portal-confirmed.png'), full_page=True)
    page.goto(base + '/my/maintenance')
    assert page.get_by_role('heading', name='Lịch sử bảo dưỡng').is_visible()
    assert page.locator('table tbody tr').count() >= 1
    print('PORTAL PASS: B2B booking, quotation visible, customer signature, confirmed order, service history')
    video = page.video
    context.close()
    video.save_as(str(root / 'docs/evidence/demo-portal-signature.webm'))
    video.delete()
    browser.close()
