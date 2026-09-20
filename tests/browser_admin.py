import os
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


base_url = os.environ.get("ADMIN_PREVIEW_URL", "http://127.0.0.1:5092")
password = os.environ.get("ADMIN_PREVIEW_PASSWORD", "preview-admin-password")
output = Path(__file__).resolve().parents[1] / "instance"


def check_dashboard(browser, viewport, filename):
    page = browser.new_page(viewport=viewport)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(f"{base_url}/admin", wait_until="networkidle")
    assert urlparse(page.url).path == "/admin/login"
    page.locator("#password").fill(password)
    page.locator("button[type=submit]").click()
    page.wait_for_url(f"{base_url}/admin")
    assert page.locator('[aria-label="关键指标"] .metric').count() == 6
    assert page.get_by_role("heading", name="当前状态漏斗").is_visible()
    assert page.locator('#operations select[name="ops_gender"]').count() == 1
    page.locator('#operations select[name="ops_gender"]').select_option("female")
    page.get_by_role("button", name="查看", exact=True).click()
    page.wait_for_url("**/admin?ops_school=&ops_gender=female#operations")
    assert page.locator('#operations select[name="ops_gender"]').input_value() == "female"
    assert page.locator("body").evaluate("el => el.scrollWidth <= window.innerWidth")
    assert not errors, errors
    page.screenshot(path=str(output / filename), full_page=True)
    page.close()


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel=os.environ.get("ADMIN_BROWSER_CHANNEL") or None)
    check_dashboard(browser, {"width": 1440, "height": 1000}, "admin-desktop.png")
    check_dashboard(browser, {"width": 390, "height": 844}, "admin-mobile.png")
    browser.close()

print("admin browser checks passed")
