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

## 12. Month/Year Collapsed Distributions (2026-07-09 requirement)

预计验收/预计交付年月分布图的横轴粒度随自然年动态变化：

- 当年（`pd.Timestamp.now().year`）及更早：按 `%y年%m月` 展示。
- 当年之后的年份：合并为整年 `%y年`（如 `27年`、`28年`）。
- 到了下一个自然年自动前移：2027 年时 27 年按月、28 年及以后按年。

## 13. Chart Drill-down

可明确映射回项目的图表直接点击图形下钻，不再显示业务部按钮区：

- 分类饼图：按图中分类精确筛选；验收/交付二分类按 `交付状态` 关键词筛选。
- 预计验收/交付年月柱图：使用与图表相同的按月/未来年份折叠标签筛选。
- 当年/跨年/已验收偏差分类图：先限定对应交付分组，再按偏差分类筛选。
- 业务部进度偏差排名图：先限定当年交付分组，再按逗号拆分后的业务单元包含匹配。
- 已交付未验收业务部排名图：先限定 `已交付` + `未验收`，再按业务单元匹配。

实现说明：普通 Plotly Pie 主要产生 click 事件，Streamlit 原生 `on_select` 无法稳定
接收，因此饼图使用 `streamlit-plotly-events==0.0.6`；柱图使用原生 selection。
两者点击后都轮换 widget/component key，把事件变成一次性事件，确保弹窗关闭后点击
同一扇区或同一柱仍会再次触发。Plotly 6 传给旧组件时必须用 `go.Pie` + Python list
生成普通 JSON 数组，不能直接传 `px.pie` 的 typed-array 数据。

弹窗展示所选项目的全部原始列（`display_columns`：按列顺序排除
`DERIVED_HELPER_COLUMNS` = 执行比例是否虚拟 + 6 个派生应/已归档列）。不要把
“原始列清单”存进被 `@st.cache_data` 缓存的 dataclass；应从当前 DataFrame 现算。

## 14. Formula (Audit) Export

`src/export_formulas.py` `build_formula_workbook` 生成核算版工作簿：分析单元格为
活公式（`=SUMPRODUCT/COUNTA/SUMIF...`）指向「实施进度底表」，改底表数据自动重算，
供人工核对口径。要点：

- 公式引用底表列的**列字母按导出布局动态计算**（`get_column_letter`），支持任意
  列顺序；行范围用实际数据行数 `$2:$<n+1>`。
- 归档动作列（应/已归档）在底表内用 `IF(...)` 公式重算。
- **禁止在 SUMPRODUCT 内对区域使用 `IFERROR(range,0)`**：Excel 会把它塌成标量而非
  逐元素求值，导致整列因子被当成单一值（实测公司净额算成 sum(收入) 而非
  sum(收入×(1-采购))）。导出数据无错误值、空单元格在算术中即 0，直接去掉 IFERROR。
- 已用真实文件 + 真 Excel 重算交叉校验：项目数/未验收（SUMPRODUCT-SEARCH）、
  视角一二（SUMPRODUCT）、人效净额（SUMPRODUCT）、业务单元净额（SUMIF）全部与
  Python 指标一致。

## 15. 人效基础数据 Replication (person base table + data note)

Columns: `人员`, `净执行合同额`, `所属区域/业务单元`, `数据说明`.

数据说明 rules:

- Person found in `人员关系表` and has net amount > 0: `人员关系表匹配/当前有执行数据`
- Person found in `人员关系表` and net amount = 0: `人员关系表匹配/当前无执行数据`
- Person appears in execution data but not in an uploaded `人员关系表`: department is
  `人员关系缺失/待确认`, note is `人员关系表缺失-未进行项目区域推断`; never infer a
  department from project regions when a relation table exists.
- No `人员关系表` uploaded at all: `无人员关系表-区域按项目推断`

## 16. 26年人均净合同额（人员3口径）

This is a separate business metric from section 4. Do not reuse the legacy
`收入 * (1 - B-服务采购比例)` result as the 2026 personnel-3 result.

Required input sheets:

- `input_实施进度表` (legacy alias: `实施进度底表`)
- `input_外委更新金额`
- `input_人员关系表` (legacy alias: `人员关系表`)

Columns are resolved by header text, never by Excel column position. The new
personnel-3 calculation must not create virtual equal-split execution ratios.

Outsourced-subproject states:

- `已匹配`: included in accepted outsourced amount.
- `需人工确认`: candidate is shown but excluded until explicitly confirmed.
- `未匹配`: no credible candidate; excluded and reported as an exception.

Matching priority is project-number exact match, normalized-name exact match,
then fuzzy candidate generation. Explicit confirmations override generated
status only when the specified implementation project exists.

Project formulas:

