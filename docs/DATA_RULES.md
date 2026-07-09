# Data Rules

This document defines how uploaded raw data should be read and transformed.

## 1. Input Sheets

Primary sheet:

- `实施进度底表`

Optional sheets:

- `人员关系表`
- `人效基础数据`

If the exact sheet name is absent, the app should scan all sheets and choose the first sheet containing these required columns:

- `A-项目名称`
- `当前进度`
- `交付状态`

## 2. Core Columns

Required for basic dashboard:

- `A-项目名称`
- `A-项目经理区域`
- `A-执行人员`
- `执行项目类型`
- `收入`
- `当前进度`
- `进度分类`
- `进度偏差`
- `进度偏差分类`
- `时间进度`
- `交付状态`
- `预计交付日期`
- `预计验收日期（若已签约，默认经法）`

Required for archive analysis:

- `当前进度`
- `启动归档`
- `中期归档`
- `临近终期归档`

Required for efficiency analysis:

- `收入`
- `B-服务采购比例`
- `执行人员1`
- `执行人员1执行比例`
- `执行人员2`
- `执行人员2执行比例`
- `执行人员3`
- `执行人员3执行比例`
- `执行人员4`
- `执行人员4执行比例`
- `执行人员5`
- `执行人员5执行比例`

If `执行人员1-5` and ratios are blank, derive virtual values from `A-执行人员`.

## 3. Virtual Execution Ratio Rule

If execution ratios are not manually provided:

1. Split `A-执行人员` by comma, supporting both `,` and `，`.
2. Fill `执行人员1-5` in order.
3. Equal-split ratio by participant count.
4. Mark the ratio as virtual in UI and export notes.

Example:

`季慧颖,许浩然,安稳飞,童瑶`

becomes:

- `执行人员1 = 季慧颖`, ratio `25%`
- `执行人员2 = 许浩然`, ratio `25%`
- `执行人员3 = 安稳飞`, ratio `25%`
- `执行人员4 = 童瑶`, ratio `25%`

Important: this is a placeholder only. Business-confirmed ratios override virtual ratios.

## 4. Efficiency Formula

Person net execution contract amount:

```text
person_net = SUM(project_income * (1 - outsourcing_ratio) * person_execution_ratio)
```

Column mapping:

- `project_income`: `收入`
- `outsourcing_ratio`: `B-服务采购比例`
- `person_execution_ratio`: `执行人员N执行比例`

If outsourcing ratio is blank, current fallback is `0`.

## 5. Archive View 1: Project-Stage Progressive Compliance

This is a project-level metric. Each project counts once in its current stage.

Denominator:

- Start stage: `10% <= 当前进度 < 50%`
- Middle stage: `50% <= 当前进度 < 90%`
- Final stage: `当前进度 >= 90%`
- Overall: all projects with `当前进度 >= 10%`

Numerator:

- Start stage: denominator projects with `启动归档 = 是`
- Middle stage: denominator projects with `启动归档 = 是` and `中期归档 = 是`
- Final stage: denominator projects with `启动归档 = 是`, `中期归档 = 是`, and `临近终期归档 = 是`
- Overall: sum of the three stage numerators

Rate:

```text
stage_rate = numerator / denominator
overall_rate = total_numerator / total_denominator
```

## 6. Archive View 2: Archive-Node Completion

This is an archive-action metric. Each archive node is assessed independently.

Denominator:

- Start archive node: projects with `当前进度 >= 10%`
- Middle archive node: projects with `当前进度 >= 50%`
- Final archive node: projects with `当前进度 >= 90%`

Numerator:

- Start archive node: denominator projects with `启动归档 = 是`
- Middle archive node: denominator projects with `中期归档 = 是`
- Final archive node: denominator projects with `临近终期归档 = 是`

Rate:

```text
node_rate = node_numerator / node_denominator
overall_node_rate = sum(node_numerators) / sum(node_denominators)
```

## 7. Date Rules

If actual delivery and actual acceptance dates are absent:

- Use `预计交付日期` for estimated delivery month.
- Use `预计验收日期（若已签约，默认经法）` for estimated acceptance month.
- Label charts as estimated, not actual.

## 8. Business Unit Rules

Preferred business-unit mapping:

1. `人员关系表`: person to `所属区域`.
2. If no relation sheet: infer from project region `A-项目经理区域`.
3. If multiple regions exist, split by comma and mark as multi-region.
4. If still unknown, mark as `未匹配`.

## 9. Single-Sheet Uploads (2026-07-08 requirement update)

Uploaded raw files may contain **only** `实施进度底表`. All analysis output must be
computed by the app from that sheet alone:

- The three analysis sheets (`进度信息分析`, `人效基础数据`, `人效分析`) are **never read**
  from the upload. The app reproduces their content and renders it on the web page.
- `人员关系表` remains optional. Without it, person area falls back to project-region
  inference (section 8) and the data note must say so.
- Uploaded files may add new columns and may reorder columns. All access is by column
  name; column position must never matter; unknown extra columns are ignored.

## 10. Derived Archive Action Columns

The six action columns may be absent from uploads. The app always recomputes them
(replicating the workbook formulas) and overwrites uploaded values if present:

```text
启动应归档     = 1 if 当前进度 is numeric and >= 0.1 else 0
启动已归档     = 1 if 启动应归档 = 1 and 启动归档 = "是" else 0
中期应归档     = 1 if 当前进度 is numeric and >= 0.5 else 0
中期已归档     = 1 if 中期应归档 = 1 and 中期归档 = "是" else 0
临近中期应归档 = 1 if 当前进度 is numeric and >= 0.9 else 0
临近中期已归档 = 1 if 临近中期应归档 = 1 and 临近终期归档 = "是" else 0
```

If the source columns `启动归档`/`中期归档`/`临近终期归档` are missing, the
"已归档" columns are 0 and a warning is shown.

## 11. 进度信息分析 Replication (project/acceptance summary)

Three summary blocks, replicating the sheet's left-side formulas:

- 项目数 by 业务单元: `公司整体` = row count with non-blank `A-项目名称`; per unit =
  rows whose comma-split `A-项目经理区域` contains the unit.
- 未验收 by 业务单元: same, additionally `交付状态` contains `未验收`.
- 已验收 by 业务单元: same, additionally `交付状态` contains `已验收`.

Business units are derived **dynamically** from the data (comma-split of
`A-项目经理区域`, first-seen order), never hardcoded.

## 12. 人效基础数据 Replication (person base table + data note)

Columns: `人员`, `净执行合同额`, `所属区域/业务单元`, `数据说明`.

数据说明 rules:

- Person found in `人员关系表` and has net amount > 0: `人员关系表匹配/当前有执行数据`
- Person found in `人员关系表` and net amount = 0: `人员关系表匹配/当前无执行数据`
- Person appears in execution data but not in `人员关系表`: `执行名单补充-临时归属待确认`
- No `人员关系表` uploaded at all: `无人员关系表-区域按项目推断`

