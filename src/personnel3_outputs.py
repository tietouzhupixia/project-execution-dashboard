from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .personnel3_loader import coerce_number_series
from .personnel3_metrics import MATCHED, NEEDS_CONFIRMATION, UNMATCHED


@dataclass
class Personnel3Outputs:
    personnel3_list: pd.DataFrame
    allocation: pd.DataFrame
    company: pd.DataFrame
    department: pd.DataFrame
    person: pd.DataFrame
    exceptions: pd.DataFrame
    checks: pd.DataFrame
    summary: pd.DataFrame


def personnel3_department_projects(project_detail: pd.DataFrame, department: str) -> pd.DataFrame:
    return project_detail.loc[
        project_detail["项目净额归属部门"].eq(department)
        & project_detail["是否纳入口径"].eq("是")
    ].copy()


def personnel3_department_people(personnel3_list: pd.DataFrame, department: str) -> pd.DataFrame:
    return personnel3_list.loc[personnel3_list["所属区域3"].eq(department)].copy()


def personnel3_person_allocations(allocation: pd.DataFrame, person: str) -> pd.DataFrame:
    return allocation.loc[
        allocation["执行人员"].eq(person) & allocation["是否人员3范围"].eq("是")
    ].copy()


def personnel3_project_rows(project_detail: pd.DataFrame, project_id: str) -> pd.DataFrame:
    return project_detail.loc[project_detail["项目管理编号"].astype(str).eq(str(project_id))].copy()


def personnel3_project_allocations(allocation: pd.DataFrame, project_id: str) -> pd.DataFrame:
    return allocation.loc[allocation["项目管理编号"].astype(str).eq(str(project_id))].copy()


def personnel3_project_outsource(outsource_matches: pd.DataFrame, project_id: str) -> pd.DataFrame:
    return outsource_matches.loc[
        outsource_matches["对应实施项目编号"].astype(str).eq(str(project_id))
    ].copy()


def personnel3_exceptions_of_type(exceptions: pd.DataFrame, exception_type: str) -> pd.DataFrame:
    return exceptions.loc[exceptions["异常类型"].eq(exception_type)].copy()


def build_personnel3_outputs(
    implementation: pd.DataFrame,
    people: pd.DataFrame,
    outsource_matches: pd.DataFrame,
    project_detail: pd.DataFrame,
    *,
    expected_people_count: int = 22,
) -> Personnel3Outputs:
    personnel3_list = build_personnel3_list(people)
    allocation = build_person_allocation(implementation, project_detail, personnel3_list)
    company, department, person = build_three_level_outputs(
        project_detail,
        personnel3_list,
        allocation,
    )
    exceptions = build_personnel3_exceptions(
        implementation,
        project_detail,
        personnel3_list,
        outsource_matches,
    )
    checks = build_personnel3_checks(
        company,
        department,
        allocation,
        outsource_matches,
        expected_people_count=expected_people_count,
    )
    summary = pd.DataFrame(
        [
            {"指标": "项目数", "值": int(company.loc[0, "项目数"])},
            {"指标": "有效执行人数（人员3）", "值": int(company.loc[0, "有效执行人数（人员3）"])},
            {"指标": "公司26年净执行合同额", "值": float(company.loc[0, "26年净执行合同额"])},
            {"指标": "公司人均净合同额", "值": float(company.loc[0, "人均净合同额"])},
        ]
    )
    return Personnel3Outputs(
        personnel3_list=personnel3_list,
        allocation=allocation,
        company=company,
        department=department,
        person=person,
        exceptions=exceptions,
        checks=checks,
        summary=summary,
    )


def build_personnel3_list(people: pd.DataFrame) -> pd.DataFrame:
    """Use only 人员 3 and 所属区域 3, preserving the first row per person."""
    if not {"人员 3", "所属区域 3"}.issubset(people.columns):
        return pd.DataFrame(columns=["人员3", "所属区域3"])
    result = people[["人员 3", "所属区域 3"]].rename(
        columns={"人员 3": "人员3", "所属区域 3": "所属区域3"}
    )
    result["人员3"] = result["人员3"].fillna("").astype(str).str.strip()
    result["所属区域3"] = result["所属区域3"].fillna("").astype(str).str.strip()
    return (
        result.loc[result["人员3"].ne("")]
        .drop_duplicates("人员3", keep="first")
        .sort_values("人员3", kind="stable")
        .reset_index(drop=True)
    )


