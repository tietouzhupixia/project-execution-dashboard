# Status

Last updated by AI: 2026-07-14.

## 当前状态速览（2026-07-14）

- 应用已上线 Streamlit Community Cloud，GitHub 仓库
  `github.com/tietouzhupixia/project-execution-dashboard`（main = 最新提交）。
  推送后云端自动重新部署；改 `src/*.py` 后若报旧错，去 Manage app → Reboot app。
- 云端运行环境为 Python 3.14 + pandas 3.x，比本地新；已针对 pandas 3 做多处加固
  （见「2026-07-13」块与 AI_HANDOFF「pandas 3 兼容」）。
- 功能齐全：原四章节 BI 报表、人员3口径第五章节、四维筛选、顶部双版本下载入口（完整数值版 + 完整公式核算版）、
  图表/大数字/业务单元汇总数字点击明细下钻弹窗。测试 46 passed；核算版公式已用
  真 Excel 重算校验与 Python 一致。
- 运行/测试须用 `.venv`；运行依赖在 `requirements.txt`，开发工具在
  `requirements-dev.txt`（云端只装前者）。

## Done

- Feasibility judged as positive.
- Project skeleton created.
- Data rules documented.
- AI handoff documented.
- Implementation plan documented.
- Minimal Streamlit app created.
- Metric modules created.
- Starter tests created.
- Current workbook copied as `data/sample/sample_dashboard_workbook.xlsx`.
- Code compiled successfully and starter test functions passed manually.
- Local `.venv` environment created.
- Dependencies installed into `.venv`.
- `.venv` pytest run passed: `2 passed`.
- Streamlit version verified: `1.59.0`.
- Streamlit app started locally on `http://localhost:8501`.
- Page availability check returned HTTP 200.
- Playwright upload/screenshot smoke check passed with no visible error markers.
- Screenshot artifacts created in `artifacts/screenshots`.
- Reader-facing table formatting was tightened:
  - archive rates display as percentages
  - money and efficiency values display with separators and two decimals
  - count fields display as integers
- Virtual execution ratio warning is shown in Chinese.
- Sample workbook metric smoke test passed:
  - project rows: 46
  - archive view 1 totals: denominator 28, numerator 5
  - archive view 2 totals: denominator 41, numerator 12
  - efficiency company people: 37 total, 30 with net amount
- 2026-07-08 requirement update implemented (single-sheet robust uploads):
  - Six 应归档/已归档 action columns are always recomputed from
    当前进度 + 归档 marks (DATA_RULES §10); conflicting uploaded values
    trigger a warning, blank values are recomputed silently.
  - 进度信息分析 project/acceptance summary blocks (项目数/未验收/已验收 by
    dynamic business unit) computed and rendered in 进度分析 tab (§11).
  - 人效基础数据 数据说明 column added to person table (§12).
  - Robustness verified: workbook variant with only 实施进度底表, reversed
    column order, extra column, and no action columns produces identical
    archive/progress metrics (test + real-workbook smoke script).
  - Test suite: 10 passed. Playwright smoke: found_errors=[].

- 2026-07-09 UI rebuilt to match reference screenshots 1-6 (BI style):
  - Single scrolling page with four numbered sections (一 总览 / 二 进度情况 /
    三 异常通报 / 四 人效分析), blue section banners, light-blue row labels,
    white cards, big blue numbers, reference palette pies/bars.
  - New metrics: `build_kpi_strip` (平均进度 新签/遗留未验收、平均偏差、归档完成度),
    `build_delivery_analysis` (未验收当年/跨年交付、已验收、当年交付率、排名表),
    `build_stage_alerts` (各阶段 项目个数/未完成质控/未完成归档 + 业务部排名),
    overview extras (验收/交付二分布、未验收阶段分布、截至日期).
  - Fixed long-standing date bug: Excel serial ints were parsed as epoch
    nanoseconds (1970); `parse_excel_date_series` now parses serials first
    (range 20000-80000), passes datetime dtype through; 最新进度更新日期 and
    开始执行日期 normalized too. Title now shows real 截至X月X日.
  - Test suite: 14 passed. Playwright smoke checks all four section banners
    render with no error markers; screenshots in `artifacts/screenshots`
    (00_full.png + section_1..4.png).

