from __future__ import annotations

import hashlib
import io

import pandas as pd
import streamlit as st

from src.charts import (
    format_table_for_display,
    inject_css,
    render_bar_chart,
    render_big_number,
    render_clickable_big_number,
    render_count_chart,
    render_deviation_ranking_chart,
    render_group_banner,
    render_horizontal_ranking_chart,
    render_metric_table,
    render_multi_bar_chart,
    render_ratio_bar_chart,
    render_row_label,
    render_selectable_metric_table,
    render_section_banner,
)
from src.data_loader import display_columns, load_workbook, parse_excel_date_series
from src.export import build_export_workbook
from src.export_formulas import build_formula_workbook
from src.metrics import (
    archive_view_1_project_subset,
    archive_view_2_record_subset,
    build_all_metrics,
    build_delivery_analysis,
    build_kpi_strip,
    build_stage_alerts,
    discover_business_units,
    filter_projects,
    project_subset_by_delivery_group,
    project_subset_by_keyword,
    project_subset_by_month,
    project_subset_by_value,
    projects_of_unit,
    stage_alert_project_subsets,
)
from src.personnel3_loader import load_personnel3_inputs
from src.personnel3_export import (
    build_personnel3_formula_workbook,
    build_personnel3_value_workbook,
)
from src.personnel3_metrics import (
    MATCHED,
    NEEDS_CONFIRMATION,
    UNMATCHED,
    build_project_net_detail,
    match_outsource_projects,
)
from src.personnel3_outputs import (
    build_personnel3_outputs,
    personnel3_department_people,
    personnel3_department_projects,
    personnel3_exceptions_of_type,
    personnel3_person_allocations,
    personnel3_project_allocations,
    personnel3_project_outsource,
    personnel3_project_rows,
)


st.set_page_config(page_title="项目执行管理仪表盘", layout="wide")
inject_css()

st.title("项目执行管理仪表盘")
st.caption("上传 Excel 后自动生成项目进度分析；包含三张 `input_` 表时同时生成人员3口径人均净合同额。")

uploaded = st.file_uploader("上传 Excel 文件", type=["xlsx"])

if not uploaded:
    st.info("请上传包含 `实施进度底表` 的 Excel 文件。")
    st.stop()

@st.cache_data(show_spinner="正在解析上传文件...")
def load_workbook_cached(file_bytes: bytes):
    """Cache parsing so filter clicks don't re-read the Excel on every rerun."""
    return load_workbook(io.BytesIO(file_bytes))


@st.cache_data(show_spinner="正在校验人员3口径输入...")
def load_personnel3_inputs_cached(file_bytes: bytes):
    return load_personnel3_inputs(io.BytesIO(file_bytes))


try:
    uploaded_bytes = uploaded.getvalue()
    workbook = load_workbook_cached(uploaded_bytes)
except Exception as exc:  # noqa: BLE001 - 面向业务用户的兜底提示
    st.error(
        "文件解析失败，请确认上传的是包含「实施进度底表」的 Excel（.xlsx）。\n\n"
        f"技术信息：{type(exc).__name__}: {exc}"
    )
    st.stop()

try:
    personnel3_inputs = load_personnel3_inputs_cached(uploaded_bytes)
    personnel3_parse_error = None
except Exception as exc:  # noqa: BLE001 - 新口径失败不阻断原四章节
    personnel3_inputs = None
    personnel3_parse_error = f"{type(exc).__name__}: {exc}"

# ------------------------------------------------------------------ 筛选
with st.expander("筛选（默认全部项目）"):
    f1, f2, f3, f4 = st.columns(4)
    unit_options = discover_business_units(workbook.raw)
    manager_options = (
        sorted(workbook.raw["A-项目经理"].dropna().astype(str).str.strip().unique())
        if "A-项目经理" in workbook.raw.columns
        else []
    )
    stage_options = (
        sorted(workbook.raw["进度分类"].dropna().astype(str).str.strip().unique())
        if "进度分类" in workbook.raw.columns
        else []
    )
    month_options = (
        sorted(
            parse_excel_date_series(workbook.raw["预计交付日期"]).dt.strftime("%y年%m月").dropna().unique()
        )
        if "预计交付日期" in workbook.raw.columns
        else []
    )
    with f1:
        picked_units = st.multiselect("业务单元", unit_options)
    with f2:
        picked_managers = st.multiselect("项目经理", manager_options)
    with f3:
        picked_stages = st.multiselect("进度阶段", stage_options)
    with f4:
        picked_months = st.multiselect("预计交付月", month_options)

raw = filter_projects(
    workbook.raw,
    units=picked_units,
    managers=picked_managers,
    stages=picked_stages,
    months=picked_months,
)
is_filtered = len(raw) != len(workbook.raw)
if raw.empty:
    st.warning("当前筛选条件下没有项目，请调整筛选。")
    st.stop()

try:
    metrics = build_all_metrics(raw, workbook.relation)
    kpi = build_kpi_strip(raw)
    delivery = build_delivery_analysis(raw)
    alerts = build_stage_alerts(raw)
    export_payload = build_export_workbook(raw, metrics, delivery, alerts)
    formula_payload = build_formula_workbook(raw, discover_business_units(raw), metrics.efficiency["person"])
except Exception as exc:  # noqa: BLE001 - 云端会打码原始堆栈，这里给出可读信息
    st.error(
        "指标计算失败，底表中可能存在预期外的数据格式。\n\n"
        f"技术信息：{type(exc).__name__}: {exc}"
    )
    st.stop()

all_warnings = workbook.warnings + metrics.warnings
if all_warnings:
    with st.expander("数据提醒", expanded=True):
        for warning in all_warnings:
            st.warning(warning)