def build_person_allocation(
    implementation: pd.DataFrame,
    project_detail: pd.DataFrame,
    personnel3_list: pd.DataFrame,
) -> pd.DataFrame:
    """Unpivot only explicitly filled person/ratio pairs; never infer equal shares."""
    people_to_department = dict(
        zip(personnel3_list["人员3"], personnel3_list["所属区域3"])
    )
    rows: list[dict] = []
    for position, (_, project) in enumerate(implementation.iterrows()):
        detail = project_detail.iloc[position]
        for slot in range(1, 6):
            person = _clean_text(project.get(f"执行人员{slot}"))
            ratio = _ratio(project.get(f"执行人员{slot}执行比例"))
            if not person or pd.isna(ratio):
                continue
            in_scope = person in people_to_department
            project_amount = _number(detail.get("纳入口径26年净执行合同额"))
            rows.append(
                {
                    "项目管理编号": detail["项目管理编号"],
                    "项目名称": detail["项目名称"],
                    "执行人员": person,
                    "执行比例": float(ratio),
                    "人员3部门": people_to_department.get(person, "人员3范围外"),
                    "是否人员3范围": "是" if in_scope else "否",
                    "项目26年净执行合同额": project_amount,
                    "分摊26年净执行合同额": project_amount * float(ratio),
                }
            )
    return pd.DataFrame(
        rows,
        columns=[
            "项目管理编号",
            "项目名称",
            "执行人员",
            "执行比例",
            "人员3部门",
            "是否人员3范围",
            "项目26年净执行合同额",
            "分摊26年净执行合同额",
        ],
    )


