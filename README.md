# Project Execution Dashboard - Streamlit Skeleton

This folder is a handoff-ready skeleton for a Streamlit app that lets a user upload raw project execution data and generates dashboard tables/charts similar to the reference screenshots.

## Feasibility

Feasible, with caveats.

The dashboard does not need to reproduce the old screenshot value of 51 projects. Future uploaded raw data may have a different project count, and the app should calculate from the uploaded file each time.

Current feasible modules:

- Project overview: total projects, project type distribution, delivery/acceptance distribution, estimated delivery or acceptance month distribution.
- Progress analysis: average progress, progress deviation, deviation type distribution, business-unit deviation ranking, project-level deviation ranking.
- Archive analysis: two required views.
  - View 1: project-stage progressive compliance rate.
  - View 2: archive-node completion rate.
- Efficiency analysis: company, business-unit, and person-level net execution contract amount.

Remaining data caveats:

- If uploaded data does not include actual delivery or actual acceptance dates, the app can only show estimated delivery or estimated acceptance month.
- If uploaded data has no `已交付-未验收` rows, that table/chart should show 0 or "no data".
- If execution ratios are blank, the app can create virtual equal-split ratios and mark them as virtual.
- If outsourcing ratio is blank, the current default is 0. This must be confirmed with the business owner.
- If no personnel relation table is uploaded, business-unit efficiency will fall back to project region or "unmatched".

## Folder Layout

```text
streamlit_project_dashboard/
  app.py
  requirements.txt
  run_streamlit.ps1
  .streamlit/config.toml
  data/
    raw/          # Put uploaded source files here only for local testing.
    processed/    # Optional generated outputs/cache.
    sample/       # Optional sample files.
  docs/
    DATA_RULES.md
    ENVIRONMENT.md
    AI_HANDOFF.md
    IMPLEMENTATION_PLAN.md
    STATUS.md
  src/
    data_loader.py
    metrics.py
    charts.py
  tests/
    test_metrics.py
```

## Quick Start

```powershell
cd D:\英大碳资产实习\进度信息表\streamlit_project_dashboard
.\run_streamlit.ps1
```

Then upload an Excel file. The app will look for a sheet named `实施进度底表`; if absent, it will scan sheets and pick the first one containing key columns such as `A-项目名称`, `当前进度`, and `交付状态`.

Use the local Python environment:

```text
.venv\Scripts\python.exe
.venv\Scripts\streamlit.exe
```

See [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md) before running tests or adding packages.

## Requested Skills

The user requested these skills from a screenshot:

- spec-driven-development
- planning-and-task-breakdown
- incremental-implementation
- frontend-ui-engineering
- test-driven-development
- source-driven-development
- shipping-and-launch

These exact skills were not available as installed `SKILL.md` files in the current session, so this skeleton follows those methods manually:

- source-driven: based on the current workbook fields and screenshots.
- spec-driven: documented data rules and metric definitions.
- planning: written plan and status files.
- incremental: skeleton first, then metrics, then UI.
- test-driven: starter tests included.
- frontend: Streamlit layout planned.
- shipping: deployment steps documented.