info_col, dl_col1, dl_col2 = st.columns([2, 1, 1])
with info_col:
    scope = f"筛选后 {len(raw)} / 共 {len(workbook.raw)}" if is_filtered else f"{len(raw)}"
    st.caption(f"识别底表：{workbook.source_sheet}；项目数：{scope}")
today = f"{pd.Timestamp.now():%Y%m%d}"
mime_xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
with dl_col1:
    st.download_button(
        "下载分析结果",
        data=export_payload,
        file_name=f"项目执行管理分析_{today}.xlsx",
        mime=mime_xlsx,
        use_container_width=True,
        help="数值版：直接查看计算好的结果表。",
    )
with dl_col2:
    st.download_button(
        "下载核算版（含公式）",
        data=formula_payload,
        file_name=f"项目执行管理分析_核算版_{today}.xlsx",
        mime=mime_xlsx,
        use_container_width=True,
        help="公式版：分析单元格为活公式，指向实施进度底表，可人工核对计算逻辑。",
    )
if is_filtered:
    st.info("当前为筛选视图：以下所有图表、表格与导出文件均按筛选后的项目计算。")


def pct(value: float | None, digits: int = 2) -> str:
    return f"{value:.{digits}%}" if value is not None and value == value else "无"


@st.dialog("项目明细", width="large")
def show_project_detail(
    context: str,
    detail: pd.DataFrame,
    *,
    count_label: str = "项目",
) -> None:
    st.subheader(context)
    st.caption(f"共 {len(detail)} 个{count_label}")
    columns = display_columns(detail)
    if detail.empty or not columns:
        st.info("暂无数据")
        return
    ordered = detail[columns].sort_values("进度偏差") if "进度偏差" in columns else detail[columns]
    st.dataframe(
        format_table_for_display(ordered),
        use_container_width=True,
        hide_index=True,
    )


@st.dialog("人员3口径明细", width="large")
def show_personnel3_table(context: str, detail: pd.DataFrame, *, count_label: str = "记录") -> None:
    st.subheader(context)
    st.caption(f"共 {len(detail)} 条{count_label}")
    if detail.empty:
        st.info("暂无数据")
        return
    st.dataframe(format_table_for_display(detail), use_container_width=True, hide_index=True)


@st.dialog("部门人效明细", width="large")
def show_personnel3_department(
    department: str,
    project_detail: pd.DataFrame,
    personnel3_list: pd.DataFrame,
) -> None:
    st.subheader(department)
    project_tab, people_tab = st.tabs(["纳入口径项目", "人员3名单"])
    with project_tab:
        projects = personnel3_department_projects(project_detail, department)
        st.caption(f"共 {len(projects)} 个项目")
        st.dataframe(format_table_for_display(projects), use_container_width=True, hide_index=True)
    with people_tab:
        people = personnel3_department_people(personnel3_list, department)
        st.caption(f"共 {len(people)} 人")
        st.dataframe(format_table_for_display(people), use_container_width=True, hide_index=True)


@st.dialog("项目净额明细", width="large")
def show_personnel3_project(
    project_id: str,
    project_detail: pd.DataFrame,
    outsource_matches: pd.DataFrame,
    allocation: pd.DataFrame,
) -> None:
    project = personnel3_project_rows(project_detail, project_id)
    title = project.iloc[0]["项目名称"] if not project.empty else project_id
    st.subheader(str(title))
    net_tab, outsource_tab, allocation_tab = st.tabs(["项目净额", "外委子项目", "人员分摊"])
    with net_tab:
        st.dataframe(format_table_for_display(project), use_container_width=True, hide_index=True)
    with outsource_tab:
        outsourced = personnel3_project_outsource(outsource_matches, project_id)
        st.caption(f"共 {len(outsourced)} 条外委子项目")
        if outsourced.empty:
            st.info("暂无对应外委子项目")
        else:
            st.dataframe(format_table_for_display(outsourced), use_container_width=True, hide_index=True)
    with allocation_tab:
        allocations = personnel3_project_allocations(allocation, project_id)
        st.caption(f"共 {len(allocations)} 条已填比例分摊")
        if allocations.empty:
            st.info("暂无已填执行比例")
        else:
            st.dataframe(format_table_for_display(allocations), use_container_width=True, hide_index=True)


def render_project_kpi(
    title: str,
    value: str,
    detail: pd.DataFrame,
    *,
    key: str,
    caption: str = "",
    context: str | None = None,
) -> None:
    """Render one project-backed KPI and open its matching source rows."""
    if render_clickable_big_number(title, value, caption, key=key):
        show_project_detail(context or title, detail)


def show_summary_cell_detail(
    selection: tuple[int, str] | None,
    table: pd.DataFrame,
    scope: pd.DataFrame,
    *,
    value_column: str,
    context: str,
) -> None:
    """Map a clicked numeric business-unit summary cell back to projects."""
    if selection is None or selection[1] != value_column:
        return
    row = selection[0]
    if row < 0 or row >= len(table):
        return
    unit = str(table.iloc[row]["业务单元"])
    detail = scope if unit == "公司整体" else projects_of_unit(scope, unit)
    show_project_detail(f"{context} · {unit}", detail)


