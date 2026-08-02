"""
导出 16 型恋爱人格分享卡 PNG（宣发用）。

用法（先开本地 Flask debug）：
  python scripts/export_personality_cards.py

输出：
  exports/personality-cards/{CODE}-{名称}.png
  exports/personality-cards/CampusMatch-恋爱人格卡-16型.zip
"""

from __future__ import annotations

import asyncio
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "exports" / "personality-cards"
BASE = "http://127.0.0.1:5000/dev/personality-export"

# 避免把仓库根加进 path 时名称冲突
sys.path.insert(0, str(ROOT))
from personality import PERSONALITIES  # noqa: E402


async def main() -> None:
    from playwright.async_api import async_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.png"):
        old.unlink()

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={"width": 480, "height": 900},
            device_scale_factor=2,
        )
        resp = await page.goto(BASE, wait_until="networkidle", timeout=60000)
        if not resp or resp.status != 200:
            raise SystemExit(
                f"无法打开 {BASE}（status={getattr(resp, 'status', None)}）。"
                "请先在项目根目录运行: python app.py"
            )
        await page.wait_for_timeout(600)

        paths = []
        for code, meta in PERSONALITIES.items():
            sel = f"#wrap-{code} .lp-share-frame"
            el = page.locator(sel)
            await el.scroll_into_view_if_needed()
            await page.wait_for_timeout(80)
            name = meta["name"]
            dest = OUT / f"{code}-{name}.png"
            await el.screenshot(path=str(dest), type="png")
            paths.append(dest)
            print("wrote", dest.name)

        await browser.close()

    zip_path = OUT / "CampusMatch-恋爱人格卡-16型.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for pth in paths:
            zf.write(pth, arcname=pth.name)
    print("zip", zip_path)
    print("dir", OUT)


if __name__ == "__main__":
    asyncio.run(main())