```text
净额取数基数 = 中标/合同金额（非空且非0） else 预估项目金额
最终采信服务采购金额 = 已匹配外委子项目金额合计（若>0） else B-服务采购比例 * 净额取数基数
项目净执行合同额 = 净额取数基数 - 最终采信服务采购金额
26年净执行合同额 = 项目净执行合同额 * MAX(0, 26/12/31预计进度 - 1/1进度)
```

Missing start or acceptance date gives a 2026-12-31 expected progress of 100%.
Projects whose original manager region contains `绿链` or `数字化市场团队`
remain in calculation detail but have `是否纳入口径=否` and included amount 0.
When a regional team and `电碳市场团队` coexist, remove the latter from the
project net attribution department because it is guidance-only.

Personnel allocation and three-level outputs:

- Build the personnel-3 list only from `人员 3` and `所属区域 3`, deduplicate by
  person, and sort by person name for stable output.
- Unpivot `执行人员1-5` only when both person and corresponding ratio are filled.
  Never infer a ratio from `A-执行人员` in this metric.
- Allocation amount is `纳入口径26年净执行合同额 * 执行比例`. People outside the
  personnel-3 list remain in allocation detail but do not enter person output.
- Company and department amounts come directly from project detail, not allocation.
- Company denominator is the deduplicated personnel-3 count. Department denominator
  is the personnel-3 count whose `所属区域 3` equals that department.
- Person output includes every personnel-3 member; no participation produces amount 0
  and note `未填报分摊比例或未参与`.

Required exceptions include fuzzy/unmatched outsourcing, missing person ratios,
filled-ratio total not equal to 100%, people outside personnel-3, missing project IDs,
and excluded projects. Missing ratios do not reduce company/department project amount.

The 0713 source workbook has a formula defect in personal allocation: project-detail
IDs can be numeric while allocation IDs are text, so Excel `MATCH` returns no result
and all cached personal amounts remain 0 even after full recalculation. The application
normalizes IDs/uses row-linked project keys. Formula export must do the same and must
not copy that mixed-type `MATCH` formula unchanged.

Personnel-3 exports use the current matching-editor decisions and are separate from
the legacy four-section downloads. Both value and formula workbooks contain, in order:

- `output_`: summary, company, department, person, and exceptions.
- `calculation_`: outsourced matching, project net detail, personnel allocation,
  personnel-3 list, and checks.
- `input_`: untouched implementation, outsourced amount, and personnel relation tables.

The formula workbook marks formula headers orange (`#C65911`) and formula cells pale
yellow (`#FFF2CC`). Project IDs in project and allocation calculation sheets are written
as normalized text, and allocation uses `SUMIF` over those text keys.

公式核算版必须把三张 `input_` 作为唯一原始数据层。可直接追溯的字段不得再次写死：

- 外委匹配表的序号、名称、金额引用 `input_外委更新金额`；匹配状态和指定项目保留为
  系统初判/人工确认结果，采信判断与金额使用公式。
- 项目净额明细的项目字段、金额、比例、日期和期初进度引用 `input_实施进度表`，后续
  净额、年度进度与纳入口径金额均使用分步公式。
- 人员3名单引用 `input_人员关系表` 的首次有效人员行；人员分摊明细的项目、人员、比例、
  部门、范围判断和金额全部沿输入/计算表使用公式。
- 公司、部门、人员、汇总和核验表继续引用 calculation 层。异常表是规则引擎生成的文本
  审计清单，不为制造公式而使用无意义的 `="固定文字"`。

导出工作簿由应用按本次 input 行数生成，公式范围使用实际行边界而非整列引用；以后新增、
删除项目或人员时应重新上传三张 input 并导出，不能只在旧成果文件末尾粘贴新行。

## 17. KPI and Summary-Cell Drill-down

可明确对应项目范围的大数字均直接打开项目明细，显示值和下钻范围必须共用同一口径：

- `执行项目总数`：当前筛选后的全部底表行。
- 新签/遗留未验收平均进度：先按 `交付状态` 包含 `未验收`，再按
  `执行项目类型` 包含 `新签`/`遗留`。
- 所有未验收平均偏差：`交付状态` 包含 `未验收`。
- 归档完成度：所有 `当前进度 >= 10%`、已经触发至少一个归档义务的项目。
- 当年/跨年/已验收卡片：复用 `delivery_group_mask` 的对应项目分组。
- 当年交付率：明细展示分母，即 `预计交付日期` 年份等于统计年的应交付项目。
- 异常通报阶段卡片：分别复用该阶段 `应归档=1`、`应归档=1 且未质控`、
  `应归档=1 且已归档=0` 的项目范围。

进度汇总三表的数字单元格下钻：

