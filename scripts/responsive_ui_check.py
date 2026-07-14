"""Responsive browser regression for chart titles, pie labels, and archive cards."""

from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = next(ROOT.parent.glob("26*0713*.xlsx"))
OUT = ROOT / "artifacts" / "screenshots" / "responsive"
URL = "http://localhost:8501"
OUT.mkdir(parents=True, exist_ok=True)

VIEWPORTS = {
    "80": 1800,
    "100": 1440,
    "125": 1152,
    "150": 960,
    "175": 823,
    "200": 720,
}
PIE_SELECTOR = 'iframe[title="src.responsive_plotly_events.responsive_plotly_events"]'


def assert_inside(inner: dict, outer: dict, label: str) -> None:
    tolerance = 2
    if (
        inner["x"] < outer["x"] - tolerance
        or inner["x"] + inner["width"] > outer["x"] + outer["width"] + tolerance
    ):
        raise AssertionError(f"{label} overflows its card: inner={inner}, outer={outer}")


def assert_pie_centered(card, iframe, label: str) -> None:
    """Check the rendered slices, not only the responsive iframe shell."""
    frame = card.frame_locator(PIE_SELECTOR)
    paths = frame.locator(".slice path")
    paths.first.wait_for(state="visible", timeout=15000)
    boxes = [paths.nth(index).bounding_box() for index in range(paths.count())]
    boxes = [box for box in boxes if box is not None]
    if not boxes:
        raise AssertionError(f"{label} has no visible pie slices")

    left = min(box["x"] for box in boxes)
    right = max(box["x"] + box["width"] for box in boxes)
    top = min(box["y"] for box in boxes)
    bottom = max(box["y"] + box["height"] for box in boxes)
    iframe_box = iframe.bounding_box()
    pie_center = (left + right) / 2
    frame_center = iframe_box["x"] + iframe_box["width"] / 2
    tolerance = max(14, iframe_box["width"] * 0.035)
    if abs(pie_center - frame_center) > tolerance:
        raise AssertionError(
            f"{label} is not centered: pie_center={pie_center}, frame_center={frame_center}"
        )
    if (
        left < iframe_box["x"] - 2
        or right > iframe_box["x"] + iframe_box["width"] + 2
        or top < iframe_box["y"] - 2
        or bottom > iframe_box["y"] + iframe_box["height"] + 2
    ):
        raise AssertionError(f"{label} slices are clipped by the iframe")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.goto(URL, wait_until="domcontentloaded", timeout=30000)
    page.locator('input[type="file"]').set_input_files(str(WORKBOOK))
    archive_title = page.get_by_text(
        "视角一：各阶段项目整体归档率（当前及之前阶段都要完成）",
        exact=True,
    ).first
    archive_title.wait_for(timeout=90000)

    for zoom, width in VIEWPORTS.items():
        page.set_viewport_size({"width": width, "height": 1000})
        pie_title = page.get_by_text("进度偏差类型分布（在执行项目）", exact=True)
        pie_title.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        card = pie_title.locator('xpath=ancestor::*[@data-testid="stColumn"][1]')
        pie = card.locator(PIE_SELECTOR).first
        pie.wait_for(timeout=15000)
        assert_inside(pie.bounding_box(), card.bounding_box(), f"pie at {zoom}%")
        assert_pie_centered(card, pie, f"pie at {zoom}%")
        assert_inside(pie_title.bounding_box(), card.bounding_box(), f"pie title at {zoom}%")
        page.screenshot(path=str(OUT / f"delivery_pie_{zoom}.png"), full_page=False)

        archive_title.scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        archive_card = archive_title.locator(
            'xpath=ancestor::*[@data-testid="stColumn"][1]'
        )
        assert_inside(
            archive_title.bounding_box(), archive_card.bounding_box(), f"archive title at {zoom}%"
        )
        archive_card.screenshot(path=str(OUT / f"archive_view_1_{zoom}.png"))

        overflow = page.evaluate(
            "document.documentElement.scrollWidth - document.documentElement.clientWidth"
        )
        if overflow > 2:
            raise AssertionError(f"page has {overflow}px horizontal overflow at {zoom}%")

    # Narrow layouts keep custom metric tables inside the page.  If their
    # columns need more room, the table itself scrolls instead of widening the
    # whole dashboard.
    page.set_viewport_size({"width": 520, "height": 1000})
    metric_table = page.locator('div[class*="st-key-selectable_table_"]').first
    metric_table.scroll_into_view_if_needed()
    metric_table.wait_for(state="visible", timeout=15000)
    table_layout = metric_table.evaluate(
        """element => ({
            overflowX: getComputedStyle(element).overflowX,
            clientWidth: element.clientWidth,
            scrollWidth: element.scrollWidth,
            pageWidth: document.documentElement.clientWidth,
        })"""
    )
    if table_layout["overflowX"] not in {"auto", "scroll"}:
        raise AssertionError(f"metric table has no controlled horizontal scroll: {table_layout}")
    if table_layout["clientWidth"] > table_layout["pageWidth"] + 2:
        raise AssertionError(f"metric table widens the page: {table_layout}")
    if table_layout["scrollWidth"] <= table_layout["clientWidth"]:
        raise AssertionError(f"narrow metric table did not create internal scroll: {table_layout}")
    narrow_page_overflow = page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    if narrow_page_overflow > 2:
        raise AssertionError(f"narrow page has {narrow_page_overflow}px horizontal overflow")

    # Responsive pie must retain the existing click-to-detail behavior.
    page.set_viewport_size({"width": 960, "height": 1000})
    pie_title = page.get_by_text("进度偏差类型分布（在执行项目）", exact=True)
    pie_title.scroll_into_view_if_needed()
    pie_frame = page.frame_locator(
        PIE_SELECTOR
    ).first
    pie_frame.locator(".slice path").first.click(force=True)
    dialog = page.locator('[role="dialog"]')
    dialog.wait_for(state="visible", timeout=15000)
    if "项目明细" not in dialog.inner_text():
        raise AssertionError("responsive pie click did not open project detail")

    print("workbook=", WORKBOOK)
    print("viewports=", VIEWPORTS)
    print("responsive_pie_iframes=", page.locator(PIE_SELECTOR).count())
    print("pie_click=", True)
    print("metric_table_layout=", table_layout)
    browser.close()
