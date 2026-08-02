"""导出文字侧写分享卡 PNG。

用法（先开本地 Flask debug）：
  python scripts/export_letter_portrait.py

输出：
  exports/personality-cards/letter-portrait.png
"""

from __future__ import annotations

import asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "exports" / "personality-cards"
URL = "http://127.0.0.1:5000/dev/letter-portrait"


async def main() -> None:
    from playwright.async_api import async_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / "letter-portrait.png"

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={"width": 480, "height": 1100},
            device_scale_factor=2,
        )
        resp = await page.goto(URL, wait_until="networkidle", timeout=60000)
        if not resp or resp.status != 200:
            raise SystemExit(
                f"无法打开 {URL}（status={getattr(resp, 'status', None)}）。"
                "请先运行: python app.py"
            )
        await page.wait_for_timeout(700)
        el = page.locator("#letter-portrait-frame")
        await el.scroll_into_view_if_needed()
        await el.screenshot(path=str(dest), type="png")
        await browser.close()

    print("wrote", dest)


if __name__ == "__main__":
    asyncio.run(main())
