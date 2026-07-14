"""Recalculate the 0713 sample from its input sheets and compare cached outputs."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.personnel3_loader import load_personnel3_inputs
from src.personnel3_metrics import MATCHED, build_project_net_detail, match_outsource_projects
from src.personnel3_outputs import build_personnel3_outputs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    args = parser.parse_args()

    inputs = load_personnel3_inputs(args.workbook)
    if not inputs.ready:
        print("Input validation failed:")
        for error in inputs.errors:
            print(f"- {error}")
        return 1

    historical_matches = pd.read_excel(args.workbook, sheet_name="calculation_外委子项目匹配")
    confirmations = historical_matches.loc[
        historical_matches["匹配状态"].eq(MATCHED),
        ["外委序号", "匹配状态", "对应实施项目编号"],
    ]
    matches = match_outsource_projects(inputs.implementation, inputs.outsource, confirmations)
    actual = build_project_net_detail(inputs.implementation, matches)
    outputs = build_personnel3_outputs(
        inputs.implementation,
        inputs.people,
        matches,
        actual,
    )
    expected = pd.read_excel(args.workbook, sheet_name="calculation_项目净额明细")
    expected["项目管理编号"] = expected["项目管理编号"].map(
        lambda value: "" if pd.isna(value) else str(int(value)) if isinstance(value, float) and value.is_integer() else str(value).strip()
    )
    missing = expected["项目管理编号"].eq("")
    expected.loc[missing, "项目管理编号"] = [
        f"未填项目编号_行{position}"
        for position in expected.index[missing] + 2
    ]

    print(f"Workbook: {args.workbook}")
    print(f"Match states: {matches['匹配状态'].value_counts().to_dict()}")
    expected_states = historical_matches[["外委序号", "匹配状态", "最高匹配度"]].copy()
    expected_states["外委序号"] = expected_states["外委序号"].map(
        lambda value: str(int(value)) if isinstance(value, float) and value.is_integer() else str(value).strip()
    )
    expected_states["预期三状态"] = expected_states.apply(
        lambda row: MATCHED
        if row["匹配状态"] == MATCHED
        else "需人工确认"
        if float(row["最高匹配度"] or 0) >= 0.45
        else "未匹配",
        axis=1,
    )
    state_check = matches.merge(expected_states[["外委序号", "预期三状态"]], on="外委序号", how="left")
    state_difference = state_check["匹配状态"].ne(state_check["预期三状态"])
    print(f"Match-state differences: {int(state_difference.sum())}")
    if state_difference.any():
        print(
            state_check.loc[
                state_difference,
                ["外委序号", "外委项目名称", "匹配状态", "预期三状态", "最高匹配度"],
            ].to_string(index=False)
        )
    failed = False
    for column in ["项目净执行合同额", "26年净执行合同额", "纳入口径26年净执行合同额"]:
        actual_total = pd.to_numeric(actual[column], errors="coerce").fillna(0).sum()
        expected_total = pd.to_numeric(expected[column], errors="coerce").fillna(0).sum()
        difference = actual_total - expected_total
        print(f"{column}: actual={actual_total:.6f}, expected={expected_total:.6f}, diff={difference:.6f}")
        failed |= abs(difference) > 0.01

    comparison = actual.merge(
        expected[["项目管理编号", "纳入口径26年净执行合同额"]],
        on="项目管理编号",
        how="outer",
        suffixes=("_actual", "_expected"),
    )
    project_difference = (
        pd.to_numeric(comparison["纳入口径26年净执行合同额_actual"], errors="coerce").fillna(0)
        - pd.to_numeric(comparison["纳入口径26年净执行合同额_expected"], errors="coerce").fillna(0)
    ).abs()
    print(f"Max project difference: {project_difference.max():.6f}")
    print(f"Projects different by >0.01: {int(project_difference.gt(0.01).sum())}")
    if project_difference.gt(0.01).any():
        columns = [
            "项目管理编号",
            "项目名称",
            "纳入口径26年净执行合同额_actual",
            "纳入口径26年净执行合同额_expected",
        ]
        print(comparison.loc[project_difference.gt(0.01), columns].to_string(index=False))

    expected_people = pd.read_excel(args.workbook, sheet_name="calculation_人员3名单")
    actual_people = outputs.personnel3_list.reset_index(drop=True).fillna("").astype(str)
    expected_people = expected_people.reset_index(drop=True).fillna("").astype(str)
    people_equal = actual_people.equals(expected_people)
    print(f"Personnel-3 list equal: {people_equal} ({len(outputs.personnel3_list)} rows)")
    if not people_equal:
        print(pd.concat({"actual": actual_people, "expected": expected_people}, axis=1).to_string(index=False))
    failed |= not people_equal

    expected_allocation = pd.read_excel(args.workbook, sheet_name="calculation_人员分摊明细")
    expected_allocation["项目管理编号"] = expected_allocation["项目管理编号"].map(
        lambda value: "" if pd.isna(value) else str(int(value)) if isinstance(value, float) and value.is_integer() else str(value).strip()
    )
    actual_allocation = outputs.allocation.iloc[:, :6].reset_index(drop=True).copy()
    expected_allocation = expected_allocation.iloc[:, :6].reset_index(drop=True)
    allocation_equal = len(actual_allocation) == len(expected_allocation)
    if allocation_equal:
        for column in actual_allocation.columns:
            if column == "执行比例":
                allocation_equal &= (
                    pd.to_numeric(actual_allocation[column], errors="coerce").fillna(0)
                    - pd.to_numeric(expected_allocation[column], errors="coerce").fillna(0)
                ).abs().le(1e-12).all()
            else:
                allocation_equal &= actual_allocation[column].fillna("").astype(str).equals(
                    expected_allocation[column].fillna("").astype(str)
                )
    print(f"Allocation business fields equal: {allocation_equal} ({len(actual_allocation)} rows)")
    failed |= not allocation_equal

    expected_company = pd.read_excel(args.workbook, sheet_name="output_公司层面")
    expected_department = pd.read_excel(args.workbook, sheet_name="output_部门层面")
    for label, current, cached, key in [
        ("Company", outputs.company, expected_company, "层级"),
        ("Department", outputs.department, expected_department, "部门"),
    ]:
        joined = current.merge(cached, on=key, suffixes=("_actual", "_expected"))
        numeric_columns = ["26年净执行合同额", "有效执行人数（人员3）", "人均净合同额", "项目数"]
        maximum = max(
            (
                pd.to_numeric(joined[f"{column}_actual"], errors="coerce").fillna(0)
                - pd.to_numeric(joined[f"{column}_expected"], errors="coerce").fillna(0)
            ).abs().max()
            for column in numeric_columns
        )
        print(f"{label} output max difference: {maximum:.6f}")
        failed |= maximum > 0.01 or len(joined) != len(current) or len(joined) != len(cached)

    exception_counts = outputs.exceptions["异常类型"].value_counts().to_dict()
    coverage = outputs.checks.loc[
        outputs.checks["检查项"].eq("个人分摊覆盖率"), "计算值"
    ].iloc[0]
    person_amount = outputs.person["26年净执行合同额"].sum()
    print(f"Exception counts: {exception_counts}")
    print(f"Personnel-3 allocated amount: {person_amount:.6f}")
    print(f"All filled-ratio coverage: {coverage:.6%}")

    expected_person = pd.read_excel(args.workbook, sheet_name="output_人员层面")
    expected_person_amount = pd.to_numeric(expected_person["26年净执行合同额"], errors="coerce").fillna(0).sum()
    if expected_person_amount == 0 and person_amount != 0:
        print("Person output comparison: skipped (source workbook formulas evaluate to 0; project IDs use mixed text/number types)")
    else:
        person_joined = outputs.person.merge(expected_person, on=["人员3", "所属区域3"], suffixes=("_actual", "_expected"))
        person_maximum = max(
            (
                pd.to_numeric(person_joined[f"{column}_actual"], errors="coerce").fillna(0)
                - pd.to_numeric(person_joined[f"{column}_expected"], errors="coerce").fillna(0)
            ).abs().max()
            for column in ["26年净执行合同额", "参与分摊项目数", "已填比例项目平均净额"]
        )
        print(f"Person output max difference: {person_maximum:.6f}")
        failed |= person_maximum > 0.01 or len(person_joined) != len(outputs.person)
    return 1 if failed or project_difference.gt(0.01).any() else 0


if __name__ == "__main__":
    raise SystemExit(main())