# ------------------------------------------------------------------ 一、总览
overview = metrics.project_overview
as_of = overview.get("as_of")
as_of_text = f"-截至{as_of.month}月{as_of.day}日" if as_of is not None else ""
status_text = (
    raw["交付状态"].astype(str)
    if "交付状态" in raw.columns
    else pd.Series("", index=raw.index)
)
project_type_text = (
    raw["执行项目类型"].astype(str)
    if "执行项目类型" in raw.columns
    else pd.Series("", index=raw.index)
)
all_unaccepted_projects = raw.loc[status_text.str.contains("未验收", na=False)].copy()
all_accepted_projects = raw.loc[status_text.str.contains("已验收", na=False)].copy()
render_section_banner(f"一、公司项目执行管理总览{as_of_text}")

with st.container(border=True):
    render_project_kpi(
        "执行项目总数",
        f"{overview['total_projects']}",
        raw,
        key="drilldown_big_total_projects",
        caption="年初至统计月末。包括往年遗留、当年新签、未签先执行三类项目；含未交付/已交付、未验收/已验收；未验收按项目阶段分类。",
        context="执行项目总数",
    )

c1, c2 = st.columns(2)
with c1:
    with st.container(border=True):
        selected = render_count_chart(
            "其中：往年遗留、新签、未签先执行分布",
            overview["project_type"],
            "执行项目类型",
            key="overview_project_type",
        )
        if selected is not None:
            show_project_detail(
                f"执行项目类型：{selected}",
                project_subset_by_value(raw, "执行项目类型", selected),
            )
    with st.container(border=True):
        selected = render_count_chart(
            "其中：验收分布",
            overview["acceptance_split"],
            "状态",
            key="overview_acceptance",
        )
        if selected is not None:
            show_project_detail(
                f"验收状态：{selected}",
                project_subset_by_keyword(raw, "交付状态", selected, "已验收", "未验收"),
            )
    with st.container(border=True):
        selected = render_count_chart(
            "其中：交付分布",
            overview["delivery_split"],
            "状态",
            key="overview_delivery",
        )
        if selected is not None:
            show_project_detail(
                f"交付状态：{selected}",
                project_subset_by_keyword(raw, "交付状态", selected, "已交付", "未交付"),
            )
with c2:
    with st.container(border=True):
        selected = render_bar_chart(
            "其中：预计验收年月分布",
            overview["estimated_acceptance_month"],
            "年月",
            "数量",
            key="overview_acceptance_month",
        )
        if selected is not None:
            show_project_detail(
                f"预计验收年月：{selected}",
                project_subset_by_month(
                    raw,
                    "预计验收日期（若已签约，默认经法）",
                    selected,
                    collapsed=True,
                ),
            )
    with st.container(border=True):
        selected = render_bar_chart(
            "其中：预计交付年月分布",
            overview["estimated_delivery_month"],
            "年月",
            "数量",
            key="overview_delivery_month",
        )
        if selected is not None:
            show_project_detail(
                f"预计交付年月：{selected}",
                project_subset_by_month(raw, "预计交付日期", selected, collapsed=True),
            )
    with st.container(border=True):
        selected = render_count_chart(
            "其中：对于未验收项目，项目阶段分布",
            overview["unaccepted_stage"],
            "进度分类",
            key="overview_unaccepted_stage",
        )
        if selected is not None:
            show_project_detail(
                f"未验收项目阶段：{selected}",
                project_subset_by_value(all_unaccepted_projects, "进度分类", selected),
            )

# KPI 条
new_unaccepted_projects = all_unaccepted_projects.loc[
    project_type_text.loc[all_unaccepted_projects.index].str.contains("新签", na=False)
].copy()
legacy_unaccepted_projects = all_unaccepted_projects.loc[
    project_type_text.loc[all_unaccepted_projects.index].str.contains("遗留", na=False)
].copy()
progress_text = (
    pd.to_numeric(raw["当前进度"], errors="coerce")
    if "当前进度" in raw.columns
    else pd.Series(float("nan"), index=raw.index)
)
archive_due_projects = raw.loc[progress_text.ge(0.1)].copy()
k1, k2, k3, k4 = st.columns(4)
with k1:
    with st.container(border=True):
        render_project_kpi(
            "公司平均进度（新签未验收）",
            pct(kpi["avg_progress_new_unaccepted"], 1),
            new_unaccepted_projects,
            key="drilldown_big_new_unaccepted_progress",
            caption="不含已交付项目",
        )
with k2:
    with st.container(border=True):
        render_project_kpi(
            "公司平均进度（遗留未验收）",
            pct(kpi["avg_progress_legacy_unaccepted"], 1),
            legacy_unaccepted_projects,
            key="drilldown_big_legacy_unaccepted_progress",
            caption="不含已交付项目",
        )
with k3:
    with st.container(border=True):
        render_project_kpi(
            "公司平均进度偏差（所有未验收）",
            pct(kpi["avg_deviation_unaccepted"], 1),
            all_unaccepted_projects,
            key="drilldown_big_unaccepted_deviation",
            caption="实际完成进度-时间进度",
        )
with k4:
    with st.container(border=True):
        render_project_kpi(
            "公司项目关键进度归档完成度",
            pct(kpi["archive_completion_rate"]),
            archive_due_projects,
            key="drilldown_big_archive_completion",
            caption="已完成归档环节数/应完成归档环节数",
            context="公司项目关键进度归档完成度 · 进度达到10%的应归档项目",
        )

# ---------------------------------------------------------- 二、进度情况
render_section_banner("二、项目执行进度情况")

s1, s2, s3 = st.columns(3)
summary = metrics.progress_summary
project_count_table = summary.get("project_count")
unaccepted_table = summary.get("unaccepted")
accepted_table = summary.get("accepted")
if "A-项目名称" in raw.columns:
    project_names = raw["A-项目名称"]
    named_projects = raw.loc[
        project_names.notna() & project_names.astype(str).str.strip().ne("")
    ].copy()
