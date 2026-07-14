from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

import pandas as pd

from .data_loader import coerce_ratio_series, parse_excel_date_series, split_people
from .personnel3_loader import coerce_number_series


MATCHED = "已匹配"
NEEDS_CONFIRMATION = "需人工确认"
UNMATCHED = "未匹配"
YEAR_END = pd.Timestamp("2026-12-31")


def match_outsource_projects(
    implementation: pd.DataFrame,
    outsource: pd.DataFrame,
    confirmations: pd.DataFrame | None = None,
    *,
    auto_threshold: float = 0.75,
    confirmation_threshold: float = 0.45,
    minimum_margin: float = 0.10,
) -> pd.DataFrame:
    """Build auditable three-state matches for every outsourced subproject."""
    projects = _project_lookup(implementation)
    confirmation_map = _confirmation_map(confirmations)
    rows: list[dict] = []

    for offset, (_, source) in enumerate(outsource.iterrows(), start=2):
        outsource_id = _clean_identifier(source.get("序号")) or str(offset - 1)
        outsource_name = _clean_text(source.get("外委项目名称"))
        amount = _number(source.get("服务采购金额（元）"))
        source_project_id = _clean_identifier(source.get("项目管理编号"))

        scores = _score_projects(outsource_name, projects)
        best = scores[0] if scores else None
        second_score = scores[1][0] if len(scores) > 1 else 0.0
        best_score = best[0] if best else 0.0
        best_project = best[1] if best else None

        status = UNMATCHED
        selected = None
        note = "没有可信候选项目，本次不纳入外委采信金额。"

        confirmation = confirmation_map.get(outsource_id)
        if confirmation:
            requested_status, requested_project = confirmation
            if requested_status == MATCHED:
                selected = _project_by_key(projects, requested_project)
                if selected:
                    status = MATCHED
                    note = "已按人工确认匹配并纳入外委采信金额。"
                else:
                    status = NEEDS_CONFIRMATION
                    note = "人工确认指定的项目不存在，请重新选择。"
            elif requested_status in (NEEDS_CONFIRMATION, UNMATCHED):
                status = requested_status
                selected = best_project if status == NEEDS_CONFIRMATION else None
                note = "已按人工确认保留，当前不纳入外委采信金额。"
        elif source_project_id:
            candidates = [project for project in projects if project["项目管理编号"] == source_project_id]
            if len(candidates) == 1:
                status, selected = MATCHED, candidates[0]
                note = "按项目管理编号精确匹配。"
            elif len(candidates) > 1:
                status, selected = NEEDS_CONFIRMATION, candidates[0]
                note = "项目管理编号对应多条实施项目，需要人工确认。"
        if confirmation is None and selected is None and best_project:
            exact = _normalize_name(outsource_name) == best_project["标准化项目名称"]
            unique_exact = exact and sum(
                project["标准化项目名称"] == best_project["标准化项目名称"] for project in projects
            ) == 1
            high_confidence = best_score >= auto_threshold and best_score - second_score >= minimum_margin
            if unique_exact or high_confidence:
                status, selected = MATCHED, best_project
                note = "按项目名称精确匹配。" if unique_exact else "按高可信名称相似度匹配。"
            elif best_score >= confirmation_threshold:
                status, selected = NEEDS_CONFIRMATION, best_project
                note = "存在相似候选项目，需要人工确认后才能纳入。"

        accepted = amount if status == MATCHED and selected else 0.0
        rows.append(
            {
                "外委序号": outsource_id,
                "外委项目名称": outsource_name,
                "服务采购金额": amount,
                "匹配状态": status,
                "对应实施项目编号": selected["项目管理编号"] if selected else "",
                "对应实施项目名称": selected["项目名称"] if selected else "",
                "最高匹配度": best_score,
                "是否自动采信": status == MATCHED,
                "纳入采信金额": accepted,
                "处理说明": note,
            }
        )
    return pd.DataFrame(rows)