- 2026-07-09 refinement round:
  - 预计验收/交付年月分布：当年按月、未来年份折叠为整年（随自然年自动前移，
    `month_counts_collapsed`，DATA_RULES §12）。
  - 业务部进度偏差排名表支持行点击下钻：st.dialog 弹出该业务部项目实施进度
    明细（`projects_of_unit`，DATA_RULES §13）。注意 Streamlit 行选择要点
    表格最左侧选择列。
  - 展示层修复：datetime 列先转字符串再 fillna（pandas 3 禁止向 datetime 列
    填字符串）。
  - Tests: 25 passed; Playwright verified collapsed bars and dialog drill-down.

- 2026-07-09 filters + export + section-3 chart:
  - Top filter bar (业务单元/项目经理/进度阶段/预计交付月, empty = all); the whole
    page and the export recompute on the filtered subset, with a visible notice.
  - "下载分析结果 Excel" button: `src/export.py` `build_export_workbook` writes
    项目验收汇总 / 归档分析 / 异常通报 / 交付进度分析 / 人效分析 / 人效基础数据 /
    实施进度底表(含派生列) into one xlsx.
  - 归档合规分析视角一/二 rendered as grouped denominator/numerator bar charts
    with rate annotations (tables kept in an expander); section 3 got a
    三阶段×三指标 grouped bar chart.
  - Test suite: 17 passed. Playwright checks: sections render, download button
    present, applying a unit filter shows 筛选后 13/46 and recomputes the page.

- 2026-07-13 部署上云 + pandas3 加固 + 下钻 + 核算版导出:
  - 部署到 Streamlit Cloud，代码推 GitHub（见「当前状态速览」）。
  - 修复云端崩溃（AttributeError/ImportError/TypeError 系列，根因见 AI_HANDOFF
    「pandas 3 兼容」）：执行人员列全空被读成 float64 时先转 object；纯文本列用
    `not is_numeric_dtype` 判断而非 dtype==object；`pd.Series(pd.NA,float64)` 改
    `float('nan')`；百分号/千分位字符串解析；金额无法解析改为警告而非静默 0。
  - 上传解析加 `st.cache_data`；load 与指标/导出计算均 try/except 给可读错误
    （云端会打码原始堆栈）。
  - 图表明细下钻重做：删除业务部按钮区；总览分类饼图、年月柱图、进度偏差图、
    业务部进度偏差排名图等直接点击图形即可弹出对应项目。弹窗展示全部原始列
    （`display_columns` 排除 `DERIVED_HELPER_COLUMNS`）。
  - 饼图用 `streamlit-plotly-events` 捕获真实 click；柱图沿用 Streamlit 原生 selection。
    两类图均在点击后轮换组件 key，关闭弹窗后可再次点击同一扇区/柱。
  - 不把“原始列清单”存进被 `@st.cache_data` 缓存的 dataclass（缓存键按函数体哈希，
    旧序列化对象缺新字段会 AttributeError）——改成从当前 DataFrame 现算。
  - 新增“下载核算版（含公式）”：`src/export_formulas.py` 生成活公式工作簿，列字母
    动态计算；SUMPRODUCT 内禁用 `IFERROR(range,0)`（Excel 会塌成标量算错）。
    已用真 Excel 重算与 Python 交叉校验全部一致。
  - Test suite: 28 passed. Playwright smoke: 四章节渲染无错、饼图弹窗开-关-同扇区
    再开正常、业务部排名图点击下钻正常。

- 2026-07-13 KPI 与汇总表数字下钻:
  - `执行项目总数`、公司 KPI、当年/跨年/已验收指标和异常通报阶段数字改为可点击
    大数字；弹窗范围严格复用该指标的项目分组。
  - `项目数/未验收项目数/已验收项目数（按业务单元）` 的数字单元格可点击；
    `公司整体` 打开该口径全部项目，业务单元行再按逗号拆分区域包含匹配。
  - Streamlit 1.59 canvas dataframe 的 `single-cell` 事件在浏览器回归中不稳定，三表
    改为视觉一致的透明数字按钮表，关闭后可直接重复点击同一数字。
  - Playwright 已验证 `46 -> 共46个项目`、已验收公司整体 `2 -> 共2个项目`，以及
    关闭后再次点击同一个 `2`；原饼图和业务部排名下钻回归继续通过。

