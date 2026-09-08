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
    assert page.locator(".metric").count() == 6
    assert page.locator(".admin-alert").filter(has_text="API Key").count() == 1
    assert page.locator("body").evaluate("el => el.scrollWidth <= window.innerWidth")
    assert not errors, errors
    page.screenshot(path=str(output / filename), full_page=True)
    page.close()


with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    check_dashboard(browser, {"width": 1440, "height": 1000}, "admin-desktop.png")
    check_dashboard(browser, {"width": 390, "height": 844}, "admin-mobile.png")
    browser.close()

print("admin browser checks passed")