def build_project_net_detail(
    implementation: pd.DataFrame,
    outsource_matches: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate the project-level 2026 net amount defined by the handoff rules."""
    frame = implementation.copy()
    keys = _project_keys(frame)
    contract = _number_series(frame.get("C-中标/合同金额"), frame.index)
    estimated = _number_series(frame.get("预估项目金额"), frame.index)
    outsource_ratio = coerce_ratio_series(_series(frame, "B-服务采购比例")).replace(
        [float("inf"), float("-inf")], pd.NA
    ).fillna(0)
    opening_progress = coerce_ratio_series(_series(frame, "1/1进度")).replace(
        [float("inf"), float("-inf")], pd.NA
    ).fillna(0)
    start_dates = parse_excel_date_series(_series(frame, "开始执行日期"))
    acceptance_dates = parse_excel_date_series(_series(frame, "预计验收日期（若已签约，默认经法）"))

    base = contract.where(contract.notna() & contract.ne(0), estimated).fillna(0)
    accepted = outsource_matches.loc[
        outsource_matches["匹配状态"].eq(MATCHED),
        ["对应实施项目编号", "纳入采信金额"],
    ].copy()
    accepted["纳入采信金额"] = pd.to_numeric(accepted["纳入采信金额"], errors="coerce").fillna(0)
    accepted_sum = accepted.groupby("对应实施项目编号")["纳入采信金额"].sum()
    matched_amount = keys.map(accepted_sum).fillna(0)
    final_outsource = matched_amount.where(matched_amount.gt(0), outsource_ratio * base)
    final_outsource = final_outsource.where(base.ne(0), 0)
    net = base - final_outsource
    expected_progress = pd.Series(
        [_expected_year_end_progress(start, end) for start, end in zip(start_dates, acceptance_dates)],
        index=frame.index,
        dtype="float64",
    )
    annual_delta = (expected_progress - opening_progress).clip(lower=0)
    annual_net = net * annual_delta

    original_region = _series(frame, "A-项目经理区域").fillna("").astype(str).str.strip()
    included = ~original_region.str.contains("绿链|数字化市场团队", regex=True, na=False)

    detail = pd.DataFrame(
        {
            "项目管理编号": keys,
            "项目名称": _series(frame, "A-项目名称").fillna("").astype(str).str.strip(),
            "项目经理": _series(frame, "A-项目经理").fillna("").astype(str).str.strip(),
            "项目经理区域_原始": original_region,
            "项目净额归属部门": original_region.map(_net_department),
            "中标/合同金额": contract,
            "预计项目金额": estimated,
            "原服务采购比例": outsource_ratio,
            "开始执行日期": start_dates,
            "预计验收日期": acceptance_dates,
            "1/1进度": opening_progress,
            "净额取数基数": base,
            "外委子项目采信金额": matched_amount,
            "最终采信服务采购金额": final_outsource,
            "采信依据": [
                "项目金额缺失，待补"
                if project_base == 0
                else "已匹配外委子项目合计"
                if matched > 0
                else "原服务采购比例×净额取数基数"
                for project_base, matched in zip(base, matched_amount)
            ],
            "项目净执行合同额": net,
            "26/12/31预计进度": expected_progress,
            "年度进度差": annual_delta,
            "26年净执行合同额": annual_net,
            "是否纳入口径": included.map({True: "是", False: "否"}),
            "纳入口径26年净执行合同额": annual_net.where(included, 0),
        }
    )
    return detail


def _project_lookup(implementation: pd.DataFrame) -> list[dict]:
    keys = _project_keys(implementation)
    names = _series(implementation, "A-项目名称").fillna("").astype(str).str.strip()
    return [
        {
            "项目管理编号": key,
            "项目名称": name,
            "标准化项目名称": _normalize_name(name),
        }
        for key, name in zip(keys, names)
        if name
    ]


def _project_keys(implementation: pd.DataFrame) -> pd.Series:
    ids = _series(implementation, "项目管理编号")
    return pd.Series(
        [
            _clean_identifier(value) or f"未填项目编号_行{position}"
            for position, value in enumerate(ids, start=2)
        ],
        index=implementation.index,
        dtype="object",
    )


def _score_projects(name: str, projects: list[dict]) -> list[tuple[float, dict]]:
    normalized = _normalize_name(name)
    if not normalized:
        return []
    scored = [
        (SequenceMatcher(None, normalized, project["标准化项目名称"]).ratio(), project)
        for project in projects
        if project["标准化项目名称"]
    ]
    return sorted(scored, key=lambda item: item[0], reverse=True)


def _confirmation_map(confirmations: pd.DataFrame | None) -> dict[str, tuple[str, str]]:
    if confirmations is None or confirmations.empty:
        return {}
    required = {"外委序号", "匹配状态", "对应实施项目编号"}
    if not required.issubset(confirmations.columns):
        return {}
    return {
        _clean_identifier(row["外委序号"]): (
            _clean_text(row["匹配状态"]),
            _clean_identifier(row["对应实施项目编号"]),
        )
        for _, row in confirmations.iterrows()
        if _clean_identifier(row["外委序号"])
    }


def _project_by_key(projects: list[dict], key: str) -> dict | None:
    matches = [project for project in projects if project["项目管理编号"] == key]
    return matches[0] if len(matches) == 1 else None


def _expected_year_end_progress(start: object, acceptance: object) -> float:
    if pd.isna(start) or pd.isna(acceptance):
        return 1.0
    start = pd.Timestamp(start)
    acceptance = pd.Timestamp(acceptance)
    if start > YEAR_END:
        return 0.0
    if acceptance <= YEAR_END:
        return 1.0
    duration = (acceptance - start).days
    if duration <= 0:
        return 0.0
    return max(0.0, min(1.0, (YEAR_END - start).days / duration))


def _net_department(value: object) -> str:
    regions = split_people(value)
    without_guidance = [region for region in regions if "电碳市场团队" not in region]
    return ",".join(without_guidance or regions)


def _normalize_name(value: object) -> str:
    text = unicodedata.normalize("NFKC", _clean_text(value)).lower()
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]", "", text)


def _clean_identifier(value: object) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _clean_text(value: object) -> str:
    return "" if pd.isna(value) else str(value).strip()


def _number(value: object) -> float:
    parsed = coerce_number_series(pd.Series([value]), allow_percent=True).iloc[0]
    if pd.isna(parsed) or parsed in (float("inf"), float("-inf")):
        return 0.0
    return float(parsed)


def _number_series(series: pd.Series | None, index: pd.Index) -> pd.Series:
    source = series if series is not None else pd.Series(index=index, dtype="float64")
    return coerce_number_series(source)


def _series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column in frame:
        return frame[column]
    return pd.Series(pd.NA, index=frame.index, dtype="object")
