"""Upload a raw three-input workbook and verify Personnel-3 compatibility."""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
URL = "http://localhost:8501"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    args = parser.parse_args()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.goto(URL, wait_until="domcontentloaded", timeout=30_000)
        page.locator('input[type="file"]').set_input_files(str(args.workbook.resolve()))
        page.wait_for_selector("text=五、26年人均净合同额（人员3口径）", timeout=90_000)
        page.wait_for_selector("text=当前确认结果：", timeout=180_000)
        page.locator(".st-key-personnel3_company_projects").get_by_role(
            "button", name="59", exact=True
        ).wait_for(timeout=180_000)
        page.locator(".st-key-personnel3_company_people").get_by_role(
            "button", name="22", exact=True
        ).wait_for(timeout=30_000)
        page.locator(".st-key-drilldown_big_current_project_count").get_by_role(
            "button", name="48", exact=True
        ).wait_for(timeout=30_000)
        page.locator(".st-key-drilldown_big_cross_project_count").get_by_role(
            "button", name="4", exact=True
        ).wait_for(timeout=30_000)
        page.locator(".st-key-drilldown_big_current_delivery_rate").get_by_role(
            "button", name="4.88%", exact=True
        ).wait_for(timeout=30_000)

        body = page.locator("body").inner_text(timeout=30_000)
        status_lines = [
            line
            for line in body.splitlines()
            if line.startswith("系统初判：") or line.startswith("当前确认结果：")
        ]
        errors = [
            marker
            for marker in (
                "Personnel3Inputs",
                "AttributeError",
                "人员3口径计算失败",
                "Traceback",
            )
            if marker in body
        ]
        screenshot = ROOT / "artifacts" / "screenshots" / "personnel3_raw_input_fixed.png"
        page.get_by_text("五、26年人均净合同额（人员3口径）", exact=True).scroll_into_view_if_needed()
        page.screenshot(path=str(screenshot), full_page=True)
        browser.close()

    print(f"workbook={args.workbook}")
    print(f"status_lines={status_lines}")
    print("projects=59")
    print("people=22")
    print("current_delivery=48")
    print("cross_year_delivery=4")
    print("delivery_rate=4.88%")
    print(f"errors={errors}")
    if errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
