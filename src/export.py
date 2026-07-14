from __future__ import annotations

import io

import pandas as pd

from .metrics import MetricResult


def build_export_workbook(
    raw: pd.DataFrame,
    metrics: MetricResult,
    delivery: dict,
    alerts: list[dict],
) -> bytes:
    """Assemble the computed dashboard tables into a downloadable xlsx."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        summary = metrics.progress_summary
        write_blocks(
            writer,
            "项目验收汇总",
            [
                ("项目数（按业务单元）", summary["project_count"]),
                ("未验收项目数（按业务单元）", summary["unaccepted"]),
                ("已验收项目数（按业务单元）", summary["accepted"]),
            ],
        )

        write_blocks(
            writer,
            "归档分析",
            [
                ("视角一：各阶段项目整体归档率（当前及之前阶段都要完成）", metrics.archive_view_1),
                ("视角二：环节维度归档完成率（各归档环节单独计算）", metrics.archive_view_2),
            ],
        )

        alert_summary = pd.DataFrame(
            [
                {
                    "阶段": a["stage"],
                    "项目个数": a["project_count"],
                    "未完成质控个数": a["unqc_count"],
                    "未完成归档个数": a["unarchived_count"],
                }
                for a in alerts
            ]
        )
        alert_blocks: list[tuple[str, pd.DataFrame]] = [("阶段异常通报汇总", alert_summary)]
        for a in alerts:
            alert_blocks.append((f"{a['stage']} 业务部门未完成质控/归档", a["region_table"]))
        write_blocks(writer, "异常通报", alert_blocks)

        current = delivery["current_year"]
        cross = delivery["cross_year"]
        accepted = delivery["accepted"]
        delivery_summary = pd.DataFrame(
            [
                {"分组": "未验收-当年交付", "项目个数": current["count"],
                 "平均进度": current["avg_progress"], "平均进度偏差": current["avg_deviation"]},
                {"分组": "未验收-跨年交付", "项目个数": cross["count"],
                 "平均进度": cross["avg_progress"], "平均进度偏差": cross["avg_deviation"]},
                {"分组": "已验收", "项目个数": accepted["count"],
                 "平均进度": None, "平均进度偏差": None},
            ]
        )
        write_blocks(
            writer,
            "交付进度分析",
            [
                ("交付分组汇总", delivery_summary),
                ("业务部进度偏差排名（当年交付）", current["region_deviation_ranking"]),
                ("项目进度偏差排名（跨年交付）", cross["project_deviation_ranking"]),
            ],
        )

        eff = metrics.efficiency
        write_blocks(
            writer,
            "人效分析",
            [("公司维度", eff["company"]), ("业务单元维度", eff["business_unit"])],
        )
        write_blocks(writer, "人效基础数据", [("单人维度（人效基础数据）", eff["person"])])

        raw.to_excel(writer, sheet_name="实施进度底表", index=False)

    return buffer.getvalue()


def write_blocks(writer: pd.ExcelWriter, sheet_name: str, blocks: list[tuple[str, pd.DataFrame]]) -> None:
    """Write titled tables stacked on one sheet, one blank row between blocks."""
    row = 0
    titles: list[tuple[int, str]] = []
    for title, df in blocks:
        titles.append((row + 1, title))  # openpyxl is 1-based
        frame = df if df is not None and not df.empty else pd.DataFrame({"提示": ["暂无数据"]})
        frame.to_excel(writer, sheet_name=sheet_name, startrow=row + 1, index=False)
        row += len(frame) + 3  # title + header + rows + blank

    worksheet = writer.sheets[sheet_name]
    for title_row, title in titles:
        worksheet.cell(row=title_row, column=1, value=title)
