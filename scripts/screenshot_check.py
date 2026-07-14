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

    dialog = page.locator('[role="dialog"]')

    # KPI regression: the large total is a direct project-detail entry point.
    total_button = page.get_by_role("button", name="46", exact=True).first
    total_button.scroll_into_view_if_needed()
    total_button.click()
    dialog.wait_for(state="visible", timeout=15000)
    total_dialog_text = dialog.inner_text()
    if "执行项目总数" not in total_dialog_text or "共 46 个项目" not in total_dialog_text:
        raise SystemExit(f"unexpected total KPI dialog: {total_dialog_text[:200]}")
    page.screenshot(path=str(OUT / "total_kpi_drilldown.png"))
    dialog.locator('button[aria-label="Close"]').click()
    dialog.wait_for(state="hidden", timeout=10000)

    # Summary-table regression: click the first numeric cell (company total = 2).
    accepted_heading = page.get_by_text("已验收项目数（按业务单元）", exact=True)
    accepted_heading.scroll_into_view_if_needed()
    accepted_table = page.locator(".st-key-selectable_table_summary_accepted_count")
    accepted_table.get_by_role("button", name="2", exact=True).click()
    dialog.wait_for(state="visible", timeout=15000)
    accepted_dialog_text = dialog.inner_text()
    if "已验收项目数 · 公司整体" not in accepted_dialog_text or "共 2 个项目" not in accepted_dialog_text:
        raise SystemExit(f"unexpected accepted-cell dialog: {accepted_dialog_text[:200]}")
    page.screenshot(path=str(OUT / "accepted_summary_cell_drilldown.png"))
    dialog.locator('button[aria-label="Close"]').click()
    dialog.wait_for(state="hidden", timeout=10000)

    # The remounted table must allow clicking the same cell after closing.
    accepted_heading = page.get_by_text("已验收项目数（按业务单元）", exact=True)
    accepted_heading.scroll_into_view_if_needed()
    accepted_table = page.locator(".st-key-selectable_table_summary_accepted_count")
    accepted_table.get_by_role("button", name="2", exact=True).click()
    dialog.wait_for(state="visible", timeout=15000)
    accepted_dialog_text = dialog.inner_text()
    if "已验收项目数 · 公司整体" not in accepted_dialog_text:
        raise SystemExit(f"accepted-cell drill-down did not reopen: {accepted_dialog_text[:200]}")
    dialog.locator('button[aria-label="Close"]').click()
    dialog.wait_for(state="hidden", timeout=10000)

    # Project-deviation ranking: project name and percentage cells are row drill-downs.
    project_ranking = page.locator(
        ".st-key-selectable_table_cross_project_deviation_ranking"
    )
    project_ranking.scroll_into_view_if_needed()
    project_ranking.get_by_role("button").first.click()
    dialog.wait_for(state="visible", timeout=15000)
    ranking_dialog_text = dialog.inner_text()
    if "跨年交付 · 项目进度偏差" not in ranking_dialog_text or "共 1 个项目" not in ranking_dialog_text:
        raise SystemExit(f"unexpected project-ranking dialog: {ranking_dialog_text[:200]}")
    page.screenshot(path=str(OUT / "project_ranking_drilldown.png"))
    dialog.locator('button[aria-label="Close"]').click()
    dialog.wait_for(state="hidden", timeout=10000)

    # Stage comparison: first bar is 项目启动 / 项目个数 = 28.
    alert_chart = page.locator(
        '[class*="st-key-alert_stage_comparison_selection_"] [data-testid="stPlotlyChart"]'
    ).first
    alert_bar = alert_chart.locator(".point path").first
    alert_bar.scroll_into_view_if_needed()
    alert_bar.click(force=True)
    dialog.wait_for(state="visible", timeout=15000)
    alert_chart_dialog_text = dialog.inner_text()
    if "项目启动 · 项目个数" not in alert_chart_dialog_text or "共 28 个项目" not in alert_chart_dialog_text:
        raise SystemExit(f"unexpected alert-chart dialog: {alert_chart_dialog_text[:200]}")
    page.screenshot(path=str(OUT / "alert_chart_drilldown.png"))
    dialog.locator('button[aria-label="Close"]').click()
    dialog.wait_for(state="hidden", timeout=10000)

    # Stage business-unit table: every numeric cell opens its unit-scoped projects.
    alert_region_table = page.locator(".st-key-selectable_table_alert_region_0")
    alert_region_table.scroll_into_view_if_needed()
    alert_region_table.get_by_role("button").first.click()
    dialog.wait_for(state="visible", timeout=15000)
    alert_region_dialog_text = dialog.inner_text()
    if "项目启动 ·" not in alert_region_dialog_text or "未完成质控" not in alert_region_dialog_text:
        raise SystemExit(f"unexpected alert-region dialog: {alert_region_dialog_text[:200]}")
    page.screenshot(path=str(OUT / "alert_region_drilldown.png"))
    dialog.locator('button[aria-label="Close"]').click()
    dialog.wait_for(state="hidden", timeout=10000)

    # Archive view 1: first denominator bar is 启动阶段 / 应归档项目 = 20.
    archive_view_1 = page.locator(
        '[class*="st-key-archive_view_1_selection_"] [data-testid="stPlotlyChart"]'
    ).first
    archive_view_1_bar = archive_view_1.locator(".point path").first
    archive_view_1_bar.scroll_into_view_if_needed()
    archive_view_1_bar.click(force=True)
    dialog.wait_for(state="visible", timeout=15000)
    archive_view_1_dialog_text = dialog.inner_text()
    if "视角一 · 启动阶段 · 应归档项目" not in archive_view_1_dialog_text or "共 20 个项目" not in archive_view_1_dialog_text:
        raise SystemExit(f"unexpected archive-view-1 dialog: {archive_view_1_dialog_text[:200]}")
    page.screenshot(path=str(OUT / "archive_view_1_drilldown.png"))
    dialog.locator('button[aria-label="Close"]').click()
    dialog.wait_for(state="hidden", timeout=10000)

    # The rate label itself is also a selectable point and maps to the denominator scope.
    archive_view_1 = page.locator(
        '[class*="st-key-archive_view_1_selection_"] [data-testid="stPlotlyChart"]'
    ).first
    archive_view_1_rate = archive_view_1.locator(".scatterlayer .textpoint text").first
    archive_view_1_rate.scroll_into_view_if_needed()
    archive_view_1_rate.click(force=True)
    dialog.wait_for(state="visible", timeout=15000)
    archive_rate_dialog_text = dialog.inner_text()
    if "视角一 · 启动阶段 · 归档率口径项目" not in archive_rate_dialog_text or "共 20 个项目" not in archive_rate_dialog_text:
        raise SystemExit(f"unexpected archive-rate dialog: {archive_rate_dialog_text[:200]}")
    dialog.locator('button[aria-label="Close"]').click()
    dialog.wait_for(state="hidden", timeout=10000)

    # Archive view 2: fourth denominator bar is 整体 / 应完成归档环节 = 41.
    archive_view_2 = page.locator(
        '[class*="st-key-archive_view_2_selection_"] [data-testid="stPlotlyChart"]'
    ).first
    archive_view_2_bar = archive_view_2.locator(".point path").nth(3)
    archive_view_2_bar.scroll_into_view_if_needed()
    archive_view_2_bar.click(force=True)
    dialog.wait_for(state="visible", timeout=15000)
    archive_view_2_dialog_text = dialog.inner_text()
    if "视角二 · 整体 · 应完成归档环节" not in archive_view_2_dialog_text or "共 41 个归档环节" not in archive_view_2_dialog_text:
        raise SystemExit(f"unexpected archive-view-2 dialog: {archive_view_2_dialog_text[:200]}")
    page.screenshot(path=str(OUT / "archive_view_2_drilldown.png"))
    dialog.locator('button[aria-label="Close"]').click()
    dialog.wait_for(state="hidden", timeout=10000)

    # Drill-down regression: the same pie slice must open again after closing.
    pie_component = page.frame_locator('iframe[title="src.responsive_plotly_events.responsive_plotly_events"]').first
    first_pie_slice = pie_component.locator('.slice path').nth(1)
    first_pie_slice.scroll_into_view_if_needed()
    first_pie_slice.click(force=True)
    dialog.wait_for(state="visible", timeout=15000)
    first_dialog_text = dialog.inner_text()
    if "项目明细" not in first_dialog_text or "共 " not in first_dialog_text:
        raise SystemExit(f"unexpected drill-down dialog: {first_dialog_text[:200]}")
    page.screenshot(path=str(OUT / "drilldown_dialog.png"))
    dialog.locator('button[aria-label="Close"]').click()
    dialog.wait_for(state="hidden", timeout=10000)

    unit_ranking_chart = page.locator(
        '[class*="st-key-current_unit_deviation_ranking_selection_"] '
        '[data-testid="stPlotlyChart"]'
    ).first
    unit_ranking_bar = unit_ranking_chart.locator('.point path').first
    unit_ranking_bar.scroll_into_view_if_needed()
    unit_ranking_bar.click(force=True)
    dialog.wait_for(state="visible", timeout=15000)
    unit_dialog_text = dialog.inner_text()
    if "当年交付 · 业务单元" not in unit_dialog_text:
        raise SystemExit(f"unexpected unit ranking dialog: {unit_dialog_text[:200]}")
    page.screenshot(path=str(OUT / "unit_ranking_drilldown.png"))
    dialog.locator('button[aria-label="Close"]').click()
    dialog.wait_for(state="hidden", timeout=10000)

    pie_component = page.frame_locator('iframe[title="src.responsive_plotly_events.responsive_plotly_events"]').first
    first_pie_slice = pie_component.locator('.slice path').nth(1)
    first_pie_slice.click(force=True)
    dialog.wait_for(state="visible", timeout=15000)
    second_dialog_text = dialog.inner_text()
    if "项目明细" not in second_dialog_text or "共 " not in second_dialog_text:
        raise SystemExit(f"drill-down did not reopen: {second_dialog_text[:200]}")
    dialog.locator('button[aria-label="Close"]').click()
    dialog.wait_for(state="hidden", timeout=10000)

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
    print("drilldown_reopen=", True)
    print("unit_ranking_drilldown=", True)
    print("total_kpi_drilldown=", True)
    print("accepted_cell_drilldown_reopen=", True)
    print("project_ranking_drilldown=", True)
    print("alert_chart_drilldown=", True)
    print("alert_region_drilldown=", True)
    print("archive_view_1_drilldown=", True)
    print("archive_rate_label_drilldown=", True)
    print("archive_view_2_drilldown=", True)
    if found_errors or missing_sections:
        raise SystemExit(1)
    browser.close()
