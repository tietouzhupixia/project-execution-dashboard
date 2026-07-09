from __future__ import annotations

import pandas as pd
import streamlit as st

from src.charts import (
    inject_css,
    render_bar_chart,
    render_big_number,
    render_count_chart,
    render_group_banner,
    render_metric_table,
    render_multi_bar_chart,
    render_ratio_bar_chart,
    render_row_label,
    render_section_banner,
)
from src.data_loader import load_workbook, parse_excel_date_series
from src.export import build_export_workbook
from src.metrics import (
    build_all_metrics,
    build_delivery_analysis,
    build_kpi_strip,
    build_stage_alerts,
    discover_business_units,
    filter_projects,
)


st.set_page_config(page_title="项目执行管理仪表盘", layout="wide")
inject_css()

st.title("项目执行管理仪表盘")
st.caption("上传 raw data（仅需包含 `实施进度底表`）后自动生成总览、进度、异常通报和人效分析。")

uploaded = st.file_uploader("上传 Excel 文件", type=["xlsx"])

if not uploaded:
    st.info("请上传包含 `实施进度底表` 的 Excel 文件。")
    st.stop()

workbook = load_workbook(uploaded)

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

metrics = build_all_metrics(raw, workbook.relation)
kpi = build_kpi_strip(raw)
delivery = build_delivery_analysis(raw)
alerts = build_stage_alerts(raw)

all_warnings = workbook.warnings + metrics.warnings
if all_warnings:
    with st.expander("数据提醒", expanded=True):
        for warning in all_warnings:
            st.warning(warning)

info_col, download_col = st.columns([3, 1])
with info_col:
    scope = f"筛选后 {len(raw)} / 共 {len(workbook.raw)}" if is_filtered else f"{len(raw)}"
    st.caption(f"识别底表：{workbook.source_sheet}；项目数：{scope}")