- 2026-07-14 补齐截图四类下钻入口:
  - 归档视角一、视角二的分母柱、分子柱和顶部归档率/完成率文字均可点击；
    视角一按当前阶段递进合规反查，视角二按独立归档环节反查。
  - 视角二“整体”保留同一项目触发的多个归档环节记录并增加 `归档环节` 列，
    因此弹窗记录数与图上 41/12 严格一致，不按项目去重。
  - `各阶段异常情况对比` 的每根柱按阶段+指标反查；三阶段业务部门异常表的每个
    数字按阶段+业务单元反查；跨年 `项目进度偏差排名` 可点项目名或偏差值。
  - 新增公共反查函数 `archive_view_1_project_subset`、
    `archive_view_2_record_subset`、`stage_alert_project_subsets`，统计与下钻共用口径。
  - Test suite: 29 passed。Playwright 新增验证：项目偏差排名、异常对比柱、异常业务部
    数字、归档视角一分母柱、归档率文字、归档视角二整体 41 个环节全部通过。

- 2026-07-14 仪表盘缩放适配与归档标题简化:
  - 归档标题统一改为“当前及之前阶段都要完成”和“各归档环节单独计算”，并同步网页、
    数值版 Excel、公式核算版 Excel。
  - 图表标题移出 Plotly 画布并支持换行；饼图百分比放入扇区，完整分类名放入底部图例，
    保留扇区点击下钻。
  - 点击饼图组件补上 Plotly resize handler，解决 iframe 已变宽但内部 SVG 仍停留在旧宽度、
    导致饼图偏左或被裁成半截的问题；缩放后饼图随卡片缩小并保持居中。
  - 1200px 以下卡片换行，900px 以下主要内容单列；自定义指标表只在自身内部横向滚动。
  - Playwright 按 80%/100%/125%/150%/175%/200% 六档等效宽度验证标题、饼图圆心及
    扇区边界、归档卡片、页面横向溢出、表格滚动及饼图点击弹窗。

- 2026-07-14 人员3口径 phase 1 完成:
  - 新增 `src/personnel3_loader.py`：按字段名读取并校验三张 input 表；不触发旧人效的
    虚拟均分，旧单表路径保持不变。
  - 新增 `src/personnel3_metrics.py`：外委三状态匹配、人工确认覆盖、项目净额归属、
    外委采信优先级、2026年末预计进度、年度净额及纳入口径排除。
  - 金额解析只接受普通数字/规范千分位；逗号数字列表不再被拼成超大数，按无效值
    警告并在计算中按空值处理。
  - 新增 `scripts/check_personnel3_sample.py` 和 8 个专项测试。全量 `37 passed`；0713
    样例状态为 31/7/24，三项金额总计和逐项目对账差异均为 0。

- 2026-07-14 人员3口径 phase 2 完成:
  - 新增 `src/personnel3_outputs.py`：人员3名单、手填比例分摊、公司/部门/个人输出、
    异常检查、核验和最终摘要。
  - 0713对账：22人名单一致、63条分摊业务字段一致、公司和六部门最大差异0；按正式
    三状态生成57条异常，人员3个人金额合计为 `5,311,734.969178`。
  - 用本机Excel对副本执行 `CalculateFullRebuild` 后，原文件个人金额仍为0；确认根因
    是项目明细编号为数值、分摊编号为文本，原 `MATCH` 公式匹配失败。Python结果已
    统一项目键，后续公式导出不得照抄该错误。
  - 全量测试 `41 passed`，compileall 通过。

- 2026-07-14 人员3口径 phase 3 完成:
  - 同一上传文件同时进入旧报表解析和三张 input 表解析；缺少人员3输入时只提示，
    不阻断原四章节。
  - 新增第五章节：外委三状态人工确认、公司 KPI、部门/个人/项目排名、异常、核验。
  - 人工确认表保留候选项目编号；状态改为 `已匹配` 后立即重算项目净额及三级人效。
  - 公司数字、部门、个人、项目、匹配状态、异常图均可点击反查，弹窗关闭后可再次点击。
  - 0713 原始 input 初判为 `28 已匹配 / 10 需人工确认 / 24 未匹配`；浏览器测试确认
    一条候选后实时变为 `29 / 9 / 24`。历史 calculation 结果作为确认输入时仍为 `31 / 7 / 24`。
  - 全量测试 `42 passed`；新旧两套 Playwright 回归与 compileall 全部通过。

- 2026-07-14 人员关系表识别修复:
  - 原四章节读取器现同时识别 `input_人员关系表` 和旧名 `人员关系表`，并优先使用
    `人员 3 / 所属区域 3`；修复上传0713人员3工作簿后仍显示“无人员关系表”的误判。
  - 真实文件回归：关系表34行已载入，人员3正式名单仍为22人，公司、部门和逐项目
    金额对账差异均为0；全量测试 `43 passed`。

