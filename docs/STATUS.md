# Status

Last updated by AI: 2026-07-13.

## 当前状态速览（2026-07-13）

- 应用已上线 Streamlit Community Cloud，GitHub 仓库
  `github.com/tietouzhupixia/project-execution-dashboard`（main = 最新提交）。
  推送后云端自动重新部署；改 `src/*.py` 后若报旧错，去 Manage app → Reboot app。
- 云端运行环境为 Python 3.14 + pandas 3.x，比本地新；已针对 pandas 3 做多处加固
  （见「2026-07-13」块与 AI_HANDOFF「pandas 3 兼容」）。
- 功能齐全：四章节 BI 报表、四维筛选、两个下载按钮（数值版 + 含公式核算版）、
  业务部明细下钻弹窗。测试 27 passed；核算版公式已用真 Excel 重算校验与 Python 一致。
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
  - 业务部明细下钻：改用每业务部一个 `st.button`（弃用 `st.dataframe` 行选择，
    换 key 重挂载后首击 selection 不回传，导致“关闭后要再点一次”）；弹窗展示
    该业务部全部原始列（`display_columns` 排除 `DERIVED_HELPER_COLUMNS`）。
  - 不把“原始列清单”存进被 `@st.cache_data` 缓存的 dataclass（缓存键按函数体哈希，
    旧序列化对象缺新字段会 AttributeError）——改成从当前 DataFrame 现算。
  - 新增“下载核算版（含公式）”：`src/export_formulas.py` 生成活公式工作簿，列字母
    动态计算；SUMPRODUCT 内禁用 `IFERROR(range,0)`（Excel 会塌成标量算错）。
    已用真 Excel 重算与 Python 交叉校验全部一致。
  - Test suite: 27 passed. Playwright smoke: 四章节渲染无错、两个下载按钮、下钻
    弹窗开-关-再开循环正常。

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
logs/streamlit-8501.out.log
logs/streamlit-8501.err.log
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
