import io

import pandas as pd

from src.data_loader import load_workbook, normalize_raw_data, parse_excel_date_series
from src.export import build_export_workbook
from src.metrics import (
    build_all_metrics,
    build_archive_view_1,
    build_archive_view_2,
    build_delivery_analysis,
    build_efficiency,
    build_kpi_strip,
    build_progress_summary,
    build_stage_alerts,
    filter_projects,
)


def test_archive_views():
    raw = pd.DataFrame(
        [
            {"当前进度": 0.2, "启动归档": "是", "中期归档": "否", "临近终期归档": "否"},
            {"当前进度": 0.7, "启动归档": "是", "中期归档": "是", "临近终期归档": "否"},
            {"当前进度": 0.95, "启动归档": "是", "中期归档": "否", "临近终期归档": "是"},
        ]
    )

    view1 = build_archive_view_1(raw)
    assert view1.loc[view1["阶段"] == "启动阶段", "已完成归档项目数（分子）"].iloc[0] == 1
    assert view1.loc[view1["阶段"] == "中期阶段", "已完成归档项目数（分子）"].iloc[0] == 1
    assert view1.loc[view1["阶段"] == "终期阶段", "已完成归档项目数（分子）"].iloc[0] == 0

    view2 = build_archive_view_2(raw)
    assert view2.loc[view2["归档环节"] == "启动归档环节", "已完成归档环节数（分子）"].iloc[0] == 3
    assert view2.loc[view2["归档环节"] == "中期归档环节", "已完成归档环节数（分子）"].iloc[0] == 1
    assert view2.loc[view2["归档环节"] == "终期归档环节", "已完成归档环节数（分子）"].iloc[0] == 1


def test_virtual_execution_ratio_and_efficiency():
    warnings = []
    raw = pd.DataFrame(
        [
            {
                "A-执行人员": "A,B",
                "收入": 100,
                "B-服务采购比例": 0.2,
            }
        ]
    )
    normalized = normalize_raw_data(raw, warnings)
    assert normalized.loc[0, "执行人员1"] == "A"
    assert normalized.loc[0, "执行人员1执行比例"] == 0.5
    assert normalized.loc[0, "执行人员2"] == "B"
    assert normalized.loc[0, "执行人员2执行比例"] == 0.5

    efficiency = build_efficiency(normalized, relation=None, warnings=[])
    person = efficiency["person"].set_index("人员")
    assert person.loc["A", "净执行合同额"] == 40
    assert person.loc["B", "净执行合同额"] == 40


def test_derive_archive_action_columns_when_absent():
    """Uploads without the 6 action columns must get them recomputed (DATA_RULES §10)."""
    raw = pd.DataFrame(
        [
            {"当前进度": 0.2, "启动归档": "是", "中期归档": "否", "临近终期归档": "否"},
            {"当前进度": 0.95, "启动归档": "是", "中期归档": "是", "临近终期归档": "否"},
            {"当前进度": None, "启动归档": "是", "中期归档": "是", "临近终期归档": "是"},
        ]
    )
    out = normalize_raw_data(raw, [])

    assert out["启动应归档"].tolist() == [1, 1, 0]
    assert out["启动已归档"].tolist() == [1, 1, 0]
    assert out["中期应归档"].tolist() == [0, 1, 0]
    assert out["中期已归档"].tolist() == [0, 1, 0]
    assert out["临近中期应归档"].tolist() == [0, 1, 0]
    assert out["临近中期已归档"].tolist() == [0, 0, 0]


def test_derived_action_columns_overwrite_stale_uploaded_values():
    raw = pd.DataFrame(
        [{"当前进度": 0.2, "启动归档": "是", "启动应归档": 0, "启动已归档": 0}]
    )
    warnings: list[str] = []
    out = normalize_raw_data(raw, warnings)
    assert out.loc[0, "启动应归档"] == 1
    assert out.loc[0, "启动已归档"] == 1
    assert any("重新计算" in w for w in warnings)


