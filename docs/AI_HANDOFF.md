# AI Handoff

This file records what has been done in the current workspace and what the next AI should know before continuing.

## Current Workspace

Root:

```text
D:\英大碳资产实习\进度信息表
```

Existing source workbook:

```text
D:\英大碳资产实习\进度信息表\公司项目执行管理仪表盘v0.xlsx
```

New project folder:

```text
D:\英大碳资产实习\进度信息表\streamlit_project_dashboard
```

## User Goal

Build a Streamlit app. Other people upload raw data, and the app generates dashboard tables/charts similar to the reference screenshots.

The app does not need a perfect pixel-level copy. It only needs to generate charts/tables from uploaded data. The raw data and project count may differ from the old screenshots.

Required analysis areas:

- screenshot-style project overview and progress charts
- progress analysis tables
- efficiency analysis tables
- archive analysis with two new views

## Skill Request Status

The user requested skills shown in an image:

- spec-driven-development
- planning-and-task-breakdown
- incremental-implementation
- frontend-ui-engineering
- test-driven-development
- source-driven-development
- shipping-and-launch

These exact skill files were not available in this session. The skeleton was created manually following those principles.

## What Was Done Before Creating This Skeleton

The workbook was inspected. Important source sheets:

- `实施进度底表`
- `进度信息分析`
- `人效基础数据`
- `人效分析`
- `人员关系表`

Earlier workbook edits already performed:

1. `进度信息分析` was filled with project/acceptance summary formulas.
2. `实施进度底表` archive action columns were filled:
   - `启动应归档`
   - `启动已归档`
   - `中期应归档`
   - `中期已归档`
   - `临近中期应归档`
   - `临近中期已归档`
3. Two archive views were added in `进度信息分析`:
   - View 1: project-stage progressive compliance.
   - View 2: archive-node completion.
4. `执行人员1-5` and execution ratios were virtually filled by equal split and marked.
5. `人效基础数据` and `人效分析` were filled with formulas and analysis blocks.

## Important Business Logic

Efficiency:

```text
person_net = 收入 * (1 - B-服务采购比例) * 执行比例
```

If execution ratio is not manually filled, virtual equal split can be used but must be visibly marked.

Archive View 1:

- Project-level.
- A middle-stage project counts complete only if start and middle archive are complete.
- A final-stage project counts complete only if start, middle, and final archive are complete.

Archive View 2:

- Archive-node-level.
- Start, middle, final archive nodes are independent.
- Does not check earlier nodes.

## Current Skeleton Status

Created files:

- `README.md`
- `requirements.txt`
- `.streamlit/config.toml`
- `.gitignore`
- `run_streamlit.ps1`
- `docs/DATA_RULES.md`
- `docs/ENVIRONMENT.md`
- `docs/AI_HANDOFF.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/STATUS.md`
- `app.py`
- `src/data_loader.py`
- `src/metrics.py`
- `src/charts.py`
- `tests/test_metrics.py`
- `data/sample/sample_dashboard_workbook.xlsx`
- `scripts/screenshot_check.py`
- `artifacts/screenshots/01_overview.png`
- `artifacts/screenshots/02_progress.png`
- `artifacts/screenshots/03_archive.png`
- `artifacts/screenshots/04_efficiency.png`
- `artifacts/screenshots/05_raw.png`

Next AI should:

1. Use the local virtual environment at `.venv`.
2. Run `.\run_streamlit.ps1`.
3. Upload the current workbook and verify charts render.
4. Harden edge cases and add screenshots/tests.
5. Add column-alias mapping if a new raw workbook uses different field names.

## 2026-07-08 Requirement Update (implemented)

User clarified upload constraints; all implemented and tested (DATA_RULES §9-§12):

- Uploads may contain **only** `实施进度底表`. The three analysis sheets
  (进度信息分析 / 人效基础数据 / 人效分析) are never read from the upload —
  the app computes and renders their content.
- The six 应归档/已归档 action columns may be absent; `derive_archive_action_columns`
  in `src/data_loader.py` always recomputes them (formula replicated from the
  workbook: 应归档 = progress threshold 0.1/0.5/0.9; 已归档 = 应归档 且 归档列="是").
