from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .data_loader import (
    EXEC_PERSON_COLUMNS,
    EXEC_RATIO_COLUMNS,
    parse_excel_date_series,
    split_people,
)


YES = "是"


@dataclass
class MetricResult:
    project_overview: dict
    progress_tables: dict[str, pd.DataFrame]
    progress_summary: dict[str, pd.DataFrame]
    archive_view_1: pd.DataFrame
    archive_view_2: pd.DataFrame
    efficiency: dict[str, pd.DataFrame]
    warnings: list[str]


def build_all_metrics(raw: pd.DataFrame, relation: pd.DataFrame | None = None) -> MetricResult:
    warnings: list[str] = []
    project_overview = build_project_overview(raw)
    progress_tables = build_progress_tables(raw)
    progress_summary = build_progress_summary(raw)
    archive_view_1 = build_archive_view_1(raw)
    archive_view_2 = build_archive_view_2(raw)
    efficiency = build_efficiency(raw, relation, warnings)
    return MetricResult(
        project_overview=project_overview,
        progress_tables=progress_tables,
        progress_summary=progress_summary,
        archive_view_1=archive_view_1,
        archive_view_2=archive_view_2,
        efficiency=efficiency,
        warnings=warnings,
    )


def build_progress_summary(raw: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Replicate 进度信息分析 left blocks: counts by business unit (DATA_RULES §11).

    Units come dynamically from comma-split A-项目经理区域 in first-seen order.
    """
    units = discover_business_units(raw)
    name_col = raw["A-项目名称"] if "A-项目名称" in raw.columns else pd.Series(pd.NA, index=raw.index)
    has_name = name_col.notna() & (name_col.astype(str).str.strip() != "")
    status = raw["交付状态"].astype(str) if "交付状态" in raw.columns else pd.Series("", index=raw.index)
    unit_sets = raw.get("A-项目经理区域", pd.Series(pd.NA, index=raw.index)).map(
        lambda v: set(split_regions(v)) if pd.notna(v) else set()
    )

    def block(mask: pd.Series, value_name: str) -> pd.DataFrame:
        rows = [{"业务单元": "公司整体", value_name: int(mask.sum())}]
        for unit in units:
            in_unit = unit_sets.map(lambda s: unit in s)
            rows.append({"业务单元": unit, value_name: int((mask & in_unit).sum())})
        return pd.DataFrame(rows)

    return {
        "project_count": block(has_name, "项目数"),
        "unaccepted": block(status.str.contains("未验收", na=False), "未验收项目数"),
        "accepted": block(status.str.contains("已验收", na=False), "已验收项目数"),
    }


def discover_business_units(raw: pd.DataFrame) -> list[str]:
    """Collect business units from A-项目经理区域 in first-seen order."""
    if "A-项目经理区域" not in raw.columns:
        return []
    units: list[str] = []
    seen: set[str] = set()
    for value in raw["A-项目经理区域"]:
        if pd.isna(value):
            continue
        for unit in split_regions(value):
            if unit != "未填" and unit not in seen:
                seen.add(unit)
                units.append(unit)
    return units


def build_project_overview(raw: pd.DataFrame) -> dict:
    total = len(raw)
    status = raw["交付状态"].astype(str) if "交付状态" in raw.columns else pd.Series("", index=raw.index)
    unaccepted_rows = raw.loc[status.str.contains("未验收", na=False)]

    as_of = None
    if "最新进度更新日期" in raw.columns:
        parsed = parse_excel_date_series(raw["最新进度更新日期"])
        if parsed.notna().any():
            as_of = parsed.max()

    return {
        "total_projects": total,
        "as_of": as_of,
        "project_type": value_counts(raw, "执行项目类型"),
        "delivery_status": value_counts(raw, "交付状态"),
        "acceptance_split": keyword_split(status, "已验收", "未验收"),
        "delivery_split": keyword_split(status, "已交付", "未交付"),
        "progress_stage": value_counts(raw, "进度分类"),
        "unaccepted_stage": value_counts(unaccepted_rows, "进度分类"),
        "deviation_type": value_counts(raw, "进度偏差分类"),
        "estimated_delivery_month": month_counts_collapsed(raw, "预计交付日期"),
        "estimated_acceptance_month": month_counts_collapsed(raw, "预计验收日期（若已签约，默认经法）"),
    }


def keyword_split(status: pd.Series, positive: str, negative: str) -> pd.DataFrame:
    """Binary split of a compound status column, e.g. 已验收 vs 未验收."""
    labels = status.map(
        lambda s: positive if positive in s else (negative if negative in s else "未填")
    )
    return labels.value_counts().rename_axis("状态").reset_index(name="数量")


def build_progress_tables(raw: pd.DataFrame) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}

    if "A-项目经理区域" in raw.columns and "进度偏差" in raw.columns:
        region_rows = explode_region(raw)
        tables["business_unit_deviation"] = (
            region_rows.groupby("业务单元", dropna=False)["进度偏差"]
            .mean()
            .reset_index()
            .sort_values("进度偏差", ascending=False)
        )

    project_cols = [c for c in ["A-项目名称", "当前进度", "时间进度", "进度偏差", "进度偏差分类"] if c in raw.columns]
    if project_cols:
        tables["project_deviation"] = raw[project_cols].copy().sort_values(
            "进度偏差", ascending=True if "进度偏差" in project_cols else False
        )

    return tables


ARCHIVE_VIEW_1_RULES = [
    ("启动阶段", "10%<=当前进度<50%", 0.1, 0.5, ["启动归档"]),
    ("中期阶段", "50%<=当前进度<90%", 0.5, 0.9, ["启动归档", "中期归档"]),
    ("终期阶段", "当前进度>=90%", 0.9, None, ["启动归档", "中期归档", "临近终期归档"]),
]

ARCHIVE_VIEW_2_RULES = [
    ("启动归档环节", "当前进度>=10%", 0.1, "启动归档"),
    ("中期归档环节", "当前进度>=50%", 0.5, "中期归档"),
    ("终期归档环节", "当前进度>=90%", 0.9, "临近终期归档"),
]


def build_archive_view_1(raw: pd.DataFrame) -> pd.DataFrame:
    """Project-stage progressive compliance view."""
    result = []
    for stage, scope, low, high, checks in ARCHIVE_VIEW_1_RULES:
        scoped = progress_scope(raw, low, high)
        denominator = len(scoped)
        numerator = int(scoped.apply(lambda row: all(row.get(col) == YES for col in checks), axis=1).sum())
        result.append(
            {
                "阶段": stage,
                "进度范围": scope,
                "应归档项目数（分母）": denominator,
                "已完成归档项目数（分子）": numerator,
                "归档率": safe_rate(numerator, denominator),
            }
        )

    total_denominator = sum(row["应归档项目数（分母）"] for row in result)
    total_numerator = sum(row["已完成归档项目数（分子）"] for row in result)
    result.append(
        {
            "阶段": "整体",
            "进度范围": "当前进度>=10%",
            "应归档项目数（分母）": total_denominator,
            "已完成归档项目数（分子）": total_numerator,
            "归档率": safe_rate(total_numerator, total_denominator),
        }
    )
    return pd.DataFrame(result)


def build_archive_view_2(raw: pd.DataFrame) -> pd.DataFrame:
    """Archive-node completion view."""
    result = []
    for node, condition, threshold, archive_col in ARCHIVE_VIEW_2_RULES:
        scoped = progress_scope(raw, threshold, None)
        denominator = len(scoped)
        numerator = int((scoped.get(archive_col) == YES).sum()) if archive_col in scoped.columns else 0
        result.append(
            {
                "归档环节": node,
                "触发条件": condition,
                "应完成归档环节数（分母）": denominator,
                "已完成归档环节数（分子）": numerator,
                "环节完成率": safe_rate(numerator, denominator),
            }
        )

    total_denominator = sum(row["应完成归档环节数（分母）"] for row in result)
    total_numerator = sum(row["已完成归档环节数（分子）"] for row in result)
    result.append(
        {
            "归档环节": "整体",
            "触发条件": "三类环节合计",
            "应完成归档环节数（分母）": total_denominator,
            "已完成归档环节数（分子）": total_numerator,
            "环节完成率": safe_rate(total_numerator, total_denominator),
        }
    )
    return pd.DataFrame(result)


def archive_view_1_project_subset(
    raw: pd.DataFrame,
    stage: str,
    *,
    completed: bool,
) -> pd.DataFrame:
    """Reverse one view-1 denominator/numerator bar to its source projects."""
    if stage == "整体":
        parts = [
            archive_view_1_project_subset(raw, rule[0], completed=completed)
            for rule in ARCHIVE_VIEW_1_RULES
        ]
        return pd.concat(parts).sort_index() if parts else raw.iloc[0:0].copy()

    rule = next((item for item in ARCHIVE_VIEW_1_RULES if item[0] == stage), None)
    if rule is None:
        return raw.iloc[0:0].copy()
    _, _, low, high, checks = rule
    scoped = progress_scope(raw, low, high)
    if not completed:
        return scoped

    complete = pd.Series(True, index=scoped.index)
    for column in checks:
        if column not in scoped.columns:
            return scoped.iloc[0:0].copy()
        complete &= scoped[column].astype(str).str.strip().eq(YES)
    return scoped.loc[complete].copy()


def archive_view_2_record_subset(
    raw: pd.DataFrame,
    node: str,
    *,
    completed: bool,
) -> pd.DataFrame:
    """Reverse one view-2 bar to archive-node records (projects may repeat)."""
    if node == "整体":
        parts = [
            archive_view_2_record_subset(raw, rule[0], completed=completed)
            for rule in ARCHIVE_VIEW_2_RULES
        ]
        return pd.concat(parts, ignore_index=True) if parts else raw.iloc[0:0].copy()

    rule = next((item for item in ARCHIVE_VIEW_2_RULES if item[0] == node), None)
    if rule is None:
        return raw.iloc[0:0].copy()
    _, _, threshold, archive_col = rule
    scoped = progress_scope(raw, threshold, None)
    if completed:
        if archive_col not in scoped.columns:
            scoped = scoped.iloc[0:0].copy()
        else:
            scoped = scoped.loc[
                scoped[archive_col].astype(str).str.strip().eq(YES)
            ].copy()
    detail = scoped.copy()
    detail.insert(0, "归档环节", node)
    return detail


def build_efficiency(raw: pd.DataFrame, relation: pd.DataFrame | None, warnings: list[str]) -> dict[str, pd.DataFrame]:
    if "收入" not in raw.columns:
        warnings.append("No 收入 column; efficiency analysis cannot be calculated.")
        empty = pd.DataFrame()
        return {"company": empty, "business_unit": empty, "person": empty}

    relation_area = build_person_area_mapping(relation)
    project_area = build_person_area_from_projects(raw)
    person_area = {**project_area, **relation_area}
    rows = []
    for _, project in raw.iterrows():
        income = number_or_zero(project.get("收入"))
        outsource = number_or_zero(project.get("B-服务采购比例"))
        net_base = income * (1 - outsource)
        for person_col, ratio_col in zip(EXEC_PERSON_COLUMNS, EXEC_RATIO_COLUMNS):
            person = project.get(person_col)
            ratio = number_or_zero(project.get(ratio_col))
            if pd.isna(person) or not str(person).strip() or ratio == 0:
                continue
            rows.append(
                {
                    "人员": str(person).strip(),
                    "净执行合同额": net_base * ratio,
                    "执行比例是否虚拟": bool(project.get("执行比例是否虚拟", False)),
                }
            )

    if rows:
        person = pd.DataFrame(rows).groupby("人员", as_index=False).agg(
            净执行合同额=("净执行合同额", "sum"),
            含虚拟比例=("执行比例是否虚拟", "any"),
        )
    else:
        warnings.append("No execution people or ratios available; efficiency amounts are all zero.")
        person = pd.DataFrame(columns=["人员", "净执行合同额", "含虚拟比例"])

    all_people = ordered_people(relation_area, project_area, person["人员"].tolist())
    if all_people:
        person = (
            pd.DataFrame({"人员": all_people})
            .merge(person, on="人员", how="left")
            .fillna({"净执行合同额": 0, "含虚拟比例": False})
        )
    person["所属区域/业务单元"] = person["人员"].map(person_area).fillna("未匹配")
    person["数据说明"] = build_data_notes(person, relation_area)

    unit = (
        person.groupby("所属区域/业务单元", as_index=False)
        .agg(
            净执行合同额=("净执行合同额", "sum"),
            人员数=("人员", "count"),
            有净额人数=("净执行合同额", lambda s: int((s > 0).sum())),
        )
        .sort_values("净执行合同额", ascending=False)
    )
    unit["人均净额（全部）"] = unit["净执行合同额"] / unit["人员数"].where(unit["人员数"] > 0)
    unit["人均净额（有净额）"] = unit["净执行合同额"] / unit["有净额人数"].where(unit["有净额人数"] > 0)

    total = person["净执行合同额"].sum()
    active_count = int((person["净执行合同额"] > 0).sum())
    company = pd.DataFrame(
        [
            {"指标": "公司净执行合同额", "值": total},
            {"指标": "统计人员数", "值": len(person)},
            {"指标": "有净额人数", "值": active_count},
            {"指标": "人均净执行合同额（全部人员）", "值": total / len(person) if len(person) else 0},
            {
                "指标": "人均净执行合同额（有净额人员）",
                "值": total / max(active_count, 1),
            },
        ]
    )

    return {"company": company, "business_unit": unit, "person": person.sort_values("净执行合同额", ascending=False)}


def filter_projects(
    raw: pd.DataFrame,
    units: list[str] | None = None,
    managers: list[str] | None = None,
    stages: list[str] | None = None,
    months: list[str] | None = None,
) -> pd.DataFrame:
    """Filter the raw sheet by dashboard controls; empty selections mean no filter."""
    mask = pd.Series(True, index=raw.index)

    if units and "A-项目经理区域" in raw.columns:
        selected = set(units)
        mask &= raw["A-项目经理区域"].map(
            lambda v: bool(selected & set(split_regions(v))) if pd.notna(v) else False
        )
    if managers and "A-项目经理" in raw.columns:
        mask &= raw["A-项目经理"].astype(str).str.strip().isin(managers)
    if stages and "进度分类" in raw.columns:
        mask &= raw["进度分类"].astype(str).str.strip().isin(stages)
    if months and "预计交付日期" in raw.columns:
        labels = parse_excel_date_series(raw["预计交付日期"]).dt.strftime("%y年%m月").fillna("未填")
        mask &= labels.isin(months)

    return raw.loc[mask].copy()


def build_kpi_strip(raw: pd.DataFrame) -> dict:
    """KPI cards below section 1 (reference image 2)."""
    progress = pd.to_numeric(raw.get("当前进度"), errors="coerce") if "当前进度" in raw.columns else pd.Series(dtype=float)
    deviation = pd.to_numeric(raw.get("进度偏差"), errors="coerce") if "进度偏差" in raw.columns else pd.Series(dtype=float)
    status = raw["交付状态"].astype(str) if "交付状态" in raw.columns else pd.Series("", index=raw.index)
    ptype = raw["执行项目类型"].astype(str) if "执行项目类型" in raw.columns else pd.Series("", index=raw.index)

    unaccepted = status.str.contains("未验收", na=False)
    new_unaccepted = unaccepted & ptype.str.contains("新签", na=False)
    legacy_unaccepted = unaccepted & ptype.str.contains("遗留", na=False)

    view2 = build_archive_view_2(raw)
    overall = view2.loc[view2["归档环节"] == "整体", "环节完成率"]

    return {
        "avg_progress_new_unaccepted": float(progress[new_unaccepted].mean()) if new_unaccepted.any() else None,
        "avg_progress_legacy_unaccepted": float(progress[legacy_unaccepted].mean()) if legacy_unaccepted.any() else None,
        "avg_deviation_unaccepted": float(deviation[unaccepted].mean()) if unaccepted.any() else None,
        "archive_completion_rate": float(overall.iloc[0]) if not overall.empty else None,
    }


def build_delivery_analysis(raw: pd.DataFrame, ref_year: int | None = None) -> dict:
    """Section 2 groups (reference images 3-4): 未验收[当年/跨年] and 已验收."""
    ref_year = ref_year or pd.Timestamp.now().year
    dates = parse_excel_date_series(raw["预计交付日期"]) if "预计交付日期" in raw.columns else pd.Series(pd.NaT, index=raw.index)
    year = dates.dt.year

    current_mask = delivery_group_mask(raw, "current_unaccepted", ref_year)
    cross_mask = delivery_group_mask(raw, "cross_unaccepted", ref_year)
    accepted_mask = delivery_group_mask(raw, "accepted", ref_year)
    delivered = raw["交付状态"].astype(str).str.contains("已交付", na=False) if "交付状态" in raw.columns else pd.Series(False, index=raw.index)
    unaccepted = raw["交付状态"].astype(str).str.contains("未验收", na=False) if "交付状态" in raw.columns else pd.Series(False, index=raw.index)

    def group_stats(mask: pd.Series) -> dict:
        scoped = raw.loc[mask]
        progress = pd.to_numeric(scoped.get("当前进度"), errors="coerce") if "当前进度" in scoped.columns else pd.Series(dtype=float)
        deviation = pd.to_numeric(scoped.get("进度偏差"), errors="coerce") if "进度偏差" in scoped.columns else pd.Series(dtype=float)
        return {
            "count": int(mask.sum()),
            "avg_progress": float(progress.mean()) if progress.notna().any() else None,
            "avg_deviation": float(deviation.mean()) if deviation.notna().any() else None,
            "deviation_type": value_counts(scoped, "进度偏差分类"),
        }

    current = group_stats(current_mask)
    current["delivery_month"] = month_counts(raw.loc[current_mask], "预计交付日期")
    if "A-项目经理区域" in raw.columns and "进度偏差" in raw.columns and current_mask.any():
        current["region_deviation_ranking"] = (
            explode_region(raw.loc[current_mask])
            .groupby("业务单元", dropna=False)["进度偏差"]
            .mean()
            .reset_index()
            .rename(columns={"进度偏差": "进度偏差（平均值）"})
            .sort_values("进度偏差（平均值）", ascending=False)
        )
    else:
        current["region_deviation_ranking"] = pd.DataFrame()

    cross = group_stats(cross_mask)
    cross_years = year[cross_mask].dropna().astype(int).astype(str) + "年"
    cross["delivery_year"] = (
        cross_years.value_counts().rename_axis("年份").reset_index(name="数量").sort_values("年份")
        if not cross_years.empty
        else pd.DataFrame(columns=["年份", "数量"])
    )
    rank_cols = [c for c in ["A-项目名称", "进度偏差"] if c in raw.columns]
    cross["project_deviation_ranking"] = (
        raw.loc[cross_mask, rank_cols].sort_values("进度偏差", ascending=False)
        if len(rank_cols) == 2
        else pd.DataFrame()
    )

    accepted = group_stats(accepted_mask)
    due_current = int((year == ref_year).sum())
    delivered_current = int((delivered & (year == ref_year)).sum())
    accepted["delivery_rate"] = safe_rate(delivered_current, due_current)
    accepted["delivery_rate_detail"] = f"{ref_year % 100}年已交付 {delivered_current} / 应交付 {due_current}"
    delivered_unaccepted = delivered & unaccepted
    if "A-项目经理区域" in raw.columns and delivered_unaccepted.any():
        accepted["delivered_unaccepted_ranking"] = (
            explode_region(raw.loc[delivered_unaccepted])
            .groupby("业务单元", dropna=False)
            .size()
            .reset_index(name="项目个数")
            .sort_values("项目个数", ascending=False)
        )
    else:
        accepted["delivered_unaccepted_ranking"] = pd.DataFrame()

    return {"ref_year": ref_year, "current_year": current, "cross_year": cross, "accepted": accepted}


STAGE_ALERT_RULES = [
    ("项目启动（进度达10%）", "启动应归档", "启动已归档"),
    ("项目中期（进度达50%）", "中期应归档", "中期已归档"),
    ("项目临近终期（进度达90%）", "临近中期应归档", "临近中期已归档"),
]


def stage_alert_project_subsets(raw: pd.DataFrame, stage: str) -> dict[str, pd.DataFrame | None]:
    """Return the exact project scopes behind one stage-alert metric group."""
    rule = next((item for item in STAGE_ALERT_RULES if item[0] == stage), None)
    if rule is None:
        empty = raw.iloc[0:0].copy()
        return {
            "projects": empty,
            "unqc": None,
            "unarchived": empty,
            "region_focus": empty,
        }

    _, due_col, done_col = rule
    due = (
        pd.to_numeric(raw[due_col], errors="coerce").fillna(0).astype(int)
        if due_col in raw.columns
        else pd.Series(0, index=raw.index)
    )
    done = (
        pd.to_numeric(raw[done_col], errors="coerce").fillna(0).astype(int)
        if done_col in raw.columns
        else pd.Series(0, index=raw.index)
    )
    in_stage = due.eq(1)
    projects = raw.loc[in_stage].copy()
    unarchived = raw.loc[in_stage & done.eq(0)].copy()

    if "是否完成质控？" in raw.columns:
        qc = raw["是否完成质控？"].astype(str).str.strip()
        unqc: pd.DataFrame | None = raw.loc[in_stage & qc.ne("是")].copy()
        region_focus = unqc
    else:
        unqc = None
        region_focus = unarchived

    return {
        "projects": projects,
        "unqc": unqc,
        "unarchived": unarchived,
        "region_focus": region_focus,
    }


def build_stage_alerts(raw: pd.DataFrame) -> list[dict]:
    """Section 3 (reference images 5-6): per-stage incomplete QC/archive counts.

    Expects a normalized frame (derived action columns present).
    """
    alerts = []
    for stage, _, _ in STAGE_ALERT_RULES:
        subsets = stage_alert_project_subsets(raw, stage)
        projects = subsets["projects"]
        unqc = subsets["unqc"]
        unarchived = subsets["unarchived"]
        focus = subsets["region_focus"]
        if "A-项目经理区域" in raw.columns and focus is not None and not focus.empty:
            region_table = (
                explode_region(focus)
                .groupby("业务单元", dropna=False)
                .size()
                .reset_index(name="记录数")
                .sort_values("记录数", ascending=False)
            )
        else:
            region_table = pd.DataFrame(columns=["业务单元", "记录数"])

        alerts.append(
            {
                "stage": stage,
                "project_count": len(projects) if projects is not None else 0,
                "unarchived_count": len(unarchived) if unarchived is not None else 0,
                "unqc_count": len(unqc) if unqc is not None else None,
                "region_table": region_table,
            }
        )
    return alerts


def build_data_notes(person: pd.DataFrame, relation_area: dict[str, str]) -> pd.Series:
    """人效基础数据 数据说明 column (DATA_RULES §12)."""
    if not relation_area:
        return pd.Series("无人员关系表-区域按项目推断", index=person.index)

    def note(row: pd.Series) -> str:
        if str(row["人员"]) not in relation_area:
            return "执行名单补充-临时归属待确认"
        if row["净执行合同额"] > 0:
            return "人员关系表匹配/当前有执行数据"
        return "人员关系表匹配/当前无执行数据"

    return person.apply(note, axis=1)


def build_person_area_mapping(relation: pd.DataFrame | None) -> dict[str, str]:
    if relation is None or relation.empty:
        return {}

    mapping: dict[str, str] = {}
    # 新版三表工作簿以“人员 3 / 所属区域 3”为正式口径；旧字段仅作兼容回退。
    # 同一人员在多个口径中出现时，保留排在最前面的人员3归属。
    pairs = [
        ("人员 3", "所属区域 3"),
        ("人员 2", "所属区域 2"),
        ("人员", "所属区域"),
    ]
    for person_col, area_col in pairs:
        if person_col not in relation.columns or area_col not in relation.columns:
            continue
        for _, row in relation.iterrows():
            person = row.get(person_col)
            area = row.get(area_col)
            if pd.notna(person) and pd.notna(area) and str(person).strip() not in mapping:
                mapping[str(person).strip()] = str(area).strip()
    return mapping


def build_person_area_from_projects(raw: pd.DataFrame) -> dict[str, str]:
    """Infer person area from the project region as a fallback."""
    if "A-项目经理区域" not in raw.columns:
        return {}

    votes: dict[str, dict[str, int]] = {}
    for _, project in raw.iterrows():
        regions = split_regions(project.get("A-项目经理区域"))
        if not regions:
            continue
        region = regions[0]
        for person_col in EXEC_PERSON_COLUMNS:
            person = project.get(person_col)
            if pd.isna(person) or not str(person).strip():
                continue
            name = str(person).strip()
            votes.setdefault(name, {})
            votes[name][region] = votes[name].get(region, 0) + 1

    inferred = {}
    for person, counts in votes.items():
        inferred[person] = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return inferred


def ordered_people(*sources: object) -> list[str]:
    """Return people in stable first-seen order from mappings/lists."""
    result: list[str] = []
    seen: set[str] = set()
    for source in sources:
        if isinstance(source, dict):
            values = source.keys()
        else:
            values = source or []
        for value in values:
            if pd.isna(value):
                continue
            name = str(value).strip()
            if name and name not in seen:
                seen.add(name)
                result.append(name)
    return result


def progress_scope(raw: pd.DataFrame, low: float, high: float | None) -> pd.DataFrame:
    if "当前进度" not in raw.columns:
        return raw.iloc[0:0].copy()
    progress = pd.to_numeric(raw["当前进度"], errors="coerce")
    mask = progress >= low
    if high is not None:
        mask &= progress < high
    return raw.loc[mask].copy()


def value_counts(raw: pd.DataFrame, column: str) -> pd.DataFrame:
    if column not in raw.columns:
        return pd.DataFrame(columns=[column, "数量"])
    return raw[column].fillna("未填").value_counts().rename_axis(column).reset_index(name="数量")


def month_counts(raw: pd.DataFrame, column: str) -> pd.DataFrame:
    if column not in raw.columns:
        return pd.DataFrame(columns=["年月", "数量"])
    months = parse_excel_date_series(raw[column]).dt.strftime("%y年%m月").fillna("未填")
    return months.value_counts().rename_axis("年月").reset_index(name="数量")


def month_counts_collapsed(raw: pd.DataFrame, column: str, ref_year: int | None = None) -> pd.DataFrame:
    """当年（及以前）按月、当年之后的年份折叠为整年（DATA_RULES §12）。"""
    if column not in raw.columns:
        return pd.DataFrame(columns=["年月", "数量"])
    ref_year = ref_year or pd.Timestamp.now().year
    labels = collapsed_month_labels(raw[column], ref_year)
    return labels.value_counts().rename_axis("年月").reset_index(name="数量")


def collapsed_month_labels(series: pd.Series, ref_year: int | None = None) -> pd.Series:
    """Use the exact labels shown by collapsed overview month charts."""
    ref_year = ref_year or pd.Timestamp.now().year
    dates = parse_excel_date_series(series)

    def label(value: object) -> str:
        if pd.isna(value):
            return "未填"
        if value.year > ref_year:
            return f"{value.year % 100}年"
        return value.strftime("%y年%m月")

    return dates.map(label)


def project_subset_by_value(raw: pd.DataFrame, column: str, value: str) -> pd.DataFrame:
    """Return rows matching an exact chart category, including the 未填 bucket."""
    if column not in raw.columns:
        return raw.iloc[0:0].copy()
    series = raw[column]
    if value == "未填":
        mask = series.isna() | series.astype(str).str.strip().eq("")
    else:
        mask = series.astype(str).str.strip().eq(str(value).strip())
    return raw.loc[mask].copy()


def project_subset_by_keyword(
    raw: pd.DataFrame,
    column: str,
    value: str,
    positive: str,
    negative: str,
) -> pd.DataFrame:
    """Mirror keyword_split so a clicked binary status maps back to source rows."""
    if column not in raw.columns:
        return raw.iloc[0:0].copy()
    series = raw[column].astype(str)
    positive_mask = series.str.contains(positive, na=False)
    negative_mask = series.str.contains(negative, na=False)
    if value == positive:
        mask = positive_mask
    elif value == negative:
        mask = ~positive_mask & negative_mask
    else:
        mask = ~positive_mask & ~negative_mask
    return raw.loc[mask].copy()


def project_subset_by_month(
    raw: pd.DataFrame,
    column: str,
    value: str,
    *,
    collapsed: bool,
    ref_year: int | None = None,
) -> pd.DataFrame:
    """Map a clicked date bar back to projects using the same displayed labels."""
    if column not in raw.columns:
        return raw.iloc[0:0].copy()
    if collapsed:
        labels = collapsed_month_labels(raw[column], ref_year)
    else:
        labels = parse_excel_date_series(raw[column]).dt.strftime("%y年%m月").fillna("未填")
    return raw.loc[labels.eq(value)].copy()


def delivery_group_mask(raw: pd.DataFrame, group: str, ref_year: int | None = None) -> pd.Series:
    """Single source of truth for section-2 project groups and their drill-downs."""
    ref_year = ref_year or pd.Timestamp.now().year
    status = raw["交付状态"].astype(str) if "交付状态" in raw.columns else pd.Series("", index=raw.index)
    dates = parse_excel_date_series(raw["预计交付日期"]) if "预计交付日期" in raw.columns else pd.Series(pd.NaT, index=raw.index)
    year = dates.dt.year
    unaccepted = status.str.contains("未验收", na=False)

    groups = {
        "current_unaccepted": unaccepted & ~(year > ref_year),
        "cross_unaccepted": unaccepted & (year > ref_year),
        "accepted": status.str.contains("已验收", na=False),
        "delivered_unaccepted": status.str.contains("已交付", na=False) & unaccepted,
    }
    if group not in groups:
        raise ValueError(f"Unknown delivery group: {group}")
    return groups[group]


def project_subset_by_delivery_group(
    raw: pd.DataFrame,
    group: str,
    ref_year: int | None = None,
) -> pd.DataFrame:
    return raw.loc[delivery_group_mask(raw, group, ref_year)].copy()


def projects_of_unit(raw: pd.DataFrame, unit: str) -> pd.DataFrame:
    """某业务部的项目子集；多区域项目按包含匹配归入每个区域（DATA_RULES §13）。"""
    if "A-项目经理区域" not in raw.columns:
        return raw.iloc[0:0].copy()
    mask = raw["A-项目经理区域"].map(
        lambda v: unit in split_regions(v) if pd.notna(v) else False
    )
    return raw.loc[mask].copy()


def explode_region(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in raw.iterrows():
        regions = split_regions(row.get("A-项目经理区域"))
        for region in regions:
            new_row = row.copy()
            new_row["业务单元"] = region
            rows.append(new_row)
    return pd.DataFrame(rows)


def split_regions(value: object) -> list[str]:
    return split_people(value) or ["未填"]


def number_or_zero(value: object) -> float:
    if pd.isna(value):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def safe_rate(numerator: int | float, denominator: int | float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0