def test_blank_uploaded_action_values_recomputed_without_warning():
    """NaN (e.g. uncached formulas) is not a conflict — recompute silently."""
    raw = pd.DataFrame(
        [{"当前进度": 0.2, "启动归档": "是", "启动应归档": None, "启动已归档": None}]
    )
    warnings: list[str] = []
    out = normalize_raw_data(raw, warnings)
    assert out.loc[0, "启动应归档"] == 1
    assert out.loc[0, "启动已归档"] == 1
    assert not any("重新计算" in w for w in warnings)


def test_progress_summary_blocks():
    """进度信息分析 left blocks: counts by dynamic business unit (DATA_RULES §11)."""
    raw = pd.DataFrame(
        [
            {"A-项目名称": "P1", "A-项目经理区域": "华东事业部", "交付状态": "未验收"},
            {"A-项目名称": "P2", "A-项目经理区域": "华东事业部，华北业务部", "交付状态": "已验收"},
            {"A-项目名称": "P3", "A-项目经理区域": "华北业务部", "交付状态": "执行中-未验收"},
        ]
    )
    summary = build_progress_summary(raw)

    total = summary["project_count"].set_index("业务单元")["项目数"]
    assert total["公司整体"] == 3
    assert total["华东事业部"] == 2
    assert total["华北业务部"] == 2

    unaccepted = summary["unaccepted"].set_index("业务单元")["未验收项目数"]
    assert unaccepted["公司整体"] == 2
    assert unaccepted["华东事业部"] == 1
    assert unaccepted["华北业务部"] == 1

    accepted = summary["accepted"].set_index("业务单元")["已验收项目数"]
    assert accepted["公司整体"] == 1
    assert accepted["华东事业部"] == 1
    assert accepted["华北业务部"] == 1


def test_efficiency_data_note_with_relation():
    """人效基础数据 数据说明 rules (DATA_RULES §12)."""
    raw = normalize_raw_data(
        pd.DataFrame([{"A-执行人员": "张三,李四", "收入": 100, "B-服务采购比例": 0}]), []
    )
    relation = pd.DataFrame(
        [
            {"人员": "张三", "所属区域": "华东事业部"},
            {"人员": "王五", "所属区域": "华北业务部"},
        ]
    )
    person = build_efficiency(raw, relation=relation, warnings=[])["person"].set_index("人员")

    assert person.loc["张三", "数据说明"] == "人员关系表匹配/当前有执行数据"
    assert person.loc["王五", "数据说明"] == "人员关系表匹配/当前无执行数据"
    assert person.loc["李四", "数据说明"] == "执行名单补充-临时归属待确认"


def test_efficiency_data_note_without_relation():
    raw = normalize_raw_data(
        pd.DataFrame([{"A-执行人员": "张三", "收入": 100, "B-服务采购比例": 0,
                       "A-项目经理区域": "华东事业部"}]), []
    )
    person = build_efficiency(raw, relation=None, warnings=[])["person"].set_index("人员")
    assert person.loc["张三", "数据说明"] == "无人员关系表-区域按项目推断"


def test_column_order_and_extra_columns_do_not_matter():
    """DATA_RULES §9: reordered + extra columns must give identical archive metrics."""
    base = pd.DataFrame(
        [
            {"当前进度": 0.2, "启动归档": "是", "中期归档": "否", "临近终期归档": "否"},
            {"当前进度": 0.7, "启动归档": "是", "中期归档": "是", "临近终期归档": "否"},
        ]
    )
    shuffled = base[list(reversed(base.columns))].copy()
    shuffled["新增列X"] = "whatever"

    v1_base = build_archive_view_1(normalize_raw_data(base, []))
    v1_shuffled = build_archive_view_1(normalize_raw_data(shuffled, []))
    pd.testing.assert_frame_equal(v1_base, v1_shuffled)


