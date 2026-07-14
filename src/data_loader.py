from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO

import pandas as pd


PRIMARY_SHEET = "实施进度底表"
RELATION_SHEETS = ("input_人员关系表", "人员关系表")

KEY_COLUMNS = ["A-项目名称", "当前进度", "交付状态"]

EXEC_PERSON_COLUMNS = [f"执行人员{i}" for i in range(1, 6)]
EXEC_RATIO_COLUMNS = [f"执行人员{i}执行比例" for i in range(1, 6)]


@dataclass
class WorkbookData:
    raw: pd.DataFrame
    relation: pd.DataFrame | None
    source_sheet: str
    warnings: list[str]


def load_workbook(file: str | BinaryIO) -> WorkbookData:
    """Load the uploaded workbook and return normalized data frames."""
    xls = pd.ExcelFile(file)
    sheet = detect_raw_sheet(xls)
    raw = pd.read_excel(xls, sheet_name=sheet)
    relation = None
    for relation_sheet in RELATION_SHEETS:
        if relation_sheet in xls.sheet_names:
            relation = pd.read_excel(xls, sheet_name=relation_sheet)
            break

    warnings = []
    missing = [col for col in KEY_COLUMNS if col not in raw.columns]
    if missing:
        warnings.append(f"缺少关键字段：{', '.join(missing)}")

    raw = normalize_raw_data(raw, warnings)
    return WorkbookData(raw=raw, relation=relation, source_sheet=sheet, warnings=warnings)


def display_columns(df: pd.DataFrame) -> list[str]:
    """Columns to show in reader-facing detail views: original order, no derived helpers."""
    return [c for c in df.columns if c not in DERIVED_HELPER_COLUMNS]


def detect_raw_sheet(xls: pd.ExcelFile) -> str:
    """Prefer the official raw sheet, otherwise scan for key columns."""
    if PRIMARY_SHEET in xls.sheet_names:
        return PRIMARY_SHEET

    for sheet in xls.sheet_names:
        sample = pd.read_excel(xls, sheet_name=sheet, nrows=3)
        if all(col in sample.columns for col in KEY_COLUMNS):
            return sheet

    return xls.sheet_names[0]


def normalize_raw_data(df: pd.DataFrame, warnings: list[str] | None = None) -> pd.DataFrame:
    """Normalize percentage, date, and execution-ratio fields."""
    warnings = warnings if warnings is not None else []
    out = df.copy()

    for col in ["当前进度", "进度偏差", "时间进度", "B-服务采购比例", *EXEC_RATIO_COLUMNS]:
        if col in out.columns:
            out[col] = coerce_ratio_series(out[col])

    for col in ["收入", "C-中标/合同金额", "预估项目金额"]:
        # pandas 3 把纯文本列读成 str dtype（非 object），用数值判断反向识别
        if col in out.columns and not pd.api.types.is_numeric_dtype(out[col]):
            cleaned = out[col].astype(str).str.replace(",", "", regex=False).str.replace("，", "", regex=False)
            numeric = pd.to_numeric(cleaned, errors="coerce")
            failed = int((out[col].notna() & numeric.isna()).sum())
            if failed:
                warnings.append(f"{col} 有 {failed} 个值无法解析为数字（如带货币符号/单位），已按空值处理。")
            out[col] = numeric

    for col in ["预计交付日期", "预计验收日期（若已签约，默认经法）", "最新进度更新日期", "开始执行日期"]:
        if col in out.columns:
            out[col] = parse_excel_date_series(out[col])

    ensure_execution_people_and_ratios(out, warnings)
    derive_archive_action_columns(out, warnings)
    return out


# (derived name, progress threshold, source archive column)
ARCHIVE_ACTION_RULES = [
    ("启动应归档", "启动已归档", 0.1, "启动归档"),
    ("中期应归档", "中期已归档", 0.5, "中期归档"),
    ("临近中期应归档", "临近中期已归档", 0.9, "临近终期归档"),
]

# 系统在规范化阶段派生的辅助列，展示明细时应排除（仅保留上传的原始列）。
VIRTUAL_RATIO_FLAG = "执行比例是否虚拟"
DERIVED_HELPER_COLUMNS = [VIRTUAL_RATIO_FLAG] + [
    col for due, done, _, _ in ARCHIVE_ACTION_RULES for col in (due, done)
]


def derive_archive_action_columns(df: pd.DataFrame, warnings: list[str]) -> None:
    """Recompute the six 应归档/已归档 action columns from progress + archive marks.

    Uploads may lack these columns entirely (DATA_RULES §10); when present they may
    be stale static values, so they are always recomputed and overwritten.
    """
    progress = pd.to_numeric(df.get("当前进度"), errors="coerce") if "当前进度" in df.columns else pd.Series(pd.NA, index=df.index)

    missing_sources = [col for _, _, _, col in ARCHIVE_ACTION_RULES if col not in df.columns]
    if missing_sources:
        warnings.append(f"缺少归档字段：{', '.join(missing_sources)}，对应“已归档”列按 0 处理。")

    overwritten: list[str] = []
    for due_col, done_col, threshold, source_col in ARCHIVE_ACTION_RULES:
        due = ((progress.notna()) & (progress >= threshold)).astype(int)
        if source_col in df.columns:
            done = ((due == 1) & (df[source_col].astype(str).str.strip() == "是")).astype(int)
        else:
            done = pd.Series(0, index=df.index)

        for col, values in ((due_col, due), (done_col, done)):
            if col in df.columns:
                uploaded = pd.to_numeric(df[col], errors="coerce")
                conflict = uploaded.notna() & (uploaded.astype("Int64") != values)
                if conflict.any():
                    overwritten.append(col)
            df[col] = values

    if overwritten:
        warnings.append(
            f"上传文件中的 {', '.join(sorted(set(overwritten)))} 与当前进度/归档状态不一致，已按规则重新计算。"
        )