else:
    named_projects = raw.iloc[0:0].copy()
with s1:
    with st.container(border=True):
        selected_cell = render_selectable_metric_table(
            "项目数（按业务单元）",
            project_count_table,
            key="summary_project_count",
        )
        show_summary_cell_detail(
            selected_cell,
            project_count_table,
            named_projects,
            value_column="项目数",
            context="项目数",
        )
with s2:
    with st.container(border=True):
        selected_cell = render_selectable_metric_table(
            "未验收项目数（按业务单元）",
            unaccepted_table,
            key="summary_unaccepted_count",
        )
        show_summary_cell_detail(
            selected_cell,
            unaccepted_table,
            all_unaccepted_projects,
            value_column="未验收项目数",
            context="未验收项目数",
        )
with s3:
    with st.container(border=True):
        selected_cell = render_selectable_metric_table(
            "已验收项目数（按业务单元）",
            accepted_table,
            key="summary_accepted_count",
        )
        show_summary_cell_detail(
            selected_cell,
            accepted_table,
            all_accepted_projects,
            value_column="已验收项目数",
            context="已验收项目数",
        )

ref_year_text = f"{delivery['ref_year'] % 100}年"
current_projects = project_subset_by_delivery_group(raw, "current_unaccepted", delivery["ref_year"])
cross_projects = project_subset_by_delivery_group(raw, "cross_unaccepted", delivery["ref_year"])
accepted_projects = project_subset_by_delivery_group(raw, "accepted", delivery["ref_year"])
delivered_unaccepted_projects = project_subset_by_delivery_group(
    raw,
    "delivered_unaccepted",
    delivery["ref_year"],
)
delivery_dates = (
    parse_excel_date_series(raw["预计交付日期"])
    if "预计交付日期" in raw.columns
    else pd.Series(pd.NaT, index=raw.index)
)
due_current_year_projects = raw.loc[delivery_dates.dt.year.eq(delivery["ref_year"])].copy()

# —— 未验收 · 当年交付
label_col, body_col = st.columns([1, 9])
with label_col:
    render_row_label("未验收", "当年交付")
with body_col:
    current = delivery["current_year"]
    b1, b2, b3, b4 = st.columns([2, 2, 2, 4])
    with b1:
        with st.container(border=True):
            render_project_kpi(
                "当年交付项目个数",
                f"{current['count']}",
                current_projects,
                key="drilldown_big_current_project_count",
                caption="含逾期未交付项目",
            )
    with b2:
        with st.container(border=True):
            render_project_kpi(
                "平均进度",
                pct(current["avg_progress"]),
                current_projects,
                key="drilldown_big_current_avg_progress",
                context="当年交付 · 平均进度",
            )
    with b3:
        with st.container(border=True):
            render_project_kpi(
                "平均进度偏差",
                pct(current["avg_deviation"], 1),
                current_projects,
                key="drilldown_big_current_avg_deviation",
                caption="实际完成进度-时间进度",
                context="当年交付 · 平均进度偏差",
            )
    with b4:
        with st.container(border=True):
            selected = render_count_chart(
                "进度偏差类型分布（在执行项目）",
                current["deviation_type"],
                "进度偏差分类",
                key="current_deviation_type",
            )
            if selected is not None:
                show_project_detail(
                    f"当年交付 · 进度偏差分类：{selected}",
                    project_subset_by_value(current_projects, "进度偏差分类", selected),
                )
    g1, g2 = st.columns(2)
    with g1:
        with st.container(border=True):
            selected = render_bar_chart(
                "预计交付年月",
                current["delivery_month"],
                "年月",
                "数量",
                key="current_delivery_month",
            )
            if selected is not None:
                show_project_detail(
                    f"当年交付 · 预计交付年月：{selected}",
                    project_subset_by_month(
                        current_projects,
                        "预计交付日期",
                        selected,
                        collapsed=False,
                    ),
                )
    with g2:
        with st.container(border=True):
            ranking = current["region_deviation_ranking"]
            selected = render_deviation_ranking_chart(
                "业务部进度偏差排名",
                ranking,
                "业务单元",
                "进度偏差（平均值）",
                key="current_unit_deviation_ranking",
            )
            if selected is not None:
                show_project_detail(
                    f"当年交付 · 业务单元：{selected}",
                    projects_of_unit(current_projects, selected),
                )

# —— 未验收 · 跨年交付
label_col, body_col = st.columns([1, 9])
with label_col:
    render_row_label("未验收", "跨年交付")