def _reference_raw() -> pd.DataFrame:
    """Small dataset covering the section-2/3 grouping rules from reference UI."""
    return normalize_raw_data(
        pd.DataFrame(
            [
                # 当年交付、未验收、启动阶段、质控未完成
                {"A-项目名称": "P1", "A-项目经理区域": "华东事业部", "交付状态": "未交付-未验收",
                 "执行项目类型": "26年新签", "当前进度": 0.2, "进度偏差": -0.1, "进度偏差分类": "进度显著落后",
                 "预计交付日期": "2026-12-01", "启动归档": "否", "中期归档": "否", "临近终期归档": "否",
                 "是否完成质控？": "否"},
                # 跨年交付、未验收、中期阶段、质控完成
                {"A-项目名称": "P2", "A-项目经理区域": "华北业务部", "交付状态": "未交付-未验收",
                 "执行项目类型": "往年遗留", "当前进度": 0.6, "进度偏差": 0.05, "进度偏差分类": "进度正常",
                 "预计交付日期": "2027-06-01", "启动归档": "是", "中期归档": "是", "临近终期归档": "否",
                 "是否完成质控？": "是"},
                # 当年交付、已交付-已验收、临近终期
                {"A-项目名称": "P3", "A-项目经理区域": "华东事业部", "交付状态": "已交付-已验收",
                 "执行项目类型": "26年新签", "当前进度": 1.0, "进度偏差": 0.0, "进度偏差分类": "进度正常",
                 "预计交付日期": "2026-06-01", "启动归档": "是", "中期归档": "是", "临近终期归档": "是",
                 "是否完成质控？": "否"},
            ]
        ),
        [],
    )


def test_kpi_strip():
    kpi = build_kpi_strip(_reference_raw())
    assert kpi["avg_progress_new_unaccepted"] == 0.2          # 只有 P1 是新签未验收
    assert kpi["avg_progress_legacy_unaccepted"] == 0.6       # 只有 P2 是遗留未验收
    assert abs(kpi["avg_deviation_unaccepted"] - (-0.025)) < 1e-9  # (-0.1+0.05)/2
    # 归档完成度 = 视角二整体：分母 3(启动)+2(中期)+1(终期)=6，分子 2+2+1=5
    assert abs(kpi["archive_completion_rate"] - 5 / 6) < 1e-9


def test_delivery_analysis_groups():
    result = build_delivery_analysis(_reference_raw(), ref_year=2026)

    current = result["current_year"]
    assert current["count"] == 1                     # P1（未验收且 2026 年交付）
    assert current["avg_progress"] == 0.2
    assert current["avg_deviation"] == -0.1

    cross = result["cross_year"]
    assert cross["count"] == 1                       # P2（2027 年交付）
    assert cross["avg_progress"] == 0.6
    ranking = cross["project_deviation_ranking"]
    assert ranking.iloc[0]["A-项目名称"] == "P2"

    accepted = result["accepted"]
    assert accepted["count"] == 1                    # P3
    # 当年交付率 = 当年已交付 1 / 当年应交付 2 (P1, P3)
    assert abs(accepted["delivery_rate"] - 0.5) < 1e-9


def test_stage_alerts():
    alerts = build_stage_alerts(_reference_raw())
    by_stage = {a["stage"]: a for a in alerts}

    start = by_stage["项目启动（进度达10%）"]
    assert start["project_count"] == 3               # 三个项目进度都 >=10%
    assert start["unarchived_count"] == 1            # P1 启动未归档
    assert start["unqc_count"] == 2                  # P1、P3 质控未完成

    mid = by_stage["项目中期（进度达50%）"]
    assert mid["project_count"] == 2                 # P2、P3
    assert mid["unarchived_count"] == 0
    assert mid["unqc_count"] == 1                    # P3

    final = by_stage["项目临近终期（进度达90%）"]
    assert final["project_count"] == 1               # P3
    assert final["unqc_count"] == 1
    region = final["region_table"]
    assert region.iloc[0]["业务单元"] == "华东事业部"


