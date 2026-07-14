from __future__ import annotations

from dataclasses import dataclass, field
from typing import BinaryIO

import pandas as pd


IMPLEMENTATION_ALIASES = ("input_实施进度表", "实施进度底表")
OUTSOURCE_ALIASES = ("input_外委更新金额",)
PEOPLE_ALIASES = ("input_人员关系表", "人员关系表")

IMPLEMENTATION_REQUIRED = [
    "A-项目名称",
    "项目管理编号",
    "A-项目经理区域",
    "C-中标/合同金额",
    "预估项目金额",
    "B-服务采购比例",
    "开始执行日期",
    "预计验收日期（若已签约，默认经法）",
    "1/1进度",
    *[item for i in range(1, 6) for item in (f"执行人员{i}", f"执行人员{i}执行比例")],
]
OUTSOURCE_REQUIRED = ["外委项目名称", "服务采购金额（元）"]
PEOPLE_REQUIRED = ["人员 3", "所属区域 3"]


@dataclass
class Personnel3Inputs:
    """The three untouched input tables plus validation results."""

    implementation: pd.DataFrame = field(default_factory=pd.DataFrame)
    outsource: pd.DataFrame = field(default_factory=pd.DataFrame)
    people: pd.DataFrame = field(default_factory=pd.DataFrame)
    source_sheets: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not self.errors


def load_personnel3_inputs(file: str | BinaryIO) -> Personnel3Inputs:
    """Read and validate the personnel-3 input contract without changing values."""
    xls = pd.ExcelFile(file)
    result = Personnel3Inputs()

    implementation_sheet = _find_sheet(
        xls,
        IMPLEMENTATION_ALIASES,
        discovery_columns=("A-项目名称", "项目管理编号", "1/1进度"),
    )
    outsource_sheet = _find_sheet(xls, OUTSOURCE_ALIASES)
    people_sheet = _find_sheet(xls, PEOPLE_ALIASES)

    result.implementation = _read_or_error(
        xls, implementation_sheet, "实施进度表", IMPLEMENTATION_ALIASES, result
    )
    result.outsource = _read_or_error(
        xls, outsource_sheet, "外委更新金额", OUTSOURCE_ALIASES, result
    )
    result.people = _read_or_error(
        xls, people_sheet, "人员关系表", PEOPLE_ALIASES, result
    )

    for logical, sheet in (
        ("implementation", implementation_sheet),
        ("outsource", outsource_sheet),
        ("people", people_sheet),
    ):
        if sheet:
            result.source_sheets[logical] = sheet

    _validate_columns(result.implementation, "实施进度表", IMPLEMENTATION_REQUIRED, result.errors)
    _validate_columns(result.outsource, "外委更新金额", OUTSOURCE_REQUIRED, result.errors)
    _validate_columns(result.people, "人员关系表", PEOPLE_REQUIRED, result.errors)
    _validate_values(result)
    return result


def _find_sheet(
    xls: pd.ExcelFile,
    aliases: tuple[str, ...],
    discovery_columns: tuple[str, ...] = (),
) -> str | None:
    for alias in aliases:
        if alias in xls.sheet_names:
            return alias
    if discovery_columns:
        for sheet in xls.sheet_names:
            sample = pd.read_excel(xls, sheet_name=sheet, nrows=2)
            if all(column in sample.columns for column in discovery_columns):
                return sheet
    return None


def _read_or_error(
    xls: pd.ExcelFile,
    sheet: str | None,
    label: str,
    aliases: tuple[str, ...],
    result: Personnel3Inputs,
) -> pd.DataFrame:
    if sheet is None:
        result.errors.append(f"缺少{label}，应提供工作表：{' 或 '.join(aliases)}。")
        return pd.DataFrame()
    return pd.read_excel(xls, sheet_name=sheet)


def _validate_columns(df: pd.DataFrame, label: str, required: list[str], errors: list[str]) -> None:
    if df.empty and not len(df.columns):
        return
    missing = [column for column in required if column not in df.columns]
    if missing:
        errors.append(f"{label}缺少字段：{', '.join(missing)}。字段位置可变，但名称不能变化。")


def _validate_values(result: Personnel3Inputs) -> None:
    implementation = result.implementation
    if "项目管理编号" in implementation:
        ids = implementation["项目管理编号"].dropna().astype(str).str.strip()
        ids = ids[ids.ne("")]
        duplicated = sorted(ids[ids.duplicated(keep=False)].unique())
        if duplicated:
            result.errors.append(f"实施进度表存在重复项目管理编号：{', '.join(duplicated)}。")
        missing = int(implementation["项目管理编号"].isna().sum())
        if missing:
            result.warnings.append(f"实施进度表有 {missing} 行未填项目管理编号，将使用Excel行号生成临时编号。")

    _warn_unparseable(
        implementation,
        ["C-中标/合同金额", "预估项目金额", "B-服务采购比例", "1/1进度"],
        "实施进度表",
        result.warnings,
    )
    _warn_unparseable(
        result.outsource,
        ["服务采购金额（元）"],
        "外委更新金额",
        result.warnings,
    )

    people = result.people
    if "人员 3" in people:
        names = people["人员 3"].dropna().astype(str).str.strip()
        duplicate_count = int(names.duplicated().sum())
        if duplicate_count:
            result.warnings.append(f"人员关系表的人员 3 有 {duplicate_count} 条重复记录，统计人数时将去重。")


def _warn_unparseable(
    df: pd.DataFrame,
    columns: list[str],
    label: str,
    warnings: list[str],
) -> None:
    for column in columns:
        if column not in df:
            continue
        raw = df[column]
        text = raw.astype(str).str.strip()
        parsed = coerce_number_series(raw, allow_percent=True)
        invalid = raw.notna() & text.ne("") & parsed.isna()
        if invalid.any():
            warnings.append(f"{label}字段“{column}”有 {int(invalid.sum())} 个值无法解析为数字。")


def coerce_number_series(series: pd.Series, *, allow_percent: bool = False) -> pd.Series:
    """Parse numbers while rejecting comma-separated lists disguised as amounts."""
    text = series.astype(str).str.strip().str.replace("，", ",", regex=False)
    percent = text.str.endswith("%") if allow_percent else pd.Series(False, index=series.index)
    numeric_text = text.str.rstrip("%") if allow_percent else text
    plain = numeric_text.str.match(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$", na=False)
    thousands = numeric_text.str.match(
        r"^[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?$",
        na=False,
    )
    valid = plain | thousands
    parsed = pd.to_numeric(
        numeric_text.where(valid).str.replace(",", "", regex=False),
        errors="coerce",
    )
    if allow_percent:
        parsed = parsed.where(~percent, parsed / 100)
    return parsed.replace([float("inf"), float("-inf")], pd.NA).astype("float64")
