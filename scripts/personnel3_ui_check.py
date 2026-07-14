"""Browser smoke test for the personnel-3 upload, section, and drill-downs."""

from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = next(ROOT.parent.glob("26*0713*.xlsx"))
OUT = ROOT / "artifacts" / "screenshots"
URL = "http://localhost:8501"
OUT.mkdir(parents=True, exist_ok=True)


def close_dialog(page) -> None:
    dialog = page.locator('[role="dialog"]')
    dialog.locator('button[aria-label="Close"]').click()
    dialog.wait_for(state="hidden", timeout=10000)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
    page.goto(URL, wait_until="domcontentloaded", timeout=30000)
    page.locator('input[type="file"]').set_input_files(str(WORKBOOK))
    page.wait_for_selector("text=五、26年人均净合同额（人员3口径）", timeout=90000)
    page.wait_for_selector("text=部门人均净合同额排名", timeout=90000)
    page.wait_for_timeout(3000)

    dialog = page.locator('[role="dialog"]')

    # Confirm the first low-confidence candidate. The prefilled candidate project ID is retained,
    # and every downstream amount is recalculated immediately after the editor reruns.
    match_editor = page.locator(
        '[data-testid="data-grid-canvas"]:has(th:text-is("外委序号"))'
    ).first
    match_editor.scroll_into_view_if_needed()
    match_editor.dblclick(position={"x": 720, "y": 299}, force=True)
    page.get_by_role("option", name="已匹配", exact=True).click()
    page.wait_for_selector("text=当前确认结果：已匹配 29；未匹配 24；需人工确认 9", timeout=30000)

    # Company KPI opens the exact 58 included projects and can reopen.
    company_projects = page.locator(".st-key-personnel3_company_projects").get_by_role(
        "button", name="58", exact=True
    )
    company_projects.scroll_into_view_if_needed()
    company_projects.click()
    dialog.wait_for(state="visible", timeout=15000)
    company_text = dialog.inner_text()
    if "纳入口径项目" not in company_text or "共 58 条项目" not in company_text:
        raise SystemExit(f"unexpected company drill-down: {company_text[:300]}")
    page.screenshot(path=str(OUT / "personnel3_company_drilldown.png"))
    close_dialog(page)
    company_projects = page.locator(".st-key-personnel3_company_projects").get_by_role(
        "button", name="58", exact=True
    )
    company_projects.click()
    dialog.wait_for(state="visible", timeout=15000)
    close_dialog(page)

    # Department chart opens the two-tab department detail dialog.
    department_chart = page.locator(
        '[class*="st-key-personnel3_department_ranking_selection_"] [data-testid="stPlotlyChart"]'
    ).first
    department_bar = department_chart.locator(".point path").first
    department_bar.scroll_into_view_if_needed()
    department_bar.click(force=True)
    dialog.wait_for(state="visible", timeout=15000)
    department_text = dialog.inner_text()
    if "纳入口径项目" not in department_text or "人员3名单" not in department_text:
        raise SystemExit(f"unexpected department drill-down: {department_text[:300]}")
    page.screenshot(path=str(OUT / "personnel3_department_drilldown.png"))
    close_dialog(page)

    # Person ranking opens that person's allocation rows.
    person_chart = page.locator(
        '[class*="st-key-personnel3_person_ranking_selection_"] [data-testid="stPlotlyChart"]'
    ).first
    person_bar = person_chart.locator(".point path").last
    person_bar.scroll_into_view_if_needed()
    person_bar.click(force=True)
    dialog.wait_for(state="visible", timeout=15000)
    person_text = dialog.inner_text()
    if "分摊项目" not in person_text:
        raise SystemExit(f"unexpected person drill-down: {person_text[:300]}")
    page.screenshot(path=str(OUT / "personnel3_person_drilldown.png"))
    close_dialog(page)

    # Project ranking opens net/outsource/allocation tabs.
    project_chart = page.locator(
        '[class*="st-key-personnel3_project_ranking_selection_"] [data-testid="stPlotlyChart"]'
    ).first
    project_bar = project_chart.locator(".point path").last
    project_bar.scroll_into_view_if_needed()
    project_bar.click(force=True)
    dialog.wait_for(state="visible", timeout=15000)
    project_text = dialog.inner_text()
    if "项目净额" not in project_text or "外委子项目" not in project_text or "人员分摊" not in project_text:
        raise SystemExit(f"unexpected project drill-down: {project_text[:300]}")
    page.screenshot(path=str(OUT / "personnel3_project_drilldown.png"))
    close_dialog(page)

    # Exception bars map back to current exception rows.
    exception_chart = page.locator(
        '[class*="st-key-personnel3_exception_types_selection_"] [data-testid="stPlotlyChart"]'
    ).first
    exception_bar = exception_chart.locator(".point path").first
    exception_bar.scroll_into_view_if_needed()
    exception_bar.click(force=True)
    dialog.wait_for(state="visible", timeout=15000)
    exception_text = dialog.inner_text()
    if "异常类型" not in exception_text or "共 " not in exception_text:
        raise SystemExit(f"unexpected exception drill-down: {exception_text[:300]}")
    page.screenshot(path=str(OUT / "personnel3_exception_drilldown.png"))
    close_dialog(page)

    # Matching-status slices also map back to the exact outsource rows.
    match_status_frame = page.frame_locator(
        '[class*="st-key-personnel3_match_status_click_"] iframe'
    )
    match_status_frame.locator(".slice path").first.click(force=True)
    dialog.wait_for(state="visible", timeout=15000)
    match_status_text = dialog.inner_text()
    if "外委子项目" not in match_status_text or "共 " not in match_status_text:
        raise SystemExit(f"unexpected match-status drill-down: {match_status_text[:300]}")
    page.screenshot(path=str(OUT / "personnel3_match_status_drilldown.png"))
    close_dialog(page)

    page.get_by_text("五、26年人均净合同额（人员3口径）", exact=True).scroll_into_view_if_needed()
    page.screenshot(path=str(OUT / "personnel3_section.png"), full_page=True)
    body = page.locator("body").inner_text()
    required = [
        "五、26年人均净合同额（人员3口径）",
        "外委子项目匹配确认",
        "下载人员3结果（数值版）",
        "下载完整核算工作簿（含公式）",
        "公司26年净执行合同额",
        "人员326年净执行合同额排名",
        "异常类型分布",
        "核验结果",
    ]
    missing = [text for text in required if text not in body]
    error_markers = ["Traceback", "KeyError", "TypeError", "ModuleNotFoundError"]
    errors = [marker for marker in error_markers if marker in body]
    print("workbook=", WORKBOOK)
    print("missing=", missing)
    print("errors=", errors)
    print("company_reopen=", True)
    print("department_drilldown=", True)
    print("person_drilldown=", True)
    print("project_drilldown=", True)
    print("exception_drilldown=", True)
    print("manual_confirmation_recalculation=", True)
    print("match_status_drilldown=", True)
    if missing or errors:
        raise SystemExit(1)
    browser.close()
