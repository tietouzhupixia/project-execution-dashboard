from __future__ import annotations

import io
import math

import numpy as np
import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .personnel3_loader import Personnel3Inputs
from .personnel3_outputs import Personnel3Outputs


BLUE = "1F4E78"
ORANGE = "C65911"
YELLOW = "FFF2CC"
WHITE = "FFFFFF"
MONEY_FORMAT = '#,##0.00'
PERCENT_FORMAT = '0.00%'

VALUE_SHEETS = [
    "output_人均净合同额表",
    "output_公司层面",
    "output_部门层面",
    "output_人员层面",
    "output_异常检查",
    "calculation_外委子项目匹配",
    "calculation_项目净额明细",
    "calculation_人员分摊明细",
    "calculation_人员3名单",
    "calculation_核验",
    "input_实施进度表",
    "input_外委更新金额",
    "input_人员关系表",
]


def build_personnel3_value_workbook(
    inputs: Personnel3Inputs,
    matches: pd.DataFrame,
    project_detail: pd.DataFrame,
    outputs: Personnel3Outputs,
) -> bytes:
    """Export the current confirmed personnel-3 result as auditable values."""
    frames = _frames(inputs, matches, project_detail, outputs)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet in VALUE_SHEETS:
            frames[sheet].to_excel(writer, sheet_name=sheet, index=False)
    workbook = load_workbook(io.BytesIO(buffer.getvalue()))
    for worksheet in workbook.worksheets:
        _style_sheet(worksheet, set())
    return _save(workbook)


def build_personnel3_formula_workbook(
    inputs: Personnel3Inputs,
    matches: pd.DataFrame,
    project_detail: pd.DataFrame,
    outputs: Personnel3Outputs,
) -> bytes:
    """Export live formulas over the three input tables and confirmed match decisions."""
    frames = _frames(inputs, matches, project_detail, outputs)
    workbook = Workbook()
    workbook.remove(workbook.active)
    formula_columns: dict[str, set[str]] = {}

    for sheet in VALUE_SHEETS:
        frame = frames[sheet]
        worksheet = workbook.create_sheet(sheet)
        _append_frame(worksheet, frame)

    formula_columns["calculation_外委子项目匹配"] = _write_match_formulas(
        workbook["calculation_外委子项目匹配"]
    )
    formula_columns["calculation_项目净额明细"] = _write_project_formulas(
        workbook["calculation_项目净额明细"],
        workbook["calculation_外委子项目匹配"],
    )
    formula_columns["calculation_人员分摊明细"] = _write_allocation_formulas(
        workbook["calculation_人员分摊明细"],
        workbook["calculation_项目净额明细"],
    )
    formula_columns["output_公司层面"] = _write_company_formulas(
        workbook["output_公司层面"],
        workbook["calculation_项目净额明细"],
        workbook["calculation_人员3名单"],
    )
    formula_columns["output_部门层面"] = _write_department_formulas(
        workbook["output_部门层面"],
        workbook["calculation_项目净额明细"],
        workbook["calculation_人员3名单"],
    )
    formula_columns["output_人员层面"] = _write_person_formulas(
        workbook["output_人员层面"],
        workbook["calculation_人员分摊明细"],
    )
    formula_columns["output_人均净合同额表"] = _write_summary_formulas(
        workbook["output_人均净合同额表"], workbook["output_公司层面"]
    )
    formula_columns["calculation_核验"] = _write_check_formulas(
        workbook["calculation_核验"],
        workbook["output_公司层面"],
        workbook["output_部门层面"],
        workbook["calculation_人员分摊明细"],
        workbook["calculation_外委子项目匹配"],
    )

    for worksheet in workbook.worksheets:
        _style_sheet(worksheet, formula_columns.get(worksheet.title, set()))
    workbook.calculation.fullCalcOnLoad = True
    workbook.calculation.forceFullCalc = True
    workbook.calculation.calcMode = "auto"
    return _save(workbook)


def _frames(
    inputs: Personnel3Inputs,
    matches: pd.DataFrame,
    project_detail: pd.DataFrame,
    outputs: Personnel3Outputs,
) -> dict[str, pd.DataFrame]:
    return {
        "output_人均净合同额表": outputs.summary.copy(),
        "output_公司层面": outputs.company.copy(),
        "output_部门层面": outputs.department.copy(),
        "output_人员层面": outputs.person.copy(),
        "output_异常检查": outputs.exceptions.copy(),
        "calculation_外委子项目匹配": matches.copy(),
        "calculation_项目净额明细": project_detail.copy(),
        "calculation_人员分摊明细": outputs.allocation.copy(),
        "calculation_人员3名单": outputs.personnel3_list.copy(),
        "calculation_核验": outputs.checks.copy(),
        "input_实施进度表": inputs.implementation.copy(),
        "input_外委更新金额": inputs.outsource.copy(),
        "input_人员关系表": inputs.people.copy(),
    }


