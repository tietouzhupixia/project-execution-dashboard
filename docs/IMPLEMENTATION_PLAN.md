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

Status: done with screenshot and click-drilldown smoke tests.

Tasks:

- Page header and upload controls.
- KPI cards.
- Project overview charts.
- Progress analysis tables/charts.
- Archive analysis tables/charts.
- Efficiency analysis tables.
- Warning panels for missing fields and virtual ratios.
- Direct chart click drill-down to matching project details.
- Direct KPI-number and business-unit summary-cell drill-down, including repeat
  clicks after closing the detail dialog.
- Direct drill-down from archive denominator/numerator/rate labels, stage-alert
  grouped bars and unit cells, and project-deviation ranking rows.

## Stage 5 - Testing

Status: 29 unit/integration tests plus browser screenshot and click smoke tests.

Tasks:

- Unit tests for archive view 1 and view 2.
- Unit tests for efficiency formula.
- Unit tests for virtual execution ratio.
- Integration test with sample workbook.
- Browser regression for total KPI, accepted-summary numeric cell, repeated
  same-cell click, Pie sector, and business-unit ranking drill-down.
- Browser regression for archive bars/rate text, stage-alert bars/unit cells,
  and project-deviation ranking drill-down.

## Stage 6 - Deployment

Status: deployed to Streamlit Community Cloud; local runtime also maintained.

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
3. Run business-user UAT for chart drill-down labels and project scopes.
4. Decide whether the cloud app needs viewer allowlisting or internal deployment.

## Stage 8 - 26年人均净合同额（人员3口径）

Status: phases 1-4 complete (2026-07-14).

Authoritative business source: `../0713_rules_handoff.md`.

Phase 1 scope:

- Read `input_实施进度表`, `input_外委更新金额`, and `input_人员关系表` by field name.
- Keep the legacy single-sheet dashboard path working unchanged.
- Validate required fields and report business-readable errors/warnings.
- Classify outsourced subprojects as `已匹配`, `需人工确认`, or `未匹配`.
- Accept explicit human confirmations without silently accepting ambiguous candidates.
- Calculate project net amount, expected progress at 2026-12-31, annual progress delta,
  2026 net execution contract amount, and inclusion status.
- Verify the calculation engine before adding UI charts or exports.

Phase 1 verification:

- Full suite: `37 passed`.
- 0713 sample states: `31 已匹配 / 7 需人工确认 / 24 未匹配`.
- Sample project net, 2026 net, included 2026 net, and every project row match
  the workbook cache within 0.01; observed difference is 0.
- Re-run with `scripts/check_personnel3_sample.py <workbook.xlsx>` using `.venv`.

Later phases:

- Phase 2 complete (2026-07-14): personnel allocation, personnel-3 list,
  company/department/person outputs, exceptions, checks, and final summary.
- Phase 3 complete (2026-07-14): upload integration, editable three-state matching,
  fifth dashboard section, live recalculation, and repeatable click drill-downs.
- Phase 4 complete (2026-07-14): numeric and live-formula audit exports with ordered
  `output_`, `calculation_`, and `input_` sheets, using current matching decisions.
- Run browser regression and deploy incrementally.

Phase 2 verification:

- Full suite: `41 passed`.
- Personnel-3 list: 22 rows, equal to the 0713 calculation sheet.
- Allocation business fields: 63 rows, equal to the 0713 calculation sheet.
- Company and all six department outputs: maximum difference 0.
- Corrected personnel-3 allocated amount: `5,311,734.969178`; the source workbook's
  zero personal output is an Excel mixed-type project-ID lookup defect.
- New-rule exceptions: 57 rows (`31 matched / 7 confirmation / 24 unmatched` matching).

Phase 3 verification:

- Full suite: `42 passed`; compileall passed.
- Raw-input initial matching: `28 matched / 10 confirmation / 24 unmatched`.
- Browser edit changed one prefilled candidate to matched and live counts became `29/9/24`.
- Browser regression passed company KPI reopen plus department, person, project,
  matching-state, and exception drill-downs; the legacy four-section regression also passed.