- `公司整体`：使用该表指标的全公司项目范围。
- 业务单元行：在指标范围内再用 `projects_of_unit` 做逗号拆分后的区域包含匹配。
- `项目数` 只纳入 `A-项目名称` 非空行；未验收/已验收严格沿用第 11 节状态口径。
- 数字为 `0` 时仍可点击，弹窗显示 `共 0 个项目 / 暂无数据`，便于核对。

实现采用 `render_clickable_big_number` 和 `render_selectable_metric_table`。后者使用
透明数字按钮构造表格，不依赖 Streamlit canvas dataframe 的单元格选择事件；这是为了
保证关闭弹窗后点击同一个数字仍能稳定再次触发。

## 18. Archive, Alert, and Ranking Drill-down (2026-07-14)

### 归档视角一

页面和导出工作簿统一显示为：`视角一：各阶段项目整体归档率（当前及之前阶段都要完成）`。
括号内说明强调递进规则：项目处于中期或终期时，前面阶段的归档也必须完成。

点击分母柱：返回该阶段进度范围内的全部应归档项目；点击分子柱：在同一范围内按
第 5 节递进规则返回已完成项目。点击顶部归档率文字：返回该比率的完整分母项目。
`整体` 为启动/中期/终期三个互斥当前阶段项目范围的合并。

反查函数：`archive_view_1_project_subset(raw, stage, completed=...)`。

### 归档视角二

页面和导出工作簿统一显示为：`视角二：环节维度归档完成率（各归档环节单独计算）`。
括号内说明强调各环节互相独立，只判断所统计的启动、中期或终期环节本身是否完成。

点击分母柱：返回达到该环节阈值的归档环节记录；点击分子柱：再限定本环节归档列
为 `是`。点击顶部完成率文字：返回该比率的完整分母环节记录。

`整体` 是三类环节记录的纵向合并，**不能按项目去重**。例如一个进度 100% 的项目会
分别产生启动/中期/终期三条记录；明细增加 `归档环节` 列，因此记录数必须与图中
整体分母/分子一致。

反查函数：`archive_view_2_record_subset(raw, node, completed=...)`。

### 仪表盘缩放适配

- 图表标题放在 Plotly 图形外部，可自动换行，不再被图形画布截断。
- 饼图把百分比放在扇区内、完整名称放在底部图例和悬浮提示中；点击扇区下钻保持不变。
- 页面宽度低于 1200px 时卡片允许换行，低于 900px 时主要卡片改为单列。
- 自定义指标表宽度不足时只在表格内部横向滚动，不产生整个页面的横向滚动条。

### 异常通报

- `各阶段异常情况对比`：点击任意柱，按 `阶段 + 指标` 返回项目。
- `项目个数` 对应该阶段 `应归档=1`；`未完成质控个数` 对应应归档且质控不为 `是`；
  `未完成归档个数` 对应应归档且 `已归档=0`。
- 业务部门异常表：点击 `记录数` 后，在该阶段区域表的 focus 范围内再用
  `projects_of_unit` 做业务单元包含匹配。存在质控字段时 focus 为未完成质控；
  缺少质控字段时回退为未完成归档。

反查函数：`stage_alert_project_subsets(raw, stage)`；`build_stage_alerts` 也必须调用
同一函数，避免展示数字和弹窗范围漂移。

### 项目进度偏差排名

跨年项目偏差排名的项目名、偏差值均可点击。按排名表保留的原始 DataFrame index
定位 `cross_projects` 中的单条底表记录，不仅按项目名称匹配，避免重名项目串行。

## 19. Personnel-3 Upload, Confirmation, and Drill-down (2026-07-14)

- 同一上传文件可同时服务旧四章节和人员3第五章节；人员3输入缺失或校验失败不得阻断旧报表。
- 第五章节按三张 `input_` 表全量计算，不套用页面顶部旧报表筛选。
- 外委初判严格保留 `已匹配 / 需人工确认 / 未匹配`。人工把候选改为 `已匹配` 时，
  必须同时存在有效的对应实施项目编号，随后立即重算外委采信、项目净额和三级人效。
- `系统初判` 与 `当前确认结果` 分开显示；重置匹配恢复系统初判。
- 公司 KPI 明细使用纳入口径项目或人员3名单；部门明细分项目和人员两个标签；个人明细
  使用其显式比例分摊记录；项目明细分项目净额、外委子项目、人员分摊三个标签。
- 匹配状态和异常分布点击后只返回对应状态/异常类型的记录。所有弹窗关闭后应允许再次点击。
- 0713 原始 input 的保守初判为 `28/10/24`，历史 calculation 确认后为 `31/7/24`；
  两者差异来自三条低置信匹配，不得用旧输出静默改变新上传文件的初判。