def build_three_level_outputs(
    project_detail: pd.DataFrame,
    personnel3_list: pd.DataFrame,
    allocation: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    included = project_detail["是否纳入口径"].eq("是")
    company_amount = _numeric(project_detail["纳入口径26年净执行合同额"]).sum()
    people_count = len(personnel3_list)
    company = pd.DataFrame(
        [
            {
                "层级": "公司",
                "26年净执行合同额": company_amount,
                "有效执行人数（人员3）": people_count,
                "人均净合同额": company_amount / people_count if people_count else 0.0,
                "项目数": int(included.sum()),
            }
        ]
    )

    departments = sorted(personnel3_list["所属区域3"].loc[personnel3_list["所属区域3"].ne("")].unique())
    department_rows = []
    for department_name in departments:
        project_mask = project_detail["项目净额归属部门"].eq(department_name)
        amount = _numeric(project_detail.loc[project_mask, "纳入口径26年净执行合同额"]).sum()
        department_people = int(personnel3_list["所属区域3"].eq(department_name).sum())
        department_rows.append(
            {
                "部门": department_name,
                "26年净执行合同额": amount,
                "有效执行人数（人员3）": department_people,
                "人均净合同额": amount / department_people if department_people else 0.0,
                "项目数": int((project_mask & included).sum()),
            }
        )
    department = pd.DataFrame(department_rows)

    person_rows = []
    for _, member in personnel3_list.iterrows():
        person_name = member["人员3"]
        rows = allocation.loc[
            allocation["执行人员"].eq(person_name) & allocation["是否人员3范围"].eq("是")
        ]
        amount = _numeric(rows["分摊26年净执行合同额"]).sum()
        participation_count = len(rows)
        person_rows.append(
            {
                "人员3": person_name,
                "所属区域3": member["所属区域3"],
                "26年净执行合同额": amount,
                "参与分摊项目数": participation_count,
                "已填比例项目平均净额": amount / participation_count if participation_count else 0.0,
                "说明": "仅汇总已填执行比例" if participation_count else "未填报分摊比例或未参与",
            }
        )
    person = pd.DataFrame(person_rows)
    return company, department, person


def build_personnel3_exceptions(
    implementation: pd.DataFrame,
    project_detail: pd.DataFrame,
    personnel3_list: pd.DataFrame,
    outsource_matches: pd.DataFrame,
) -> pd.DataFrame:
    """Generate the handoff's auditable exception list from current inputs."""
    rows: list[dict] = []
    people3 = set(personnel3_list["人员3"])

    for position, (_, project) in enumerate(implementation.iterrows()):
        detail = project_detail.iloc[position]
        project_id = detail["项目管理编号"]
        project_name = detail["项目名称"]
        named_people: list[str] = []
        filled_ratios: list[float] = []
        for slot in range(1, 6):
            person = _clean_text(project.get(f"执行人员{slot}"))
            if not person:
                continue
            named_people.append(person)
            ratio = _ratio(project.get(f"执行人员{slot}执行比例"))
            if pd.isna(ratio):
                rows.append(
                    _exception(
                        project_id,
                        project_name,
                        "执行人员未填分摊比例",
                        f"{person} 已填，但执行比例为空；未纳入个人分摊。",
                    )
                )
            else:
                filled_ratios.append(float(ratio))
            if person not in people3:
                rows.append(
                    _exception(
                        project_id,
                        project_name,
                        "分摊人员不在人员3范围",
                        f"{person} 不在人员关系表的人员 3 名单中；不进入个人层面。",
                    )
                )

        if named_people and not filled_ratios:
            rows.append(
                _exception(
                    project_id,
                    project_name,
                    "缺少执行比例",
                    "不使用 A-执行人员平均拆分；项目仅计入公司、部门项目净额。",
                )
            )
        elif filled_ratios and not _close(sum(filled_ratios), 1.0):
            rows.append(
                _exception(
                    project_id,
                    project_name,
                    "执行比例合计异常",
                    f"已填写比例合计为 {sum(filled_ratios):.2%}，个人层面按已填比例计算。",
                )
            )

        original_id = project.get("项目管理编号")
        if pd.isna(original_id) or not str(original_id).strip():
            rows.append(
                _exception(project_id, project_name, "缺少项目管理编号", "已按Excel行号生成临时项目编号。")
            )
        if detail["是否纳入口径"] == "否":
            rows.append(
                _exception(
                    project_id,
                    project_name,
                    "不纳入口径项目",
                    "项目经理区域包含绿链或数字化市场团队，不计入公司、部门、个人金额及项目数。",
                )
            )

    for _, match in outsource_matches.iterrows():
        status = match["匹配状态"]
        if status == MATCHED:
            continue
        score = _number(match.get("最高匹配度"))
        if status == NEEDS_CONFIRMATION:
            rows.append(
                _exception(
                    match.get("对应实施项目编号", ""),
                    match["外委项目名称"],
                    "外委子项目需人工确认",
                    f"最高匹配度 {score:.1%}；本次不自动纳入最终采信服务采购金额。",
                )
            )
        elif status == UNMATCHED:
            rows.append(
                _exception(
                    "",
                    match["外委项目名称"],
                    "外委子项目未匹配",
                    f"最高匹配度 {score:.1%}；本次不自动纳入最终采信服务采购金额。",
                )
            )

    return pd.DataFrame(
        rows,
        columns=["项目管理编号", "项目/外委子项目名称", "异常类型", "说明"],
    )


def build_personnel3_checks(
    company: pd.DataFrame,
    department: pd.DataFrame,
    allocation: pd.DataFrame,
    outsource_matches: pd.DataFrame,
    *,
    expected_people_count: int = 22,
) -> pd.DataFrame:
    company_amount = _number(company.loc[0, "26年净执行合同额"])
    department_amount = _numeric(department.get("26年净执行合同额", pd.Series(dtype=float))).sum()
    people_count = int(company.loc[0, "有效执行人数（人员3）"])
    accepted_outsource = _numeric(
        outsource_matches.loc[outsource_matches["匹配状态"].eq(MATCHED), "纳入采信金额"]
    ).sum()
    allocated = _numeric(allocation.get("分摊26年净执行合同额", pd.Series(dtype=float))).sum()
    coverage = allocated / company_amount if company_amount else 0.0
    return pd.DataFrame(
        [
            {
                "检查项": "公司金额与部门合计一致",
                "计算值": company_amount,
                "对照值": department_amount,
                "差异/状态": company_amount - department_amount,
                "说明": "部门合计应等于公司金额",
            },
            {
                "检查项": "人员3有效人数",
                "计算值": people_count,
                "对照值": expected_people_count,
                "差异/状态": "通过" if people_count == expected_people_count else "需核对",
                "说明": f"人员3去重人数应为{expected_people_count}",
            },
            {
                "检查项": "外委子项目自动采信金额",
                "计算值": accepted_outsource,
                "对照值": "",
                "差异/状态": "已匹配子项目合计",
                "说明": "仅已匹配子项目纳入",
            },
            {
                "检查项": "个人分摊覆盖率",
                "计算值": coverage,
                "对照值": "",
                "差异/状态": "覆盖完整" if _close(coverage, 1.0) else "未覆盖金额已在个人层面排除",
                "说明": "仅作填报完整度提示，不影响公司和部门金额",
            },
        ]
    )


def _exception(project_id: object, name: object, kind: str, note: str) -> dict:
    return {
        "项目管理编号": _clean_text(project_id),
        "项目/外委子项目名称": _clean_text(name),
        "异常类型": kind,
        "说明": note,
    }


def _ratio(value: object) -> float:
    parsed = coerce_number_series(pd.Series([value]), allow_percent=True).iloc[0]
    return float(parsed) if pd.notna(parsed) else float("nan")


def _number(value: object) -> float:
    parsed = coerce_number_series(pd.Series([value]), allow_percent=True).iloc[0]
    return float(parsed) if pd.notna(parsed) else 0.0


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0)


def _clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _close(left: float, right: float, tolerance: float = 1e-9) -> bool:
    return abs(left - right) <= tolerance