- 2026-07-14 人员3口径 phase 4 完成:
  - 人员3完整数值版与核算版使用当前人工确认状态，不受页面顶部旧报表筛选影响。
  - 两类工作簿均按 `output_`、`calculation_`、`input_` 排列13张表，包含结果、异常、
    核验、匹配决策、项目净额、人员分摊、人员3名单及三张完整原始输入。
  - 核算版项目净额、分摊、公司/部门/个人和核验均为活公式；公式列橙色表头、浅黄色
    单元格，项目编号统一为文本并以 `SUMIF` 关联，规避原文件混合类型 `MATCH` 缺陷。
  - 0713真实文件经Microsoft Excel全量重算：公司金额与Python一致，部门最大差异
    `4.66e-10`，个人和逐项目最大差异0，无Excel错误值；全量测试 `45 passed`。

- 2026-07-14 人员3口径完整公式链补强:
  - 13张表仍全部导出；完整核算版现在把三张 `input_` 作为唯一原始数据层。
  - 外委来源字段、项目基础字段、人员3名单和人员分摊全部改为简单跨表公式；公司、部门、
    人员、汇总和核验继续沿 calculation 层计算。异常表保留规则引擎生成的文本审计结果。
  - UI明确提示以后只需上传三张 input；识别到完整输入后，页面顶部两个下载入口直接切换为
    13张表的“下载完整结果（数值版）”和“下载完整核算版（含公式）”，第五章节不再重复放按钮。
  - 0713真实文件经Excel重算，公司/人员/项目差异0，部门最大差异`4.66e-10`，无错误值。

- 2026-07-14 人员3离线 Excel 核算模板:
  - 完整核算版预留 200 个项目、200 条外委、100 名人员及1000条人员分摊公式行；在
    `input_` 预留行内增改数据后可直接由桌面 Excel 重算，不需要重新打开网页。
  - 外委匹配确认移入 `input_外委更新金额` 四个黄色输入列；全部 5 张 calculation 和
    5 张 output 的每一个数据单元格均为公式，包括异常检查的类型与说明。
  - 0713真实文件经 Microsoft Excel `CalculateFullRebuild`：公司、项目、人员结果与
    Python 最大差异均为0，57条异常一致，所有工作表0个Excel错误值。
  - 在第100行离线新增1000元测试项目后，公司金额增加1000、项目数58→59、吴义江个人
    金额增加1000且参与项目数增加1，证明预留行公式链可独立扩展。

- 2026-07-14 人员关系完整性防护:
  - 原“四、人效分析”在已上传人员关系表时，缺失执行人员不再按项目经理区域回退；统一
    归入“人员关系缺失/待确认”，并在数据提醒中列出缺失人数和部分姓名。
  - 保留“完全未上传人员关系表”时的项目区域临时推断，避免破坏旧单表兼容路径。
  - 人员3去重人数不等于22时，页面显示阻断错误，结果仅供排查，顶部数值版和公式版正式
    下载按钮均禁用。真实文件删减为11人后的浏览器回归已验证按钮不可点击。
  - 全量测试 `46 passed`。

## In Progress

- 需用 2-3 份不同来源的真实底表进一步验证（目前主要用样例 + 用户实际文件各一份）。

## Not Started

- 正式访问控制（Streamlit Cloud 应用为公网可访问；如需限制，用 app 的 viewer 白名单）。
- 业务用户正式验收（UAT）。
- 列名别名映射：字段被重命名的文件仍会当作缺列处理（列乱序/增列已支持，改名未支持）。

## Known Risks

- Uploaded files may use different column names.
- Execution ratios may be blank or business-overridden.
- Outsourcing ratio blank values currently default to 0.
- Personnel relation table may be absent.
- Actual delivery/acceptance dates may not exist.
- Future work must use `.venv`; using system Python may miss dependencies or produce inconsistent results.

## Local Runtime

Current local server:

```text
http://localhost:8501
```

Runtime files:

```text
logs/streamlit.pid
logs/streamlit.port
logs/streamlit.out.log
logs/streamlit.err.log
```

Stop command:

```powershell
Stop-Process -Id (Get-Content .\logs\streamlit.pid)
```

## Definition of Done

- User can upload raw Excel file.
- App renders project overview, progress analysis, archive views, and efficiency analysis.
- Missing or virtual data is visibly marked.
- Deployment instructions are tested.
- Next AI or developer can reproduce the workflow from docs.