with body_col:
    cross = delivery["cross_year"]
    b1, b2, b3, b4 = st.columns([2, 2, 2, 4])
    with b1:
        with st.container(border=True):
            render_project_kpi(
                "跨年交付项目个数",
                f"{cross['count']}",
                cross_projects,
                key="drilldown_big_cross_project_count",
            )
    with b2:
        with st.container(border=True):
            render_project_kpi(
                "平均进度",
                pct(cross["avg_progress"]),
                cross_projects,
                key="drilldown_big_cross_avg_progress",
                context="跨年交付 · 平均进度",
            )
    with b3:
        with st.container(border=True):
            render_project_kpi(
                "平均进度偏差",
                pct(cross["avg_deviation"], 1),
                cross_projects,
                key="drilldown_big_cross_avg_deviation",
                caption="实际完成进度-时间进度",
                context="跨年交付 · 平均进度偏差",
            )
    with b4:
        with st.container(border=True):
            selected = render_count_chart(
                "偏差类型分布",
                cross["deviation_type"],
                "进度偏差分类",
                key="cross_deviation_type",
            )
            if selected is not None:
                show_project_detail(
                    f"跨年交付 · 进度偏差分类：{selected}",
                    project_subset_by_value(cross_projects, "进度偏差分类", selected),
                )
    g1, g2 = st.columns(2)
    with g1:
        with st.container(border=True):
            selected = render_bar_chart(
                "预计交付年",
                cross["delivery_year"],
                "年份",
                "数量",
                key="cross_delivery_year",
            )
            if selected is not None:
                year = pd.to_numeric(selected.rstrip("年"), errors="coerce")
                dates = parse_excel_date_series(cross_projects["预计交付日期"])
                detail = cross_projects.loc[dates.dt.year.eq(year)].copy()
                show_project_detail(f"跨年交付 · 预计交付年：{selected}", detail)
    with g2:
        with st.container(border=True):
            project_ranking = cross["project_deviation_ranking"]
            selected_cell = render_selectable_metric_table(
                "项目进度偏差排名",
                project_ranking,
                key="cross_project_deviation_ranking",
                clickable_columns=set(project_ranking.columns),
            )
            if selected_cell is not None and 0 <= selected_cell[0] < len(project_ranking):
                source_index = project_ranking.index[selected_cell[0]]
                detail = cross_projects.loc[cross_projects.index == source_index].copy()
                project_name = str(project_ranking.iloc[selected_cell[0]]["A-项目名称"])
                show_project_detail(f"跨年交付 · 项目进度偏差：{project_name}", detail)

# —— 已验收
label_col, body_col = st.columns([1, 9])
with label_col:
    render_row_label("已验收")
with body_col:
    accepted = delivery["accepted"]
    b1, b2, b3 = st.columns([2, 2, 4])
    with b1:
        with st.container(border=True):
            render_project_kpi(
                "已交付项目个数",
                f"{accepted['count']}",
                accepted_projects,
                key="drilldown_big_accepted_project_count",
                context="已验收项目",
            )
    with b2:
        with st.container(border=True):
            render_project_kpi(
                f"{ref_year_text}交付率",
                pct(accepted["delivery_rate"]),
                due_current_year_projects,
                key="drilldown_big_current_delivery_rate",
                caption=accepted["delivery_rate_detail"],
                context=f"{ref_year_text}交付率 · 当年应交付项目",
            )
    with b3:
        with st.container(border=True):
            selected = render_count_chart(
                "偏差类型分布",
                accepted["deviation_type"],
                "进度偏差分类",
                key="accepted_deviation_type",
            )
            if selected is not None:
                show_project_detail(
                    f"已验收 · 进度偏差分类：{selected}",
                    project_subset_by_value(accepted_projects, "进度偏差分类", selected),
                )
    with st.container(border=True):
        delivered_ranking = accepted["delivered_unaccepted_ranking"]
        selected = render_bar_chart(
            "业务部已交付未验收项目个数排名",
            delivered_ranking,
            "业务单元",
            "项目个数",
            key="delivered_unaccepted_unit_ranking",
        )
        if selected is not None:
            show_project_detail(
                f"已交付未验收 · 业务单元：{selected}",
                projects_of_unit(delivered_unaccepted_projects, selected),
            )

# ---------------------------------------------------------- 三、异常通报
render_section_banner("三、项目执行管理异常情况通报")

alert_chart_rows = []
alert_scopes: dict[str, dict[str, pd.DataFrame | None]] = {}
for alert in alerts:
    stage_short = alert["stage"].split("（")[0]
    alert_scopes[stage_short] = stage_alert_project_subsets(raw, alert["stage"])
    alert_chart_rows.append({"阶段": stage_short, "指标": "项目个数", "数量": alert["project_count"]})
    if alert["unqc_count"] is not None:
        alert_chart_rows.append({"阶段": stage_short, "指标": "未完成质控个数", "数量": alert["unqc_count"]})
    alert_chart_rows.append({"阶段": stage_short, "指标": "未完成归档个数", "数量": alert["unarchived_count"]})
with st.container(border=True):
    alert_selection = render_multi_bar_chart(
        "各阶段异常情况对比",
        pd.DataFrame(alert_chart_rows),
        "阶段",
        "数量",
        "指标",
        key="alert_stage_comparison",
    )
    if alert_selection is not None:
        selected_stage, selected_metric = alert_selection
        scope_key = {
            "项目个数": "projects",
            "未完成质控个数": "unqc",
            "未完成归档个数": "unarchived",
        }.get(selected_metric)
        selected_scope = alert_scopes.get(selected_stage, {}).get(scope_key or "")
        if selected_scope is not None:
            show_project_detail(
                f"{selected_stage} · {selected_metric}",
                selected_scope,
            )