with download_col:
    st.download_button(
        "下载分析结果 Excel",
        data=build_export_workbook(raw, metrics, delivery, alerts),
        file_name=f"项目执行管理分析_{pd.Timestamp.now():%Y%m%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
if is_filtered:
    st.info("当前为筛选视图：以下所有图表、表格与导出文件均按筛选后的项目计算。")


def pct(value: float | None, digits: int = 2) -> str:
    return f"{value:.{digits}%}" if value is not None and value == value else "无"


# ------------------------------------------------------------------ 一、总览
overview = metrics.project_overview
as_of = overview.get("as_of")
as_of_text = f"-截至{as_of.month}月{as_of.day}日" if as_of is not None else ""
render_section_banner(f"一、公司项目执行管理总览{as_of_text}")

with st.container(border=True):
    render_big_number(
        "执行项目总数",
        f"{overview['total_projects']}",
        "年初至统计月末。包括往年遗留、当年新签、未签先执行三类项目；含未交付/已交付、未验收/已验收；未验收按项目阶段分类。",
    )

c1, c2 = st.columns(2)
with c1:
    with st.container(border=True):
        render_count_chart("其中：往年遗留、新签、未签先执行分布", overview["project_type"], "执行项目类型")
    with st.container(border=True):
        render_count_chart("其中：验收分布", overview["acceptance_split"], "状态")
    with st.container(border=True):
        render_count_chart("其中：交付分布", overview["delivery_split"], "状态")
with c2:
    with st.container(border=True):
        render_bar_chart("其中：预计验收年月分布", overview["estimated_acceptance_month"], "年月", "数量")
    with st.container(border=True):
        render_bar_chart("其中：预计交付年月分布", overview["estimated_delivery_month"], "年月", "数量")
    with st.container(border=True):
        render_count_chart("其中：对于未验收项目，项目阶段分布", overview["unaccepted_stage"], "进度分类")

# KPI 条
k1, k2, k3, k4 = st.columns(4)
with k1:
    with st.container(border=True):
        render_big_number("公司平均进度（新签未验收）", pct(kpi["avg_progress_new_unaccepted"], 1), "不含已交付项目")
with k2:
    with st.container(border=True):
        render_big_number("公司平均进度（遗留未验收）", pct(kpi["avg_progress_legacy_unaccepted"], 1), "不含已交付项目")
with k3:
    with st.container(border=True):
        render_big_number("公司平均进度偏差（所有未验收）", pct(kpi["avg_deviation_unaccepted"], 1), "实际完成进度-时间进度")
with k4:
    with st.container(border=True):
        render_big_number("公司项目关键进度归档完成度", pct(kpi["archive_completion_rate"]), "已完成归档环节数/应完成归档环节数")

# ---------------------------------------------------------- 二、进度情况
render_section_banner("二、项目执行进度情况")

s1, s2, s3 = st.columns(3)
summary = metrics.progress_summary
with s1:
    with st.container(border=True):
        render_metric_table("项目数（按业务单元）", summary.get("project_count"))
with s2:
    with st.container(border=True):
        render_metric_table("未验收项目数（按业务单元）", summary.get("unaccepted"))
with s3:
    with st.container(border=True):
        render_metric_table("已验收项目数（按业务单元）", summary.get("accepted"))

ref_year_text = f"{delivery['ref_year'] % 100}年"

# —— 未验收 · 当年交付
label_col, body_col = st.columns([1, 9])
with label_col:
    render_row_label("未验收", "当年交付")
with body_col:
    current = delivery["current_year"]
    b1, b2, b3, b4 = st.columns([2, 2, 2, 4])
    with b1:
        with st.container(border=True):
            render_big_number("当年交付项目个数", f"{current['count']}", "含逾期未交付项目")
    with b2:
        with st.container(border=True):
            render_big_number("平均进度", pct(current["avg_progress"]))
    with b3:
        with st.container(border=True):
            render_big_number("平均进度偏差", pct(current["avg_deviation"], 1), "实际完成进度-时间进度")
    with b4:
        with st.container(border=True):
            render_count_chart("进度偏差类型分布（在执行项目）", current["deviation_type"], "进度偏差分类")
    g1, g2 = st.columns(2)
    with g1:
        with st.container(border=True):
            render_bar_chart("预计交付年月", current["delivery_month"], "年月", "数量")
    with g2:
        with st.container(border=True):
            render_metric_table("业务部进度偏差排名", current["region_deviation_ranking"])

# —— 未验收 · 跨年交付
label_col, body_col = st.columns([1, 9])
with label_col:
    render_row_label("未验收", "跨年交付")
with body_col:
    cross = delivery["cross_year"]
    b1, b2, b3, b4 = st.columns([2, 2, 2, 4])
    with b1:
        with st.container(border=True):
            render_big_number("跨年交付项目个数", f"{cross['count']}")
    with b2:
        with st.container(border=True):
            render_big_number("平均进度", pct(cross["avg_progress"]))
    with b3:
        with st.container(border=True):
            render_big_number("平均进度偏差", pct(cross["avg_deviation"], 1), "实际完成进度-时间进度")
    with b4:
        with st.container(border=True):
            render_count_chart("偏差类型分布", cross["deviation_type"], "进度偏差分类")
    g1, g2 = st.columns(2)
    with g1:
        with st.container(border=True):
            render_bar_chart("预计交付年", cross["delivery_year"], "年份", "数量")
    with g2:
        with st.container(border=True):
            render_metric_table("项目进度偏差排名", cross["project_deviation_ranking"])

# —— 已验收
label_col, body_col = st.columns([1, 9])
with label_col:
    render_row_label("已验收")
with body_col:
    accepted = delivery["accepted"]
    b1, b2, b3 = st.columns([2, 2, 4])
    with b1:
        with st.container(border=True):
            render_big_number("已交付项目个数", f"{accepted['count']}")
    with b2:
        with st.container(border=True):
            render_big_number(f"{ref_year_text}交付率", pct(accepted["delivery_rate"]), accepted["delivery_rate_detail"])
    with b3:
        with st.container(border=True):
            render_count_chart("偏差类型分布", accepted["deviation_type"], "进度偏差分类")
    with st.container(border=True):
        render_metric_table("业务部已交付未验收项目个数排名", accepted["delivered_unaccepted_ranking"])

# ---------------------------------------------------------- 三、异常通报
render_section_banner("三、项目执行管理异常情况通报")

alert_chart_rows = []
for alert in alerts:
    stage_short = alert["stage"].split("（")[0]
    alert_chart_rows.append({"阶段": stage_short, "指标": "项目个数", "数量": alert["project_count"]})
    if alert["unqc_count"] is not None:
        alert_chart_rows.append({"阶段": stage_short, "指标": "未完成质控个数", "数量": alert["unqc_count"]})
    alert_chart_rows.append({"阶段": stage_short, "指标": "未完成归档个数", "数量": alert["unarchived_count"]})
with st.container(border=True):
    render_multi_bar_chart("各阶段异常情况对比", pd.DataFrame(alert_chart_rows), "阶段", "数量", "指标")

for alert in alerts:
    stage_name, stage_note = alert["stage"].split("（")
    label_col, body_col = st.columns([1, 9])
    with label_col:
        render_row_label(stage_name, f"（{stage_note}")
    with body_col:
        b1, b2, b3 = st.columns([2, 2, 6])
        with b1:
            with st.container(border=True):
                render_big_number("项目个数", f"{alert['project_count']}")
        with b2:
            with st.container(border=True):
                if alert["unqc_count"] is not None:
                    render_big_number("未完成质控个数", f"{alert['unqc_count']}")
                else:
                    render_big_number("未完成质控个数", "无数据", "底表缺少 是否完成质控？ 字段")
                render_big_number("未完成归档个数", f"{alert['unarchived_count']}")
        with b3:
            with st.container(border=True):
                render_metric_table("业务部门未完成质控/归档项目个数", alert["region_table"])

render_group_banner("归档合规分析（对应「进度信息分析」sheet）")
a1, a2 = st.columns(2)
with a1:
    with st.container(border=True):
        render_ratio_bar_chart(
            "视角一：各阶段项目整体归档率（递进合规视角）",
            metrics.archive_view_1,
            category_col="阶段",
            denominator_col="应归档项目数（分母）",
            numerator_col="已完成归档项目数（分子）",
            rate_col="归档率",
            denominator_label="应归档项目数（分母）",
            numerator_label="已完成归档项目数（分子）",
            rate_label="归档率",
        )
with a2:
    with st.container(border=True):
        render_ratio_bar_chart(
            "视角二：环节维度归档完成率（节点执行视角）",
            metrics.archive_view_2,
            category_col="归档环节",
            denominator_col="应完成归档环节数（分母）",
            numerator_col="已完成归档环节数（分子）",
            rate_col="环节完成率",
            denominator_label="应完成归档环节数（分母）",
            numerator_label="已完成归档环节数（分子）",
            rate_label="完成率",
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

# ---------------------------------------------------------- 原始数据
with st.expander("原始数据（含系统派生列）"):
    st.dataframe(raw, use_container_width=True)