def _append_frame(worksheet, frame: pd.DataFrame) -> None:
    worksheet.append(list(frame.columns))
    for row in frame.itertuples(index=False, name=None):
        worksheet.append([_clean(value) for value in row])


def _write_match_formulas(worksheet) -> set[str]:
    columns = _columns(worksheet)
    for row in range(2, worksheet.max_row + 1):
        status = _cell(columns, "匹配状态", row)
        project = _cell(columns, "对应实施项目编号", row)
        amount = _cell(columns, "服务采购金额", row)
        worksheet[_cell(columns, "是否自动采信", row)] = f'=AND({status}="已匹配",{project}<>"")'
        worksheet[_cell(columns, "纳入采信金额", row)] = (
            f'=IF(AND({status}="已匹配",{project}<>""),{amount},0)'
        )
    return {"是否自动采信", "纳入采信金额"}


def _write_project_formulas(worksheet, match_sheet) -> set[str]:
    c = _columns(worksheet)
    m = _columns(match_sheet)
    match_last = max(match_sheet.max_row, 2)
    match_id = _range(match_sheet.title, m["对应实施项目编号"], 2, match_last)
    match_amount = _range(match_sheet.title, m["纳入采信金额"], 2, match_last)
    formula_columns = {
        "净额取数基数", "外委子项目采信金额", "最终采信服务采购金额", "采信依据",
        "项目净执行合同额", "26/12/31预计进度", "年度进度差", "26年净执行合同额",
        "是否纳入口径", "纳入口径26年净执行合同额",
    }
    for row in range(2, worksheet.max_row + 1):
        project_id = _cell(c, "项目管理编号", row)
        contract = _cell(c, "中标/合同金额", row)
        estimate = _cell(c, "预计项目金额", row)
        ratio = _cell(c, "原服务采购比例", row)
        start = _cell(c, "开始执行日期", row)
        end = _cell(c, "预计验收日期", row)
        opening = _cell(c, "1/1进度", row)
        base = _cell(c, "净额取数基数", row)
        matched = _cell(c, "外委子项目采信金额", row)
        accepted = _cell(c, "最终采信服务采购金额", row)
        net = _cell(c, "项目净执行合同额", row)
        expected = _cell(c, "26/12/31预计进度", row)
        delta = _cell(c, "年度进度差", row)
        annual = _cell(c, "26年净执行合同额", row)
        region = _cell(c, "项目经理区域_原始", row)
        included = _cell(c, "是否纳入口径", row)
        worksheet[base] = f'=IF(OR({contract}="",{contract}=0),IFERROR({estimate},0),{contract})'
        worksheet[matched] = f'=SUMIF({match_id},{project_id},{match_amount})'
        worksheet[accepted] = f'=IF({base}=0,0,IF({matched}>0,{matched},{ratio}*{base}))'
        worksheet[_cell(c, "采信依据", row)] = (
            f'=IF({base}=0,"项目金额缺失，待补",IF({matched}>0,"已匹配外委子项目合计",'
            f'"原服务采购比例×净额取数基数"))'
        )
        worksheet[net] = f'={base}-{accepted}'
        worksheet[expected] = (
            f'=IF(OR({start}="",{end}=""),1,IF({start}>DATE(2026,12,31),0,'
            f'IF({end}<=DATE(2026,12,31),1,MAX(0,MIN(1,(DATE(2026,12,31)-{start})/({end}-{start}))))))'
        )
        worksheet[delta] = f'=MAX(0,{expected}-{opening})'
        worksheet[annual] = f'={net}*{delta}'
        worksheet[included] = (
            f'=IF(OR(ISNUMBER(SEARCH("绿链",{region})),ISNUMBER(SEARCH("数字化市场团队",{region}))),"否","是")'
        )
        worksheet[_cell(c, "纳入口径26年净执行合同额", row)] = f'=IF({included}="是",{annual},0)'
    return formula_columns