for alert_index, alert in enumerate(alerts):
    stage_name, stage_note = alert["stage"].split("（")
    stage_scopes = alert_scopes[stage_name]
    stage_projects = stage_scopes["projects"]
    unarchived_stage_projects = stage_scopes["unarchived"]
    unqc_stage_projects = stage_scopes["unqc"]
    region_focus_projects = stage_scopes["region_focus"]
    label_col, body_col = st.columns([1, 9])
    with label_col:
        render_row_label(stage_name, f"（{stage_note}")
    with body_col:
        b1, b2, b3 = st.columns([2, 2, 6])
        with b1:
            with st.container(border=True):
                render_project_kpi(
                    "项目个数",
                    f"{alert['project_count']}",
                    stage_projects,
                    key=f"drilldown_big_alert_{alert_index}_project_count",
                    context=f"{stage_name} · 项目个数",
                )
        with b2:
            with st.container(border=True):
                if alert["unqc_count"] is not None:
                    render_project_kpi(
                        "未完成质控个数",
                        f"{alert['unqc_count']}",
                        unqc_stage_projects if unqc_stage_projects is not None else raw.iloc[0:0],
                        key=f"drilldown_big_alert_{alert_index}_unqc_count",
                        context=f"{stage_name} · 未完成质控",
                    )
                else:
                    render_big_number("未完成质控个数", "无数据", "底表缺少 是否完成质控？ 字段")
                render_project_kpi(
                    "未完成归档个数",
                    f"{alert['unarchived_count']}",
                    unarchived_stage_projects,
                    key=f"drilldown_big_alert_{alert_index}_unarchived_count",
                    context=f"{stage_name} · 未完成归档",
                )
        with b3:
            with st.container(border=True):
                region_table = alert["region_table"]
                selected_cell = render_selectable_metric_table(
                    "业务部门未完成质控/归档项目个数",
                    region_table,
                    key=f"alert_region_{alert_index}",
                )
                if (
                    selected_cell is not None
                    and selected_cell[1] == "记录数"
                    and 0 <= selected_cell[0] < len(region_table)
                    and region_focus_projects is not None
                ):
                    unit = str(region_table.iloc[selected_cell[0]]["业务单元"])
                    focus_label = (
                        "未完成质控"
                        if alert["unqc_count"] is not None
                        else "未完成归档"
                    )
                    show_project_detail(
                        f"{stage_name} · {unit} · {focus_label}",
                        projects_of_unit(region_focus_projects, unit),
                    )

render_group_banner("归档合规分析（对应「进度信息分析」sheet）")
a1, a2 = st.columns(2)
with a1:
    with st.container(border=True):
        archive_view_1_selection = render_ratio_bar_chart(
            "视角一：各阶段项目整体归档率（递进合规视角）",
            metrics.archive_view_1,
            category_col="阶段",
            denominator_col="应归档项目数（分母）",
            numerator_col="已完成归档项目数（分子）",
            rate_col="归档率",
            denominator_label="应归档项目数（分母）",
            numerator_label="已完成归档项目数（分子）",
            rate_label="归档率",
            key="archive_view_1",
        )
        if archive_view_1_selection is not None:
            stage, measure = archive_view_1_selection
            completed = measure == "numerator"
            measure_label = {
                "numerator": "已完成递进归档项目",
                "denominator": "应归档项目",
                "rate": "归档率口径项目",
            }.get(measure, "归档项目")
            show_project_detail(
                f"视角一 · {stage} · {measure_label}",
                archive_view_1_project_subset(raw, stage, completed=completed),
            )
with a2:
    with st.container(border=True):
        archive_view_2_selection = render_ratio_bar_chart(
            "视角二：环节维度归档完成率（节点执行视角）",
            metrics.archive_view_2,
            category_col="归档环节",
            denominator_col="应完成归档环节数（分母）",
            numerator_col="已完成归档环节数（分子）",
            rate_col="环节完成率",
            denominator_label="应完成归档环节数（分母）",
            numerator_label="已完成归档环节数（分子）",
            rate_label="完成率",
            key="archive_view_2",
        )
        if archive_view_2_selection is not None:
            node, measure = archive_view_2_selection
            completed = measure == "numerator"
            measure_label = {
                "numerator": "已完成归档环节",
                "denominator": "应完成归档环节",
                "rate": "完成率口径归档环节",
            }.get(measure, "归档环节")
            show_project_detail(
                f"视角二 · {node} · {measure_label}",
                archive_view_2_record_subset(raw, node, completed=completed),
                count_label="归档环节",
            )
with st.expander("查看归档合规明细表"):
    d1, d2 = st.columns(2)
    with d1:
        render_metric_table("视角一：各阶段项目整体归档率（递进合规视角）", metrics.archive_view_1)
    with d2:
        render_metric_table("视角二：环节维度归档完成率（节点执行视角）", metrics.archive_view_2)

# ---------------------------------------------------------- 四、人效分析
render_section_banner("四、人效分析")

eff = metrics.efficiency
e1, e2 = st.columns([1, 2])
with e1:
    with st.container(border=True):
        render_metric_table("公司维度", eff.get("company"))
with e2:
    with st.container(border=True):
        render_metric_table("业务单元维度", eff.get("business_unit"))
with st.container(border=True):
    render_metric_table("单人维度（人效基础数据）", eff.get("person"))
st.caption("以上三表由底表实时计算，对应原工作簿的「人效分析」与「人效基础数据」sheet。")

# ---------------------------------------------------------- 五、26年人均净合同额（人员3口径）
render_section_banner("五、26年人均净合同额（人员3口径）")

if personnel3_parse_error:
    st.error(f"人员3口径输入解析失败：{personnel3_parse_error}")
elif personnel3_inputs is None or not personnel3_inputs.ready:
    st.info("当前文件未包含完整的人员3口径输入，原四章节仍可正常使用。")
    if personnel3_inputs is not None:
        with st.expander("查看缺失内容"):
            for error in personnel3_inputs.errors:
                st.error(error)