def coerce_ratio_series(series: pd.Series) -> pd.Series:
    """Parse ratio columns tolerating percent strings like "50%"."""
    numeric = pd.to_numeric(series, errors="coerce")
    # 覆盖 object 与 pandas 3 的 str dtype 两种文本列
    if not pd.api.types.is_numeric_dtype(series):
        text = series.astype(str).str.strip()
        is_percent = text.str.endswith("%")
        if is_percent.any():
            percent_values = pd.to_numeric(text.str.rstrip("%"), errors="coerce") / 100
            numeric = numeric.fillna(percent_values.where(is_percent))
    return numeric


def parse_excel_date_series(series: pd.Series) -> pd.Series:
    """Parse Excel serials or normal date strings into pandas timestamps.

    Serial numbers must be handled before pd.to_datetime: on integers it
    silently interprets them as epoch nanoseconds (46387 -> 1970-01-01).
    """
    if pd.api.types.is_datetime64_any_dtype(series):
        return series

    numeric = pd.to_numeric(series, errors="coerce")
    # Plausible Excel date serial range: 1954-11-06 .. 2119-01-24
    serial = numeric.where((numeric >= 20000) & (numeric <= 80000))
    parsed_serial = pd.to_datetime(serial, unit="D", origin="1899-12-30", errors="coerce")
    parsed_general = pd.to_datetime(series.where(serial.isna()), errors="coerce", format="mixed")
    return parsed_serial.fillna(parsed_general)


def ensure_execution_people_and_ratios(df: pd.DataFrame, warnings: list[str]) -> None:
    """Create virtual equal-split execution people/ratios when manual fields are blank."""
    # 人名列必须是 object dtype：整列为空的上传会被读成 float64，
    # pandas 3.x 往 float 列写字符串直接抛 TypeError。
    for col in EXEC_PERSON_COLUMNS:
        if col not in df.columns:
            df[col] = pd.Series(pd.NA, index=df.index, dtype="object")
        elif df[col].dtype != object:
            df[col] = df[col].astype("object")
    for col in EXEC_RATIO_COLUMNS:
        if col not in df.columns:
            df[col] = pd.Series(float("nan"), index=df.index, dtype="float64")

    df["执行比例是否虚拟"] = detect_virtual_ratio_marker(df)

    source_col = "A-执行人员"
    if source_col not in df.columns:
        warnings.append("缺少 A-执行人员 字段，人效分析可能不完整。")
        return

    for idx, raw_names in df[source_col].items():
        names = split_people(raw_names)
        if not names:
            continue

        existing_ratio = [
            df.at[idx, col]
            for col in EXEC_RATIO_COLUMNS
            if pd.notna(df.at[idx, col])
        ]
        has_manual = len(existing_ratio) > 0
        if has_manual:
            continue

        share = 1 / min(len(names), 5)
        for i, name in enumerate(names[:5]):
            df.at[idx, EXEC_PERSON_COLUMNS[i]] = name
            df.at[idx, EXEC_RATIO_COLUMNS[i]] = share
        df.at[idx, "执行比例是否虚拟"] = True

    if df["执行比例是否虚拟"].any():
        warnings.append("部分执行比例为系统虚拟均分占位值，正式使用前需要业务方确认。")


def detect_virtual_ratio_marker(df: pd.DataFrame) -> pd.Series:
    """Detect ratios already marked as virtual in a previous Excel workflow."""
    markers = pd.Series(False, index=df.index)
    marker_columns = [
        "最新执行比例更新日期",
        "数据说明",
        "执行比例说明",
    ]
    for col in marker_columns:
        if col in df.columns:
            marker_text = df[col].astype(str)
            markers |= marker_text.str.contains("虚拟填充|按人数均分|待确认", regex=True, na=False)
            # Some legacy generated workbooks may contain mojibake question marks
            # in the marker column. Treat these as virtual placeholders too.
            markers |= marker_text.str.contains(r"\?{2,}", regex=True, na=False)
    return markers


NAME_SEPARATORS = ("，", "、", "；", ";")


def split_people(value: object) -> list[str]:
    """Split a delimited name/region list; single source of truth for separators."""
    if pd.isna(value):
        return []
    text = str(value)
    for sep in NAME_SEPARATORS:
        text = text.replace(sep, ",")
    return [part.strip() for part in text.split(",") if part.strip()]