- Columns may be added or reordered; all access is name-based and tested
  (`test_column_order_and_extra_columns_do_not_matter`).
- `build_progress_summary` in `src/metrics.py` replicates the 进度信息分析 left
  blocks with a **dynamic** business-unit list; person table now carries 数据说明.
- Note: a running Streamlit process caches `src` modules — restart the server
  after editing `src/*.py` (stop via pid file, relaunch on port 8501).

## 2026-07-09 UI Rebuild (reference screenshots 1-6)

The page is now a single scrolling BI-style report replicating the reference
screenshots in `D:\英大碳资产实习\进度信息表\1.png`-`6.png`:

- Styling lives in `src/charts.py` (`inject_css`, `render_section_banner`,
  `render_group_banner`, `render_row_label`, `render_big_number`, `PALETTE`)
  plus `.streamlit/config.toml` theme (page #F2F3F5, primary #3370FF).
- Section metrics: `build_kpi_strip`, `build_delivery_analysis(ref_year=当前年)`,
  `build_stage_alerts` in `src/metrics.py`. Section 3 未完成质控 uses
  `是否完成质控？`（缺列时显示无数据并回退归档口径做业务部排名）.
- Date parsing: `parse_excel_date_series` handles Excel serial ints FIRST
  (pd.to_datetime treats ints as epoch-ns and silently returns 1970 dates).
  Do not "simplify" it back.
- `scripts/screenshot_check.py` now asserts the four section banners exist and
  captures 00_full.png + per-section screenshots.

## 2026-07-09 Filters / Export / Charts

- `filter_projects` in `src/metrics.py` powers the top filter bar; empty
  selection = no filter; unit matching is comma-split containment.
- `src/export.py` `build_export_workbook(raw, metrics, delivery, alerts)`
  returns xlsx bytes for `st.download_button`; `write_blocks` stacks titled
  tables per sheet. Everything is computed from the (possibly filtered) frame.
- 归档视角一/二 and section-3 comparisons are charts
  (`render_ratio_bar_chart`, `render_multi_bar_chart` in `src/charts.py`);
  detail tables live in expanders.
- Playwright gotcha: Streamlit multiselect's first popover item is 全选
  (select-all) — pick options by text in automation scripts.

## 2026-07-09 pandas 3 / Streamlit Cloud compatibility hardening

Cloud runs Python 3.14 + pandas 3.x. Rules learned (do not regress):

- Writing a string into a float64 column cell RAISES TypeError in pandas 3.
  执行人员1-5 arrive as all-NaN float64 when the upload has them empty;
  `ensure_execution_people_and_ratios` coerces them to object dtype first.
- pandas 3 reads pure-text columns as `str` dtype (NOT object). Never gate
  text-parsing on `dtype == object`; use `not is_numeric_dtype(...)`.
- `pd.Series(pd.NA, dtype="float64")` raises — use `float("nan")`.
- Tolerated inputs: percent strings ("50%") in ratio columns, thousand
  separators in money columns (unparseable money warns instead of silent 0),
  name/region separators ，、；; (single source: `split_people`).
- app.py wraps load AND metric/export computation in try/except because
  Streamlit Cloud redacts tracebacks from viewers; upload parsing is cached
  with st.cache_data keyed on file bytes.
- requirements.txt = runtime only (cloud installs this); dev tools live in
  requirements-dev.txt.

## 2026-07-13 Chart Click Drill-down

- The old business-unit button grid was deleted. Project-backed pies and bars now
  open `st.dialog` project details directly from the clicked sector/bar.
- `src/charts.py` owns one-shot chart events. Native Plotly bar selections rotate
  widget keys after each click. Pie traces use `streamlit-plotly-events==0.0.6`
  because Streamlit selection events do not reliably receive Pie click events;
  the component key is rotated before opening the dialog so the same sector can
  be clicked again after closing.
- Build component pies with `go.Pie` and plain Python lists. Plotly 6 typed-array
  JSON from `px.pie` renders every category as 1 in the component's older frontend.
- `src/metrics.py` contains the exact reverse filters used by chart drill-downs:
  `project_subset_by_value`, `project_subset_by_keyword`,
  `project_subset_by_month`, and `project_subset_by_delivery_group`.
- Browser regression in `scripts/screenshot_check.py` verifies Pie click -> close ->
  same-sector click, plus business-unit ranking click. Current result: 28 tests
  passed and both drill-down checks are true.

## 2026-07-13 KPI / Summary-Number Drill-down

- `render_clickable_big_number` in `src/charts.py` makes project-backed KPI values
  direct drill-down buttons while retaining the large blue-number card style.
  `app.py` uses it for the total, four company KPIs, delivery-group KPIs, and
  section-3 stage counts. `render_project_kpi` is the shared dialog wrapper.
- The three section-2 summary blocks use `render_selectable_metric_table`. Their
  metric cells are transparent Streamlit buttons styled as ordinary table cells.
  Do not switch them back to `st.dataframe(selection_mode="single-cell")` without
  browser verification: on Streamlit 1.59 the canvas click did not reliably emit
  a selection event in Playwright, even though the API accepted the mode.
- `show_summary_cell_detail` maps a clicked row back to the exact source scope:
  company row = whole metric scope; unit row = `projects_of_unit(scope, unit)`.
- Browser regression now verifies total `46 -> 共 46 个项目`, accepted company
  total `2 -> 共 2 个项目`, close -> same `2` opens again, plus the earlier Pie
  and unit-ranking checks. Screenshots: `total_kpi_drilldown.png` and
  `accepted_summary_cell_drilldown.png`.

## 2026-07-14 Remaining Screenshot Drill-downs

- The two archive ratio charts now return `(category, measure)` from
  `render_ratio_bar_chart`; `measure` is `denominator`, `numerator`, or `rate`.
  Denominator/numerator bars and the blue rate text (implemented as a Scatter
  text trace, not a Plotly annotation) are all clickable and remount after use.
- Exact reverse filters live in `src/metrics.py`:
  `archive_view_1_project_subset`, `archive_view_2_record_subset`, and
  `stage_alert_project_subsets`. Do not duplicate their masks in `app.py`.
- View 2 overall detail is an archive-node record table, not a unique-project
  table. It concatenates start/middle/final node scopes, inserts `归档环节`, and
  intentionally repeats projects so the dialog count equals 41/12 in the sample.
- `render_multi_bar_chart` now returns `(stage, metric)` via Plotly customdata;
  every bar in the stage alert comparison opens its exact project scope.
- Three stage region tables use transparent metric-cell buttons. Their scope is
  `region_focus` from `stage_alert_project_subsets`, followed by
  `projects_of_unit`. With a QC field, focus is uncompleted QC; without it,
  focus falls back to unarchived projects.
- Cross-year project-deviation ranking uses `render_selectable_metric_table` with
  both columns clickable. It maps the clicked row through the preserved raw index,
  which is safer than project-name matching when names repeat.
- Verification: 29 pytest tests pass. Playwright additionally verifies project
  ranking, alert comparison bar, alert region cell, archive view-1 denominator,
  archive rate text, and archive view-2 overall `41` node records. Screenshots are
  `project_ranking_drilldown.png`, `alert_chart_drilldown.png`,
  `alert_region_drilldown.png`, `archive_view_1_drilldown.png`, and
  `archive_view_2_drilldown.png`.

## 2026-07-14 Personnel-3 Phase 1

Authoritative rule source: workspace `../0713_rules_handoff.md`.

- `src/personnel3_loader.py` reads the three input sheets by header text and returns
  untouched DataFrames plus errors/warnings. It deliberately does not call the legacy
  virtual execution-ratio fill.
- `src/personnel3_metrics.py` implements three-state outsourced-subproject matching,
  optional human confirmation overrides, project net calculation, 2026 year-end
  progress, annual delta, project department attribution, and inclusion exclusions.
- Match defaults: normalized exact/project-ID exact is matched; a unique fuzzy result
  at least 0.75 with a 0.10 lead is matched; score at least 0.45 is confirmation;
  otherwise unmatched. Human-confirmed matched rows take precedence.
- A zero net base forces final accepted outsourced amount to zero even if historical
  outsourced rows point to that project. This prevents negative project net amounts.
- Amount parsing accepts plain numbers and valid thousands separators. Strings such as
  `600000,800000,900000` are invalid lists, not one giant number; they generate a warning.
- `scripts/check_personnel3_sample.py <workbook>` rebuilds calculations from input sheets.
  Historical matched rows are supplied as confirmations only for comparison with the
  sample cache. Result: states 31/7/24; all project and total amount differences are 0.
- The sample exception sheet still labels three already-matched low-score rows as
  “需人工确认”. Treat that as stale exception output: the handoff's actual match-state
  field controls inclusion, and an `已匹配` row is included.
- UI and exports are not connected yet. Personnel allocation, summaries, exceptions,
  and checks are implemented in phase 2 below.

## 2026-07-14 Personnel-3 Phase 2

- `src/personnel3_outputs.py` builds the sorted/deduplicated personnel-3 list,
  unpivots only explicit execution person/ratio pairs, and produces company,
  department, person, exception, check, and summary DataFrames.
- Company and department outputs always aggregate `纳入口径26年净执行合同额` from
  project detail. Missing/partial person ratios affect only personal allocation.
- People outside personnel-3 remain visible in allocation and exceptions but do not
  enter person output. All 22 personnel-3 members remain in output, including zeros.
- The 0713 sample has 65 named execution slots, 63 filled person/ratio pairs, two
  missing ratios, six projects whose filled ratios total 25%, and 12 out-of-scope
  allocation people. New-rule exception total is 57 because three historically
  matched low-score rows are no longer duplicated as “需人工确认”.
- Sample comparison: personnel list 22/22 equal; allocation A-F 63/63 equal; company
  and six department outputs have maximum difference 0. Personnel-3 allocated total
  is `5,311,734.969178`; all filled-ratio coverage is `36.225759%`.
- Microsoft Excel `CalculateFullRebuild` on a workbook copy still leaves source person
  formulas at zero. Root cause: project detail IDs are numeric while allocation IDs
  are text, so `MATCH` fails. Python links normalized project keys correctly. The later
  formula exporter must normalize both sides (or avoid mixed-type MATCH).
- Verification: full suite `41 passed`; compileall passed. Reproduction remains
  `scripts/check_personnel3_sample.py <workbook>` using project `.venv`.

## 2026-07-14 Personnel-3 Phase 3

- `app.py` sends the same uploaded bytes to the legacy loader and
  `load_personnel3_inputs_cached`. Personnel-3 parse/missing-sheet errors are isolated;
  the original four sections must continue rendering.
- The fifth section always uses the complete three-input scope and deliberately ignores
  the legacy page-top filters. This is stated above the company KPIs.
- The matching editor key includes a SHA-256 file fingerprint. Editable fields are
  `匹配状态` and `对应实施项目编号`; reset removes that key from session state.
- `系统初判` is immutable generated matching. `当前确认结果` is rebuilt from editor
  confirmations and drives project detail, company/department/person outputs, exceptions,
  checks, charts, and dialogs in the same rerun.
- Raw 0713 input gives `28/10/24`; historical workbook statuses passed as confirmations
  give `31/7/24`. Do not silently promote the three low-confidence historical matches.
- `src/personnel3_outputs.py` owns all fifth-section drill-down scopes. Company amount and
  departments aggregate project detail; personal amounts aggregate only explicit ratios.
- `scripts/personnel3_ui_check.py` uploads the real 0713 workbook, confirms a candidate,
  asserts `29/9/24`, verifies repeatable company detail, and clicks department/person/
  project/matching/exception charts. `scripts/screenshot_check.py` protects legacy UI.
- Current verification: `42 passed`, both Playwright scripts pass, compileall passes.
- Legacy sections now also recognize `input_人员关系表` and prefer
  `人员 3 / 所属区域 3`. This fixes the false “无人员关系表” note for the real 0713
  workbook; the regression suite is now `43 passed`.
- Phase 4 export is complete in `src/personnel3_export.py`. The fifth section exposes
  separate value and formula downloads built from the current matching-editor decisions.
  Both contain 13 ordered `output_` / `calculation_` / `input_` sheets. Formula project IDs
  are normalized text and allocation uses `SUMIF`, never the source mixed-type `MATCH`.
- Real 0713 Microsoft Excel full recalculation matches Python: department maximum difference
  `4.66e-10`, person/project maximum difference 0, and no Excel error cells. Current suite:
  `45 passed`; personnel-3 browser regression passes with both download labels present.

## 2026-07-14 Personnel-3 Complete Formula Chain

- Formula export still contains all 13 ordered sheets (5 output, 5 calculation, 3 input),
  but the three input sheets are now the only raw-data layer.
- Outsource source columns, project source columns, personnel-3 list, and every allocation
  column now use simple row/lookup formulas. Matching status/project remain explicit generated
  or human-confirmed decisions because fuzzy matching is not represented as a fragile Excel formula.
- Output exceptions remain a generated text audit list; all meaningful numeric calculations and
  checks are formula-backed. Formula headers/cells retain orange/yellow audit styling.
- Real 0713 Excel recalculation: company/person/project max difference 0, department max difference
  `4.66e-10`, and zero Excel error cells. UI download labels now explicitly distinguish value and
  complete-formula workbooks.

## 2026-07-14 Personnel Relation Completeness Guard

- When a personnel relation table exists, an execution person missing from it is assigned to
  `人员关系缺失/待确认`; never infer that person's department from project regions. Project-region
  inference remains only for the legacy path where no relation table was uploaded at all.
- The formal personnel-3 headcount is fixed at 22. If the deduplicated count differs, the page may
  show diagnostic results but must disable both complete-workbook download buttons until the
  `input_人员关系表` is corrected.

## 2026-07-14 Responsive Dashboard Layout

- Archive titles now use the same plain-language wording in the web page, value workbook, and
  formula workbook: `当前及之前阶段都要完成` and `各归档环节单独计算`.
- Chart titles are rendered outside Plotly so they can wrap without clipping. Pie percentages are
  inside slices; full labels remain in the bottom legend and hover text. Pie drill-down still uses
  `streamlit-plotly-events` because native Streamlit pie selection was unreliable.
- The upstream click component does not enable React Plotly's resize handler. Keep
  `src/responsive_plotly_events.py`: it reuses the installed frontend in a temporary directory and
  adds `useResizeHandler`, so the inner SVG follows iframe/card width and remains centered.
- Below 1200px cards may wrap; below 900px main cards become single-column. Custom metric tables
  use their own horizontal scroll instead of causing document-level overflow.
- `scripts/responsive_ui_check.py` checks equivalent 80/100/125/150/175/200% browser zoom widths,
  actual pie-slice bounds and center, page/table overflow, and pie click-to-detail.

## Verification Done

- `python -m compileall -q app.py src tests` passed.
- Direct manual execution of the two starter test functions passed.
- `.venv` was created.
- Dependencies were installed into `.venv` from `requirements.txt`.
- `.venv\Scripts\python.exe -m pytest -q` passed with `2 passed`.
- `.venv\Scripts\streamlit.exe --version` returned `Streamlit, version 1.59.0`.
- Local Streamlit server was started on `http://localhost:8501`.
- HTTP availability check returned status 200.
- `scripts/screenshot_check.py` was run against the local Streamlit server; upload and all five tabs completed with `found_errors=[]`.
- Current screenshots are saved under `artifacts/screenshots`.
- UI formatting was adjusted so archive rates show as percentages, money values show with separators and two decimals, and count fields show as integers.
- Virtual execution ratio warnings now display in Chinese.
- Sample workbook smoke test passed. Notable values:
  - project rows: 46
  - archive view 1 overall: 5 / 28
  - archive view 2 overall: 12 / 41
  - efficiency people: 37 total, 30 with net amount

## Environment Rule

Future AI must use:

```text
D:\英大碳资产实习\进度信息表\streamlit_project_dashboard\.venv\Scripts\python.exe
```

Do not use system Python unless rebuilding `.venv`.

## Running Server

At handoff time, the app was started in a hidden background process.

Check URL:

```text
http://localhost:8501
```

PID and logs:

```text
logs/streamlit.pid
logs/streamlit.port
logs/streamlit.out.log
logs/streamlit.err.log
```

Stop it with:

```powershell
Stop-Process -Id (Get-Content .\logs\streamlit.pid)
```