def _write_allocation_formulas(worksheet, project_sheet) -> set[str]:
    c = _columns(worksheet)
    p = _columns(project_sheet)
    project_last = max(project_sheet.max_row, 2)
    project_ids = _range(project_sheet.title, p["项目管理编号"], 2, project_last)
    project_amounts = _range(project_sheet.title, p["纳入口径26年净执行合同额"], 2, project_last)
    for row in range(2, worksheet.max_row + 1):
        project_id = _cell(c, "项目管理编号", row)
        amount = _cell(c, "项目26年净执行合同额", row)
        ratio = _cell(c, "执行比例", row)
        worksheet[amount] = f'=SUMIF({project_ids},{project_id},{project_amounts})'
        worksheet[_cell(c, "分摊26年净执行合同额", row)] = f'={amount}*{ratio}'
    return {"项目26年净执行合同额", "分摊26年净执行合同额"}


def _write_company_formulas(worksheet, project_sheet, people_sheet) -> set[str]:
    c, p = _columns(worksheet), _columns(project_sheet)
    project_last = max(project_sheet.max_row, 2)
    amounts = _range(project_sheet.title, p["纳入口径26年净执行合同额"], 2, project_last)
    included = _range(project_sheet.title, p["是否纳入口径"], 2, project_last)
    row = 2
    amount = _cell(c, "26年净执行合同额", row)
    people = _cell(c, "有效执行人数（人员3）", row)
    worksheet[amount] = f'=SUM({amounts})'
    worksheet[people] = f'=COUNTA(\'{people_sheet.title}\'!$A$2:$A${max(people_sheet.max_row, 2)})'
    worksheet[_cell(c, "人均净合同额", row)] = f'=IFERROR({amount}/{people},0)'
    worksheet[_cell(c, "项目数", row)] = f'=COUNTIF({included},"是")'
    return {"26年净执行合同额", "有效执行人数（人员3）", "人均净合同额", "项目数"}


def _write_department_formulas(worksheet, project_sheet, people_sheet) -> set[str]:
    c, p, pe = _columns(worksheet), _columns(project_sheet), _columns(people_sheet)
    project_last, people_last = max(project_sheet.max_row, 2), max(people_sheet.max_row, 2)
    departments = _range(project_sheet.title, p["项目净额归属部门"], 2, project_last)
    amounts = _range(project_sheet.title, p["纳入口径26年净执行合同额"], 2, project_last)
    included = _range(project_sheet.title, p["是否纳入口径"], 2, project_last)
    people_departments = _range(people_sheet.title, pe["所属区域3"], 2, people_last)
    for row in range(2, worksheet.max_row + 1):
        department = _cell(c, "部门", row)
        amount = _cell(c, "26年净执行合同额", row)
        people = _cell(c, "有效执行人数（人员3）", row)
        worksheet[amount] = f'=SUMIF({departments},{department},{amounts})'
        worksheet[people] = f'=COUNTIF({people_departments},{department})'
        worksheet[_cell(c, "人均净合同额", row)] = f'=IFERROR({amount}/{people},0)'
        worksheet[_cell(c, "项目数", row)] = f'=COUNTIFS({departments},{department},{included},"是")'
    return {"26年净执行合同额", "有效执行人数（人员3）", "人均净合同额", "项目数"}


def _write_person_formulas(worksheet, allocation_sheet) -> set[str]:
    c, a = _columns(worksheet), _columns(allocation_sheet)
    last = max(allocation_sheet.max_row, 2)
    people = _range(allocation_sheet.title, a["执行人员"], 2, last)
    scope = _range(allocation_sheet.title, a["是否人员3范围"], 2, last)
    amounts = _range(allocation_sheet.title, a["分摊26年净执行合同额"], 2, last)
    for row in range(2, worksheet.max_row + 1):
        person = _cell(c, "人员3", row)
        amount = _cell(c, "26年净执行合同额", row)
        count = _cell(c, "参与分摊项目数", row)
        worksheet[amount] = f'=SUMIFS({amounts},{people},{person},{scope},"是")'
        worksheet[count] = f'=COUNTIFS({people},{person},{scope},"是")'
        worksheet[_cell(c, "已填比例项目平均净额", row)] = f'=IFERROR({amount}/{count},0)'
        worksheet[_cell(c, "说明", row)] = f'=IF({count}>0,"仅汇总已填执行比例","未填报分摊比例或未参与")'
    return {"26年净执行合同额", "参与分摊项目数", "已填比例项目平均净额", "说明"}


