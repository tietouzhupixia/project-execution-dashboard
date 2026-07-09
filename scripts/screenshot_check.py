from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample" / "sample_dashboard_workbook.xlsx"
OUT = ROOT / "artifacts" / "screenshots"
URL = "http://localhost:8501"

SECTION_TITLES = [
    "一、公司项目执行管理总览",
    "二、项目执行进度情况",
    "三、项目执行管理异常情况通报",
    "四、人效分析",
]

OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
    page.goto(URL, wait_until="domcontentloaded", timeout=30000)
    page.locator('input[type="file"]').set_input_files(str(SAMPLE))
    page.wait_for_selector("text=执行项目总数", timeout=60000)
    page.wait_for_selector("text=四、人效分析", timeout=60000)
    page.wait_for_timeout(3000)

    page.screenshot(path=str(OUT / "00_full.png"), full_page=True)

    banners = page.locator("div.section-banner")
    for i in range(banners.count()):
        banners.nth(i).scroll_into_view_if_needed()
        page.wait_for_timeout(800)
        page.screenshot(path=str(OUT / f"section_{i + 1}.png"))

    body_text = page.locator("body").inner_text(timeout=10000)
    missing_sections = [t for t in SECTION_TITLES if t not in body_text]
    error_markers = ["Traceback", "Exception", "KeyError", "ModuleNotFoundError", "NameError"]
    found_errors = [marker for marker in error_markers if marker in body_text]
    print("title=", page.title())
    print("screenshots=", OUT)
    print("missing_sections=", missing_sections)
    print("found_errors=", found_errors)
    if found_errors or missing_sections:
        raise SystemExit(1)
    browser.close()