def test_filter_projects():
    raw = _reference_raw().assign(**{"A-项目经理": ["张三", "李四", "张三"]})

    assert len(filter_projects(raw)) == 3  # 空选=不过滤

    by_unit = filter_projects(raw, units=["华北业务部"])
    assert by_unit["A-项目名称"].tolist() == ["P2"]

    by_manager = filter_projects(raw, managers=["张三"])
    assert by_manager["A-项目名称"].tolist() == ["P1", "P3"]

    by_month = filter_projects(raw, months=["26年12月"])
    assert by_month["A-项目名称"].tolist() == ["P1"]

    combined = filter_projects(raw, units=["华东事业部"], managers=["张三"], months=["26年06月"])
    assert combined["A-项目名称"].tolist() == ["P3"]


def test_filter_projects_multi_region_membership():
    raw = normalize_raw_data(
        pd.DataFrame(
            [{"A-项目名称": "P1", "A-项目经理区域": "华东事业部，华北业务部", "当前进度": 0.2}]
        ),
        [],
    )
    assert len(filter_projects(raw, units=["华北业务部"])) == 1
    assert len(filter_projects(raw, units=["西部业务部"])) == 0


def test_build_export_workbook_sheets_and_values():
    raw = _reference_raw()
    metrics = build_all_metrics(raw, relation=None)
    delivery = build_delivery_analysis(raw, ref_year=2026)
    alerts = build_stage_alerts(raw)

    payload = build_export_workbook(raw, metrics, delivery, alerts)
    book = pd.ExcelFile(io.BytesIO(payload))
    for sheet in ["项目验收汇总", "归档分析", "异常通报", "人效分析", "人效基础数据", "实施进度底表"]:
        assert sheet in book.sheet_names

    archive = pd.read_excel(book, sheet_name="归档分析", header=None)
    text = archive.fillna("").astype(str).to_numpy().ravel().tolist()
    assert any("视角一" in t for t in text)
    assert any("视角二" in t for t in text)

    base = pd.read_excel(book, sheet_name="实施进度底表")
    assert "启动应归档" in base.columns


def test_parse_excel_date_series_handles_serials_strings_datetimes():
    """Excel serial ints must not be misparsed as 1970 epoch nanoseconds."""
    serials = pd.Series([46387, 46022])          # 2026-12-31, 2025-12-31
    parsed = parse_excel_date_series(serials)
    assert parsed.dt.year.tolist() == [2026, 2025]
    assert parsed.iloc[0].month == 12

    strings = pd.Series(["2026-12-31", "2027/06/01", None])
    parsed = parse_excel_date_series(strings)
    assert parsed.dt.year.dropna().tolist() == [2026.0, 2027.0]

    datetimes = pd.Series(pd.to_datetime(["2026-06-26", "2025-01-01"]))
    parsed = parse_excel_date_series(datetimes)
    assert parsed.dt.year.tolist() == [2026, 2025]

    mixed = pd.Series([46387, "2027-06-01", None])
    parsed = parse_excel_date_series(mixed)
    assert parsed.iloc[0].year == 2026
    assert parsed.iloc[1].year == 2027
    assert pd.isna(parsed.iloc[2])


def test_load_workbook_with_only_raw_sheet():
    """DATA_RULES §9: a workbook containing only 实施进度底表 must load cleanly."""
    df = pd.DataFrame(
        [{"A-项目名称": "P1", "当前进度": 0.3, "交付状态": "未验收", "启动归档": "是"}]
    )
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="实施进度底表", index=False)
    buffer.seek(0)

    workbook = load_workbook(buffer)
    assert workbook.relation is None
    assert workbook.source_sheet == "实施进度底表"
    assert workbook.raw.loc[0, "启动应归档"] == 1
    assert workbook.raw.loc[0, "启动已归档"] == 1

