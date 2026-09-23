"""Prove that the interface can be switched between English and Vietnamese.

The script signs in as the demo dispatcher (a Vietnamese user), toggles the top-bar language
switcher, and checks that the same screens come back in the other language. It then visits the
public booking page as a Vietnamese visitor and switches the *website* language from the
header selector. The dispatcher is left back in Vietnamese so later checks see the demo state.
"""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'scripts'))
from browser_support import wait_for_odoo

password = (root / 'local-credentials.txt').read_text().splitlines()[0].removeprefix('Demo password: ')
base = 'http://127.0.0.1:8069'
evidence = root / 'docs' / 'evidence'
evidence.mkdir(exist_ok=True)
vietnamese_visitor = {'locale': 'vi-VN', 'extra_http_headers': {'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.5'}}
wait_for_odoo(base)


# The backend keeps polling, so 'networkidle' never fires; wait for the switch to land instead.
def switch_backend_language(page, label, expected, menu_word, force=False):
    """Use the top-bar switcher; a crashed earlier run may already have left the right language."""
    if not force and page.locator('.o_xyz_language_switch').inner_text().strip() == expected:
        return page.locator('.o_menu_sections').first.inner_text()
    page.locator('.o_xyz_language_switch').click()
    page.locator('.o_xyz_language_menu .o-dropdown-item', has_text=label).first.click()
    page.wait_for_load_state('domcontentloaded')
    page.locator('.o_menu_sections', has_text=menu_word).first.wait_for(timeout=60000)
    page.wait_for_timeout(1500)
    assert page.locator('.o_xyz_language_switch').inner_text().strip() == expected, \
        page.locator('.o_xyz_language_switch').inner_text()
    return page.locator('.o_menu_sections').first.inner_text()


with sync_playwright() as p:
    browser = p.chromium.launch()

    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, **vietnamese_visitor)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(base + '/web/login')
    page.locator('input[name=login]').fill('dispatch@xyz.test')
    page.locator('input[name=password]').fill(password)
    page.locator('form.oe_login_form button[type=submit]').click()
    page.wait_for_selector('.o_main_navbar', timeout=60000)
    page.wait_for_timeout(2500)

    # 1. The Vietnamese user opens the service app: the top bar reads VI and the menus are Vietnamese.
    page.goto(base + '/odoo/action-xyz_service_core.action_service_tasks', wait_until='domcontentloaded')
    page.locator('.o_menu_sections').first.wait_for(timeout=60000)
    page.wait_for_timeout(2000)
    vietnamese_menu = switch_backend_language(page, 'Vietnamese', 'VI', 'Công việc hiện trường')
    assert 'Công việc hiện trường' in vietnamese_menu, vietnamese_menu
    assert page.locator('.o_breadcrumb, .o_control_panel').first.inner_text().strip(), 'empty screen'
    page.screenshot(path=str(evidence / 'language-backend-vi.png'), full_page=True)

    # 2. Same screens in English after using the switcher.
    english_menu = switch_backend_language(page, 'English (US)', 'EN', 'Field jobs', force=True)
    assert 'Field jobs' in english_menu, english_menu
    assert page.locator('.o_control_panel').first.inner_text().strip(), 'empty screen'
    page.screenshot(path=str(evidence / 'language-backend-en.png'), full_page=True)

    # 3. Back to Vietnamese, and the switch is remembered for the session.
    vietnamese_menu = switch_backend_language(page, 'Vietnamese', 'VI', 'Công việc hiện trường', force=True)
    assert 'Công việc hiện trường' in vietnamese_menu, vietnamese_menu
    page.screenshot(path=str(evidence / 'language-backend-switched-back.png'), full_page=True)

    # 4. The public website follows the visitor language and offers its own selector.
    page.goto(base + '/maintenance', wait_until='networkidle')
    page.locator('h1', has_text='Bảo dưỡng chủ động').first.wait_for(timeout=30000)
    assert page.locator('#name').count() == 1
    page.locator('h2', has_text='Yêu cầu bảo dưỡng').first.wait_for(timeout=30000)
    page.screenshot(path=str(evidence / 'language-website-vi.png'), full_page=True)

    def switch_website_language(label, heading, request_title):
        selector = page.locator('.js_language_selector').first
        link = page.locator('.js_language_selector a.js_change_lang', has_text=label).first
        for attempt in range(3):
            selector.locator('button').click()
            try:
                link.wait_for(timeout=8000)
                break
            except Exception:
                if attempt == 2:
                    print('SELECTOR HTML', page.evaluate("() => document.querySelector('.js_language_selector')?.outerHTML"))
                    raise
        link.click()
        page.locator('h1', has_text=heading).first.wait_for(timeout=60000)
        page.locator('h2', has_text=request_title).first.wait_for(timeout=30000)

    switch_website_language('English', 'Proactive maintenance', 'Maintenance request')
    assert page.locator('#name').count() == 1
    page.screenshot(path=str(evidence / 'language-website-en.png'), full_page=True)

    # 5. And back to Vietnamese from the same selector.
    # The selector prints the language name after the last '/', i.e. " Tiếng Việt" for vi_VN.
    switch_website_language('Tiếng Việt', 'Bảo dưỡng chủ động', 'Yêu cầu bảo dưỡng')
    assert page.locator('#name').count() == 1

    assert not errors, errors
    print('LANGUAGE PASS: dispatcher switched English/Vietnamese in the backend and the website '
          'selector switched the public page, ending in Vietnamese')
    context.close()
    browser.close()