else:
    if personnel3_inputs.warnings:
        with st.expander("人员3口径数据提醒", expanded=True):
            for warning in personnel3_inputs.warnings:
                st.warning(warning)

    try:
        initial_matches = match_outsource_projects(
            personnel3_inputs.implementation,
            personnel3_inputs.outsource,
        )
        initial_project_detail = build_project_net_detail(
            personnel3_inputs.implementation,
            initial_matches,
        )
        project_options = [""] + initial_project_detail["项目管理编号"].astype(str).tolist()
        match_editor_data = initial_matches[
            [
                "外委序号",
                "外委项目名称",
                "服务采购金额",
                "匹配状态",
                "对应实施项目编号",
                "对应实施项目名称",
                "最高匹配度",
            ]
        ].copy()
        file_fingerprint = hashlib.sha256(uploaded_bytes).hexdigest()[:12]
        editor_key = f"personnel3_match_editor_{file_fingerprint}"

        render_group_banner("外委子项目匹配确认")
        with st.expander(
            "匹配确认表",
            expanded=initial_matches["匹配状态"].eq(NEEDS_CONFIRMATION).any(),
        ):
            reset_col, count_col = st.columns([1, 3])
            with reset_col:
                if st.button("重置匹配", key=f"reset_{editor_key}", use_container_width=True):
                    st.session_state.pop(editor_key, None)
                    st.rerun()
            with count_col:
                state_counts_text = "；".join(
                    f"{state} {int(count)}"
                    for state, count in initial_matches["匹配状态"].value_counts().items()
                )
                st.caption(f"系统初判：{state_counts_text}")
            edited_matches = st.data_editor(
                match_editor_data,
                key=editor_key,
                hide_index=True,
                use_container_width=True,
                num_rows="fixed",
                disabled=[
                    "外委序号",
                    "外委项目名称",
                    "服务采购金额",
                    "对应实施项目名称",
                    "最高匹配度",
                ],
                column_config={
                    "匹配状态": st.column_config.SelectboxColumn(
                        "匹配状态",
                        options=[MATCHED, NEEDS_CONFIRMATION, UNMATCHED],
                        required=True,
                    ),
                    "对应实施项目编号": st.column_config.SelectboxColumn(
                        "对应实施项目编号",
                        options=project_options,
                    ),
                    "服务采购金额": st.column_config.NumberColumn(format="%.2f"),
                    "最高匹配度": st.column_config.NumberColumn(format="%.1f%%"),
                },
            )

        confirmations = edited_matches[["外委序号", "匹配状态", "对应实施项目编号"]]
        personnel3_matches = match_outsource_projects(
            personnel3_inputs.implementation,
            personnel3_inputs.outsource,
            confirmations,
        )
        personnel3_project_detail = build_project_net_detail(
            personnel3_inputs.implementation,
            personnel3_matches,
        )
        personnel3_outputs = build_personnel3_outputs(
            personnel3_inputs.implementation,
            personnel3_inputs.people,
            personnel3_matches,
            personnel3_project_detail,
        )
        personnel3_value_payload = build_personnel3_value_workbook(
            personnel3_inputs,
            personnel3_matches,
            personnel3_project_detail,
            personnel3_outputs,
        )
        personnel3_formula_payload = build_personnel3_formula_workbook(
            personnel3_inputs,
            personnel3_matches,
            personnel3_project_detail,
            personnel3_outputs,
        )
    except Exception as exc:  # noqa: BLE001 - 第五章节失败不影响原报表
        st.error(f"人员3口径计算失败：{type(exc).__name__}: {exc}")
    else:
        st.caption("本章节按三张 input 表的全量口径计算，不受页面顶部进度筛选影响。")
        current_match_counts = "；".join(
            f"{state} {int(count)}"
            for state, count in personnel3_matches["匹配状态"].value_counts().items()
        )
        st.caption(f"当前确认结果：{current_match_counts}")
        export_info, export_value, export_formula = st.columns([2, 1, 1])
        with export_info:
            st.caption("下载内容使用当前匹配确认结果，并保留完整 input / calculation / output 审计链。")
        with export_value:
            st.download_button(
                "下载人员3结果",
                data=personnel3_value_payload,
                file_name=f"26年人均净合同额_人员3口径_{today}.xlsx",
                mime=mime_xlsx,
                use_container_width=True,
                help="数值版：保存当前确认后的全部输入、计算明细、结果、异常与核验。",
            )
        with export_formula:
            st.download_button(
                "下载人员3核算版",
                data=personnel3_formula_payload,
                file_name=f"26年人均净合同额_人员3口径_核算版_{today}.xlsx",
                mime=mime_xlsx,
                use_container_width=True,
                help="公式版：橙色表头和浅黄色单元格为活公式，可沿三张 input 表复核。",
            )
        included_projects = personnel3_project_detail.loc[
            personnel3_project_detail["是否纳入口径"].eq("是")
        ].copy()
        company_row = personnel3_outputs.company.iloc[0]
        p1, p2, p3, p4 = st.columns(4)
        with p1:
            with st.container(border=True):
                if render_clickable_big_number(
                    "纳入口径项目数",
                    f"{int(company_row['项目数'])}",
                    key="personnel3_company_projects",
                ):
                    show_personnel3_table("纳入口径项目", included_projects, count_label="项目")
        with p2:
            with st.container(border=True):
                if render_clickable_big_number(
                    "有效执行人数（人员3）",
                    f"{int(company_row['有效执行人数（人员3）'])}",
                    key="personnel3_company_people",
                ):
                    show_personnel3_table(
                        "人员3名单",
                        personnel3_outputs.personnel3_list,
                        count_label="人员",
                    )
        with p3:
            with st.container(border=True):
                if render_clickable_big_number(
                    "公司26年净执行合同额",
                    f"{float(company_row['26年净执行合同额']):,.2f}",
                    key="personnel3_company_amount",
                ):
                    show_personnel3_table("公司26年净执行合同额 · 项目明细", included_projects, count_label="项目")
        with p4:
            with st.container(border=True):
                if render_clickable_big_number(
                    "公司人均净合同额",
                    f"{float(company_row['人均净合同额']):,.2f}",
                    key="personnel3_company_average",
                ):
                    show_personnel3_table("公司人均净合同额 · 项目明细", included_projects, count_label="项目")

        render_group_banner("部门维度")
        department_chart_col, department_table_col = st.columns([1, 1])
        with department_chart_col:
            with st.container(border=True):
                selected_department = render_horizontal_ranking_chart(
                    "部门人均净合同额排名",
                    personnel3_outputs.department,
                    "部门",
                    "人均净合同额",
                    key="personnel3_department_ranking",
                )
                if selected_department is not None:
                    show_personnel3_department(
                        selected_department,
                        personnel3_project_detail,
                        personnel3_outputs.personnel3_list,
                    )
        with department_table_col:
            with st.container(border=True):
                department_selection = render_selectable_metric_table(
                    "部门人效汇总",
                    personnel3_outputs.department,
                    key="personnel3_department_table",
                )
                if department_selection is not None:
                    department_name = str(
                        personnel3_outputs.department.iloc[department_selection[0]]["部门"]
                    )
                    show_personnel3_department(
                        department_name,
                        personnel3_project_detail,
                        personnel3_outputs.personnel3_list,
                    )

        render_group_banner("人员与项目维度")
        person_col, project_col = st.columns(2)
        with person_col:
            with st.container(border=True):
                selected_person = render_horizontal_ranking_chart(
                    "人员326年净执行合同额排名",
                    personnel3_outputs.person,
                    "人员3",
                    "26年净执行合同额",
                    key="personnel3_person_ranking",
                    max_rows=22,
                )
                if selected_person is not None:
                    show_personnel3_table(
                        f"{selected_person} · 分摊项目",
                        personnel3_person_allocations(personnel3_outputs.allocation, selected_person),
                        count_label="分摊",
                    )
        with project_col:
            with st.container(border=True):
                project_ranking = included_projects[
                    ["项目管理编号", "项目名称", "纳入口径26年净执行合同额"]
                ].copy()
                project_ranking["项目"] = (
                    project_ranking["项目管理编号"].astype(str)
                    + " · "
                    + project_ranking["项目名称"].astype(str)
                )
                selected_project_label = render_horizontal_ranking_chart(
                    "项目26年净执行合同额贡献（前15）",
                    project_ranking,
                    "项目",
                    "纳入口径26年净执行合同额",
                    key="personnel3_project_ranking",
                    max_rows=15,
                )
                if selected_project_label is not None:
                    selected_project_id = selected_project_label.split(" · ", 1)[0]
                    show_personnel3_project(
                        selected_project_id,
                        personnel3_project_detail,
                        personnel3_matches,
                        personnel3_outputs.allocation,
                    )

        with st.expander("查看人员和项目完整表"):
            person_table_col, project_table_col = st.columns(2)
            with person_table_col:
                person_selection = render_selectable_metric_table(
                    "人员3明细",
                    personnel3_outputs.person,
                    key="personnel3_person_table",
                )
                if person_selection is not None:
                    person_name = str(personnel3_outputs.person.iloc[person_selection[0]]["人员3"])
                    show_personnel3_table(
                        f"{person_name} · 分摊项目",
                        personnel3_person_allocations(personnel3_outputs.allocation, person_name),
                        count_label="分摊",
                    )
            with project_table_col:
                project_table = included_projects[
                    ["项目管理编号", "项目名称", "项目净额归属部门", "纳入口径26年净执行合同额"]
                ].reset_index(drop=True)
                project_selection = render_selectable_metric_table(
                    "项目净额明细",
                    project_table,
                    key="personnel3_project_table",
                    clickable_columns={"项目管理编号", "项目名称", "纳入口径26年净执行合同额"},
                )
                if project_selection is not None:
                    selected_project_id = str(project_table.iloc[project_selection[0]]["项目管理编号"])
                    show_personnel3_project(
                        selected_project_id,
                        personnel3_project_detail,
                        personnel3_matches,
                        personnel3_outputs.allocation,
                    )

        render_group_banner("匹配、异常与核验")
        match_col, exception_col = st.columns(2)
        with match_col:
            with st.container(border=True):
                match_counts = (
                    personnel3_matches["匹配状态"]
                    .value_counts()
                    .rename_axis("匹配状态")
                    .reset_index(name="数量")
                )
                selected_match_state = render_count_chart(
                    "外委子项目匹配状态",
                    match_counts,
                    "匹配状态",
                    key="personnel3_match_status",
                )
                if selected_match_state is not None:
                    show_personnel3_table(
                        f"外委子项目 · {selected_match_state}",
                        personnel3_matches.loc[
                            personnel3_matches["匹配状态"].eq(selected_match_state)
                        ],
                        count_label="外委子项目",
                    )
        with exception_col:
            with st.container(border=True):
                exception_counts = (
                    personnel3_outputs.exceptions["异常类型"]
                    .value_counts()
                    .rename_axis("异常类型")
                    .reset_index(name="数量")
                )
                selected_exception = render_bar_chart(
                    "异常类型分布",
                    exception_counts,
                    "异常类型",
                    "数量",
                    key="personnel3_exception_types",
                )
                if selected_exception is not None:
                    show_personnel3_table(
                        f"异常类型 · {selected_exception}",
                        personnel3_exceptions_of_type(
                            personnel3_outputs.exceptions,
                            selected_exception,
                        ),
                        count_label="异常",
                    )
        with st.container(border=True):
            render_metric_table("核验结果", personnel3_outputs.checks)

# ---------------------------------------------------------- 原始数据
with st.expander("原始数据（含系统派生列）"):
    st.dataframe(raw, use_container_width=True)