def _write_summary_formulas(worksheet, company_sheet) -> set[str]:
    c, company = _columns(worksheet), _columns(company_sheet)
    mapping = {
        "项目数": "项目数",
        "有效执行人数（人员3）": "有效执行人数（人员3）",
        "公司26年净执行合同额": "26年净执行合同额",
        "公司人均净合同额": "人均净合同额",
    }
    for row in range(2, worksheet.max_row + 1):
        metric = worksheet[_cell(c, "指标", row)].value
        source = mapping.get(str(metric))
        if source:
            worksheet[_cell(c, "值", row)] = f"='{company_sheet.title}'!{_cell(company, source, 2)}"
    return {"值"}


def _write_check_formulas(worksheet, company_sheet, department_sheet, allocation_sheet, match_sheet) -> set[str]:
    c = _columns(worksheet)
    company, department = _columns(company_sheet), _columns(department_sheet)
    allocation, match = _columns(allocation_sheet), _columns(match_sheet)
    company_amount = f"'{company_sheet.title}'!{_cell(company, '26年净执行合同额', 2)}"
    company_people = f"'{company_sheet.title}'!{_cell(company, '有效执行人数（人员3）', 2)}"
    department_amounts = _range(department_sheet.title, department["26年净执行合同额"], 2, max(department_sheet.max_row, 2))
    allocation_amounts = _range(allocation_sheet.title, allocation["分摊26年净执行合同额"], 2, max(allocation_sheet.max_row, 2))
    match_status = _range(match_sheet.title, match["匹配状态"], 2, max(match_sheet.max_row, 2))
    match_amounts = _range(match_sheet.title, match["纳入采信金额"], 2, max(match_sheet.max_row, 2))
    for row in range(2, worksheet.max_row + 1):
        name = str(worksheet[_cell(c, "检查项", row)].value)
        calc = _cell(c, "计算值", row)
        compare = _cell(c, "对照值", row)
        status = _cell(c, "差异/状态", row)
        if name == "公司金额与部门合计一致":
            worksheet[calc] = f'={company_amount}'
            worksheet[compare] = f'=SUM({department_amounts})'
            worksheet[status] = f'={calc}-{compare}'
        elif name == "人员3有效人数":
            worksheet[calc] = f'={company_people}'
            worksheet[status] = f'=IF({calc}={compare},"通过","需核对")'
        elif name == "外委子项目自动采信金额":
            worksheet[calc] = f'=SUMIF({match_status},"已匹配",{match_amounts})'
        elif name == "个人分摊覆盖率":
            worksheet[calc] = f'=IFERROR(SUM({allocation_amounts})/{company_amount},0)'
            worksheet[status] = f'=IF(ABS({calc}-1)<0.000000001,"覆盖完整","未覆盖金额已在个人层面排除")'
    return {"计算值", "对照值", "差异/状态"}


def _style_sheet(worksheet, formula_columns: set[str]) -> None:
    headers = {cell.value: cell.column for cell in worksheet[1]}
    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions
    for cell in worksheet[1]:
        color = ORANGE if cell.value in formula_columns else BLUE
        cell.fill = PatternFill("solid", fgColor=color)
        cell.font = Font(color=WHITE, bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center")
    for name in formula_columns:
        column = headers.get(name)
        if column:
            for row in range(2, worksheet.max_row + 1):
                worksheet.cell(row=row, column=column).fill = PatternFill("solid", fgColor=YELLOW)
    for column_cells in worksheet.columns:
        values = [str(cell.value) for cell in column_cells if cell.value is not None]
        width = min(max([len(value) for value in values] + [8]) + 2, 42)
        worksheet.column_dimensions[get_column_letter(column_cells[0].column)].width = width
    for name, column in headers.items():
        number_format = _number_format(str(name))
        if number_format:
            for row in range(2, worksheet.max_row + 1):
                worksheet.cell(row=row, column=column).number_format = number_format


def _number_format(name: str) -> str | None:
    if "比例" in name or "进度" in name or "匹配度" in name or "覆盖率" in name:
        return PERCENT_FORMAT
    if "金额" in name or "净额" in name or name in {"计算值", "对照值", "差异/状态", "值"}:
        return MONEY_FORMAT
    return None


def _columns(worksheet) -> dict[str, int]:
    return {str(cell.value): cell.column for cell in worksheet[1] if cell.value is not None}


def _cell(columns: dict[str, int], name: str, row: int) -> str:
    return f"{get_column_letter(columns[name])}{row}"


def _range(sheet: str, column: int, first: int, last: int) -> str:
    letter = get_column_letter(column)
    return f"'{sheet}'!${letter}${first}:${letter}${last}"


def _clean(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def _save(workbook: Workbook) -> bytes:
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
