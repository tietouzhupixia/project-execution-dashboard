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
logs/streamlit-8501.out.log
logs/streamlit-8501.err.log
```

Stop it with:

```powershell
Stop-Process -Id (Get-Content .\logs\streamlit.pid)
```
