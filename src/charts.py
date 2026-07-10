from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# 参考截图配色：蓝 / 黄 / 绿 / 红 / 浅蓝 / 橙
PALETTE = ["#3370FF", "#FFC60A", "#34C724", "#F54A45", "#7FB2FF", "#FF8800"]
BLUE = "#3370FF"


def inject_css() -> None:
    """Page-level styles replicating the reference BI look (banners/cards/numbers)."""
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.2rem; max-width: 1500px; }
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: #FFFFFF;
            border-radius: 12px;
            border: 1px solid #EBEDF0;
        }
        .section-banner {
            background: #3370FF; color: #FFFFFF;
            font-size: 1.35rem; font-weight: 700;
            padding: 0.7rem 1.2rem; border-radius: 10px;
            margin: 1.1rem 0 0.9rem 0;
        }
        .group-banner {
            background: #8FB3FF; color: #FFFFFF;
            font-size: 1.05rem; font-weight: 700;
            padding: 0.45rem 1rem; border-radius: 10px;
            margin: 0.4rem 0 0.6rem 0;
        }
        .row-label {
            background: #8FB3FF; color: #FFFFFF;
            font-size: 1.15rem; font-weight: 700;
            padding: 1.4rem 0.6rem; border-radius: 10px;
            text-align: center; letter-spacing: 0.2em;
            margin: 0.2rem 0;
        }
        .row-label small { font-size: 0.8rem; letter-spacing: 0; display: block; }
        .big-card { padding: 0.9rem 1.1rem 1.1rem 1.1rem; }
        .big-card .t { font-size: 0.88rem; font-weight: 600; color: #1F2329; }
        .big-card .v { font-size: 2.3rem; font-weight: 800; color: #3370FF;
                       text-align: center; line-height: 1.5; }
        .big-card .c { font-size: 0.75rem; color: #8F959E; text-align: center; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_section_banner(text: str) -> None:
    st.markdown(f'<div class="section-banner">{text}</div>', unsafe_allow_html=True)


def render_group_banner(text: str) -> None:
    st.markdown(f'<div class="group-banner">{text}</div>', unsafe_allow_html=True)


def render_row_label(text: str, note: str = "") -> None:
    note_html = f"<small>{note}</small>" if note else ""
    st.markdown(f'<div class="row-label">{text}{note_html}</div>', unsafe_allow_html=True)


def render_big_number(title: str, value: str, caption: str = "") -> None:
    caption_html = f'<div class="c">{caption}</div>' if caption else ""
    st.markdown(
        f'<div class="big-card"><div class="t">{title}</div>'
        f'<div class="v">{value}</div>{caption_html}</div>',
        unsafe_allow_html=True,
    )


def render_count_chart(title: str, data: pd.DataFrame, name_col: str | None = None) -> None:
    if data is None or data.empty:
        st.info(f"{title}: 暂无数据")
        return
    name_col = name_col or data.columns[0]
    fig = px.pie(data, names=name_col, values="数量", title=title, color_discrete_sequence=PALETTE)
    fig.update_traces(
        texttemplate="%{label}: %{value} (%{percent:.2%})",
        textposition="outside",
        textfont_size=12,
    )
    fig.update_layout(
        showlegend=False,
        title_font=dict(size=15, color="#1F2329"),
        margin=dict(t=48, b=24, l=24, r=24),
        height=300,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_bar_chart(title: str, data: pd.DataFrame, x: str, y: str) -> None:
    if data is None or data.empty or x not in data.columns or y not in data.columns:
        st.info(f"{title}: 暂无数据")
        return
    fig = px.bar(data.sort_values(x), x=x, y=y, title=title, text_auto=True)
    fig.update_traces(marker_color=BLUE, textposition="outside", textfont=dict(color=BLUE))
    fig.update_layout(
        title_font=dict(size=15, color="#1F2329"),
        margin=dict(t=48, b=24, l=24, r=24),
        height=300,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title=None,
        yaxis_title=None,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_multi_bar_chart(title: str, data: pd.DataFrame, x: str, y: str, series: str) -> None:
    """Grouped bars, one color per series (long-form input)."""
    if data is None or data.empty:
        st.info(f"{title}: 暂无数据")
        return
    fig = px.bar(
        data, x=x, y=y, color=series, barmode="group",
        color_discrete_sequence=PALETTE, text_auto=True, title=title,
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        title_font=dict(size=15, color="#1F2329"),
        legend=dict(orientation="h", yanchor="top", y=-0.12, x=0, title=None, font=dict(size=11)),
        margin=dict(t=48, b=56, l=24, r=24),
        height=340,
        yaxis=dict(visible=False),
        xaxis_title=None,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_ratio_bar_chart(
    title: str,
    data: pd.DataFrame,
    category_col: str,
    denominator_col: str,
    numerator_col: str,
    rate_col: str,
    denominator_label: str = "应完成（分母）",
    numerator_label: str = "已完成（分子）",
    rate_label: str = "完成率",
) -> None:
    """Grouped denominator/numerator bars with the completion rate above each group."""
    needed = [category_col, denominator_col, numerator_col, rate_col]
    if data is None or data.empty or any(col not in data.columns for col in needed):
        st.info(f"{title}: 暂无数据")
        return

    categories = data[category_col].astype(str)
    fig = go.Figure()
    fig.add_bar(
        name=denominator_label,
        x=categories,
        y=data[denominator_col],
        marker_color="#7FB2FF",
        text=data[denominator_col],
        textposition="outside",
        cliponaxis=False,
    )
    fig.add_bar(
        name=numerator_label,
        x=categories,
        y=data[numerator_col],
        marker_color=BLUE,
        text=data[numerator_col],
        textposition="outside",
        cliponaxis=False,
    )
    top = float(data[denominator_col].max())
    for cat, rate in zip(categories, data[rate_col]):
        fig.add_annotation(
            x=cat,
            y=top * 1.22,
            text=f"{rate_label} <b>{float(rate):.1%}</b>",
            showarrow=False,
            font=dict(size=12, color=BLUE),
        )
    fig.update_layout(
        title=title,
        title_font=dict(size=15, color="#1F2329"),
        barmode="group",
        legend=dict(orientation="h", yanchor="top", y=-0.12, x=0, font=dict(size=11)),
        margin=dict(t=48, b=56, l=24, r=24),
        height=360,
        yaxis=dict(range=[0, top * 1.35], visible=False),
        xaxis_title=None,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_metric_table(title: str, data: pd.DataFrame) -> None:
    st.subheader(title)
    if data is None or data.empty:
        st.info("暂无数据")
        return
    st.dataframe(format_table_for_display(data), use_container_width=True, hide_index=True)


def format_table_for_display(data: pd.DataFrame) -> pd.DataFrame:
    """Format numbers for reader-facing dashboard tables."""
    out = data.copy()
    format_metric_value_column(out)
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            # datetime 列先转字符串：pandas 3 不允许向 datetime 列填字符串
            out[col] = out[col].dt.strftime("%Y-%m-%d").fillna("未填")
            continue
        if out[col].dtype == object:
            out[col] = out[col].fillna("未填")
            continue
        if not pd.api.types.is_numeric_dtype(out[col]):
            out[col] = out[col].fillna("未填")
            continue

        col_text = str(col)
        if should_format_as_percent(col_text):
            out[col] = out[col].map(lambda value: format_percent(value))
        elif should_format_as_count(col_text):
            out[col] = out[col].map(lambda value: format_count(value))
        elif should_format_as_money(col_text):
            out[col] = out[col].map(lambda value: format_money(value))
        else:
            out[col] = out[col].map(lambda value: format_number(value))
    return out


def format_metric_value_column(data: pd.DataFrame) -> None:
    """Format long metric tables where the measure name is stored in 指标."""
    if "指标" not in data.columns or "值" not in data.columns:
        return

    formatted_values: list[str] = []
    for metric_name, value in zip(data["指标"], data["值"]):
        metric_text = str(metric_name)
        if should_format_as_count(metric_text):
            formatted_values.append(format_count(value))
        elif should_format_as_money(metric_text):
            formatted_values.append(format_money(value))
        elif should_format_as_percent(metric_text):
            formatted_values.append(format_percent(value))
        else:
            formatted_values.append(format_number(value))
    data["值"] = formatted_values


def should_format_as_percent(column: str) -> bool:
    if "分类" in column or "范围" in column:
        return False
    return any(token in column for token in ["率", "当前进度", "时间进度", "进度偏差"])


def should_format_as_money(column: str) -> bool:
    return any(token in column for token in ["合同额", "净额", "金额", "人均"])


def should_format_as_count(column: str) -> bool:
    return any(token in column for token in ["数量", "项目数", "人数", "分母", "分子", "环节数"])


def format_percent(value: object) -> str:
    if pd.isna(value):
        return "未填"
    return f"{float(value):.2%}"


def format_money(value: object) -> str:
    if pd.isna(value):
        return "未填"
    return f"{float(value):,.2f}"


def format_count(value: object) -> str:
    if pd.isna(value):
        return "0"
    return f"{int(round(float(value))):,}"


def format_number(value: object) -> str:
    if pd.isna(value):
        return "未填"
    number = float(value)
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.4f}"
