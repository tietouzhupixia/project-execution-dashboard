# Implementation Plan

## Objective

Build and deploy a Streamlit dashboard where users upload raw Excel data and receive project execution, progress, archive, and efficiency dashboards.

## Stage 0 - Feasibility

Status: done.

Conclusion: feasible.

Not a perfect replica requirement. The dashboard can calculate from uploaded data, so old screenshot count 51 is not required.

## Stage 1 - Project Skeleton

Status: done.

Tasks:

- Create project folder.
- Add docs folder.
- Add data folder.
- Add source code folder.
- Add tests folder.
- Add Streamlit config and requirements.

## Stage 2 - Data Ingestion

Status: MVP done with local upload smoke test.

Tasks:

- Upload Excel through Streamlit.
- Detect `实施进度底表`.
- Validate required columns.
- Load optional `人员关系表`.
- Normalize percentage columns.
- Parse date/month fields.
- Derive virtual execution ratio when missing.

## Stage 3 - Metric Engine

Status: MVP done with sample workbook smoke test.

Tasks:

- Project overview metrics.
- Progress metrics.
- Archive View 1 metrics.
- Archive View 2 metrics.
- Efficiency metrics.
- Business-unit mapping fallback.

## Stage 4 - Dashboard UI

Status: MVP done with screenshot smoke test.

Tasks:

- Page header and upload controls.
- KPI cards.
- Project overview charts.
- Progress analysis tables/charts.
- Archive analysis tables/charts.
- Efficiency analysis tables.
- Warning panels for missing fields and virtual ratios.

## Stage 5 - Testing

Status: starter tests and browser screenshot smoke test added.

Tasks:

- Unit tests for archive view 1 and view 2.
- Unit tests for efficiency formula.
- Unit tests for virtual execution ratio.
- Integration test with sample workbook.

## Stage 6 - Deployment

Status: planned.

Options:

- Local intranet deployment.
- Streamlit Community Cloud if data can leave local environment.
- Internal server deployment with password-protected access.

Recommended for business data:

- Internal server or local machine deployment.
- Do not upload confidential raw data to public cloud unless approved.

## Stage 7 - Next Concrete Steps

1. Validate with 2-3 additional raw workbooks from the business side.
2. Add column-alias mapping for files whose raw field names differ from the current workbook.
3. Add filters for business unit, manager, stage, and delivery month if users need interactive slicing.
4. Decide final deployment mode.
5. Prepare deployment checklist and access-control approach.
