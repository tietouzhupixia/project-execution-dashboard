from __future__ import annotations

from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from src.responsive_plotly_events import plotly_events

# 参考截图配色：蓝 / 黄 / 绿 / 红 / 浅蓝 / 橙
PALETTE = ["#3370FF", "#FFC60A", "#34C724", "#F54A45", "#7FB2FF", "#FF8800"]
BLUE = "#3370FF"
PENDING_CHART_SELECTION = "_pending_chart_selection"


def inject_css() -> None:
    """Page-level styles replicating the reference BI look (banners/cards/numbers)."""
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.2rem; max-width: 1800px; }
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: #FFFFFF;
            border-radius: 12px;
            border: 1px solid #EBEDF0 !important;
            box-shadow: none !important;
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
            min-height: 390px; padding: 1.4rem 0.6rem; border-radius: 10px;
            display: flex; flex-direction: column; align-items: center;
            justify-content: center; text-align: center; letter-spacing: 0.2em;
            margin: 0.2rem 0;
        }
        .chart-title {
            color: #1F2329;
            font-size: 0.95rem;
            font-weight: 600;
            line-height: 1.45;
            overflow-wrap: anywhere;
            padding: 0.9rem 0.9rem 0.15rem 0.9rem;
        }
        [data-testid="stPlotlyChart"] {
            width: 100%;
            min-width: 0;
        }
        .group-banner.grid-header {
            min-height: 68px;
            display: flex;
            align-items: center;
            margin-top: 0;
            margin-bottom: 0.15rem;
        }
        .row-label small { font-size: 0.8rem; letter-spacing: 0; display: block; }
        .delivery-band {
            background: #8FB3FF; color: #FFFFFF;
            border-radius: 10px;
            display: flex; flex-direction: column;
            align-items: center; justify-content: center;
            gap: 0.8rem; text-align: center;
            font-size: 1.35rem; font-weight: 800;
            line-height: 1.35;
        }
        .delivery-band-unaccepted { min-height: 1390px; }
        .delivery-band-accepted { min-height: 684px; }
        .delivery-band span { display: block; }
        div[class*="st-key-delivery-top-kpi-"][data-testid="stVerticalBlock"] {
            min-height: 340px;
        }
        div[class*="st-key-delivery-tall-card-"][data-testid="stVerticalBlock"] {
            min-height: 684px;
        }
        div[class*="st-key-delivery-top-kpi-"][data-testid="stVerticalBlock"]
        > [data-testid="stLayoutWrapper"],
        div[class*="st-key-delivery-tall-card-"][data-testid="stVerticalBlock"]
        > [data-testid="stLayoutWrapper"] {
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        div[class*="st-key-delivery-top-kpi-"] div[class*="st-key-drilldown_big_"],
        div[class*="st-key-delivery-tall-card-"] div[class*="st-key-drilldown_big_"] {
            flex: 1;
        }
        div[class*="st-key-delivery-top-kpi-"] div[class*="st-key-drilldown_big_"][class*="_button"],
        div[class*="st-key-delivery-tall-card-"] div[class*="st-key-drilldown_big_"][class*="_button"] {
            flex: 1;
            display: flex;
            align-items: center;
        }
        div[class*="st-key-alert-grid-card-"][data-testid="stVerticalBlock"] {
            min-height: 390px;
        }
        div[class*="st-key-alert-grid-card-"][data-testid="stVerticalBlock"]
        > [data-testid="stLayoutWrapper"] {
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        div[class*="st-key-alert-grid-card-"] div[class*="st-key-drilldown_big_"] {
            flex: 1;
        }
        div[class*="st-key-alert-grid-card-"]
        div[class*="st-key-drilldown_big_"][class*="_button"] {
            flex: 1;
            display: flex;
            align-items: center;
        }
        div[class*="st-key-delivery-tall-card-"] [data-testid="stVerticalBlockBorderWrapper"] {
            min-height: 684px;
            display: flex;
            align-items: stretch;
        }
        div[class*="st-key-delivery-tall-card-"] [data-testid="stVerticalBlock"] {
            justify-content: space-between;
        }
        @media (max-width: 1200px) {
            [data-testid="stHorizontalBlock"] {
                flex-wrap: wrap;
            }
            [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
                min-width: 250px;
            }
            div[class*="st-key-selectable_table_"] [data-testid="stHorizontalBlock"] {
                flex-wrap: nowrap;
            }
            div[class*="st-key-selectable_table_"] [data-testid="stColumn"] {
                min-width: 0;
            }
            .row-label,
            .delivery-band-unaccepted,
            .delivery-band-accepted { min-height: 110px; }
            div[class*="st-key-delivery-top-kpi-"][data-testid="stVerticalBlock"],
            div[class*="st-key-delivery-tall-card-"][data-testid="stVerticalBlock"] {
                min-height: 0;
            }
            div[class*="st-key-alert-grid-card-"][data-testid="stVerticalBlock"] {
                min-height: 0;
            }
            div[class*="st-key-delivery-tall-card-"] [data-testid="stVerticalBlockBorderWrapper"] {
                min-height: 0;
            }
        }
        @media (max-width: 900px) {
            [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
                min-width: 100%;
            }
            div[class*="st-key-selectable_table_"] [data-testid="stColumn"] {
                min-width: 0;
            }
        }
        .big-card { padding: 0.9rem 1.1rem 1.1rem 1.1rem; }
        .big-card .t { font-size: 0.88rem; font-weight: 600; color: #1F2329; }
        .big-card .v { font-size: 2.3rem; font-weight: 800; color: #3370FF;
                       text-align: center; line-height: 1.5; }
        .big-card .c { font-size: 0.75rem; color: #8F959E; text-align: center; }
        .clickable-big-card-title {
            font-size: 0.88rem; font-weight: 600; color: #1F2329;
            padding: 0.9rem 1.1rem 0 1.1rem;
        }
        .clickable-big-card-caption {
            font-size: 0.75rem; color: #8F959E; text-align: center;
            padding: 0 1.1rem 1.1rem 1.1rem;
        }
        div[class*="st-key-drilldown_big_"] [data-testid="stButton"] button {
            min-height: 3.45rem;
            padding: 0.1rem 0.5rem;
            border: 0;
            background: transparent;
            box-shadow: none;
            color: #3370FF;
            font-size: 2.3rem;
            font-weight: 800;
            letter-spacing: 0;
            line-height: 1.25;
        }
        div[class*="st-key-drilldown_big_"] [data-testid="stButton"] button p {
            color: inherit;
            font-size: 2.3rem;
            font-weight: 800;
            letter-spacing: 0;
            line-height: 1.25;
        }
        div[class*="st-key-drilldown_big_"] [data-testid="stButton"] button:hover {
            border: 0;
            background: #F2F6FF;
            color: #245BDB;
        }
        div[class*="st-key-drilldown_big_"] [data-testid="stButton"] button:focus {
            border: 0;
            box-shadow: 0 0 0 2px rgba(51, 112, 255, 0.22);
        }
        div[class*="st-key-selectable_table_"] {
            border: 1px solid #DEE0E3;
            border-radius: 8px;
            overflow-x: auto;
            overflow-y: hidden;
            margin-bottom: 0.75rem;
            gap: 0 !important;
        }
        div[class*="st-key-selectable_table_"] [data-testid="stHorizontalBlock"] {
            gap: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            min-width: 680px;
        }
        div[class*="st-key-selectable_table_"] [data-testid="stVerticalBlock"] {
            gap: 0 !important;
        }
        div[class*="st-key-selectable_table_"][data-testid="stVerticalBlock"] {
            gap: 0 !important;
        }
        div[class*="st-key-selectable_table_"] [data-testid="stColumn"] {
            border-right: 1px solid #DEE0E3;
            border-bottom: 1px solid #DEE0E3;
        }
        div[class*="st-key-selectable_table_"] [data-testid="stColumn"]:last-child {
            border-right: 0;
        }
        .selectable-metric-cell {
            min-height: 2.25rem;
            display: flex;
            align-items: center;
            padding: 0.35rem 0.65rem;
            color: #1F2329;
            font-size: 0.88rem;
            line-height: 1.25;
        }
        .selectable-metric-header {
            color: #8F959E;
            background: #FAFAFB;
        }
        div[class*="st-key-selectable_table_"] [data-testid="stButton"] button {
            min-height: 2.25rem;
            width: 100%;
            justify-content: flex-start !important;
            padding: 0.35rem 0.65rem;
            border: 0;
            border-radius: 0;
            background: transparent;
            box-shadow: none;
            text-align: left !important;
        }
        div[class*="st-key-selectable_table_"] [data-testid="stButton"] button > div {
            width: 100%;
            justify-content: flex-start !important;
            text-align: left !important;
        }
        div[class*="st-key-selectable_table_"] [data-testid="stButton"] button
        [data-testid="stMarkdownContainer"] {
            width: 100%;
        }
        div[class*="st-key-selectable_table_"] [data-testid="stButton"] button p {
            width: 100%;
            color: #1F2329;
            font-size: 0.88rem;
            font-weight: 400;
            letter-spacing: 0;
            line-height: 1.25;
            text-align: left;
        }
        div[class*="st-key-selectable_table_"] [data-testid="stButton"] button:hover {
            border: 0;
            background: #F2F6FF;
        }
        div[class*="st-key-selectable_table_"] [data-testid="stButton"] button:hover p {
            color: #245BDB;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_section_banner(text: str) -> None:
    st.markdown(f'<div class="section-banner">{text}</div>', unsafe_allow_html=True)


def render_group_banner(text: str, *, grid_header: bool = False) -> None:
    extra_class = " grid-header" if grid_header else ""
    st.markdown(
        f'<div class="group-banner{extra_class}">{escape(text)}</div>',
        unsafe_allow_html=True,
    )


def render_row_label(text: str, note: str = "") -> None:
    note_html = f"<small>{note}</small>" if note else ""
    st.markdown(f'<div class="row-label">{text}{note_html}</div>', unsafe_allow_html=True)


def render_delivery_band(lines: list[str], variant: str) -> None:
    """Render the dashboard's in-content delivery-status band."""
    safe_lines = "".join(f"<span>{escape(line)}</span>" for line in lines)
    st.markdown(
        f'<div class="delivery-band delivery-band-{escape(variant)}">{safe_lines}</div>',
        unsafe_allow_html=True,
    )


def render_big_number(title: str, value: str, caption: str = "") -> None:
    caption_html = f'<div class="c">{caption}</div>' if caption else ""
    st.markdown(
        f'<div class="big-card"><div class="t">{title}</div>'
        f'<div class="v">{value}</div>{caption_html}</div>',
        unsafe_allow_html=True,
    )


def render_chart_title(title: str) -> None:
    """Render chart titles as responsive HTML instead of clipped Plotly SVG text."""
    st.markdown(
        f'<div class="chart-title">{escape(title)}</div>',
        unsafe_allow_html=True,
    )


def render_clickable_big_number(
    title: str,
    value: str,
    caption: str = "",
    *,
    key: str,
) -> bool:
    """Render a KPI value as a button while retaining the BI number-card look."""
    with st.container(key=key):
        st.markdown(
            f'<div class="clickable-big-card-title">{title}</div>',
            unsafe_allow_html=True,
        )
        clicked = st.button(
            value,
            key=f"{key}_button",
            type="tertiary",
            width="stretch",
            help=f"查看{title}对应的项目明细",
        )
        if caption:
            st.markdown(
                f'<div class="clickable-big-card-caption">{caption}</div>',
                unsafe_allow_html=True,
            )
    return clicked


def _capture_chart_selection(widget_key: str, chart_key: str, point_field: str) -> None:
    """Copy a Plotly selection into one-shot state, then remount the chart.

    Plotly selections persist in widget state. Rotating the widget key after a
    click makes closing a dialog and clicking the same point again reliable.
    """
    state = st.session_state.get(widget_key, {})
    selection = state.get("selection", {}) if state else {}
    points = selection.get("points", []) if selection else []
    if not points:
        return

    value = points[0].get(point_field)
    if value is None:
        return
    if isinstance(value, (list, tuple)) and len(value) == 1:
        value = value[0]

    st.session_state[PENDING_CHART_SELECTION] = {
        "chart_key": chart_key,
        "value": value,
    }
    generation_key = f"_chart_generation_{chart_key}"
    st.session_state[generation_key] = st.session_state.get(generation_key, 0) + 1


def _render_selectable_plotly_chart(
    fig: go.Figure,
    *,
    key: str | None,
    point_field: str,
) -> str | None:
    if key is None:
        st.plotly_chart(fig, use_container_width=True)
        return None

    generation_key = f"_chart_generation_{key}"
    generation = st.session_state.get(generation_key, 0)
    widget_key = f"{key}_selection_{generation}"

    def capture() -> None:
        _capture_chart_selection(widget_key, key, point_field)

    st.plotly_chart(
        fig,
        use_container_width=True,
        key=widget_key,
        on_select=capture,
        selection_mode="points",
        config={"displayModeBar": False},
    )

    pending = st.session_state.get(PENDING_CHART_SELECTION)
    if pending and pending.get("chart_key") == key:
        st.session_state.pop(PENDING_CHART_SELECTION, None)
        return str(pending["value"])
    return None


def _render_clickable_pie(
    fig: go.Figure,
    *,
    key: str | None,
    labels: list[str],
) -> str | None:
    """Render the responsive pie with the click component used by existing drill-downs."""
    if key is None:
        st.plotly_chart(fig, use_container_width=True)
        return None

    generation_key = f"_chart_generation_{key}"
    generation = st.session_state.get(generation_key, 0)
    widget_key = f"{key}_click_{generation}"
    events = plotly_events(
        fig,
        override_height=320,
        key=widget_key,
    )
    if events:
        point_number = events[0].get("pointNumber")
        if point_number is not None and 0 <= int(point_number) < len(labels):
            st.session_state[PENDING_CHART_SELECTION] = {
                "chart_key": key,
                "value": labels[int(point_number)],
            }
            st.session_state[generation_key] = generation + 1
            st.rerun()

    pending = st.session_state.get(PENDING_CHART_SELECTION)
    if pending and pending.get("chart_key") == key:
        st.session_state.pop(PENDING_CHART_SELECTION, None)
        return str(pending["value"])
    return None


def render_count_chart(
    title: str,
    data: pd.DataFrame,
    name_col: str | None = None,
    *,
    key: str | None = None,
) -> str | None:
    if data is None or data.empty:
        st.info(f"{title}: 暂无数据")
        return None
    name_col = name_col or data.columns[0]
    chart_data = data[[name_col, "数量"]].copy()
    chart_data["数量"] = pd.to_numeric(chart_data["数量"], errors="coerce").fillna(0)
    total = float(chart_data["数量"].sum())
    if total <= 0:
        st.info(f"{title}: 暂无数据")
        return None

    labels = chart_data[name_col].astype(str).tolist()
    values = [float(value) for value in chart_data["数量"].tolist()]
    colors = [PALETTE[index % len(PALETTE)] for index in range(len(labels))]
    render_chart_title(title)
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            marker=dict(colors=colors),
            sort=False,
        )
    )
    fig.update_traces(
        texttemplate="%{percent:.0%}",
        textposition="inside",
        insidetextorientation="auto",
        textfont_size=12,
        hovertemplate="%{label}<br>数量：%{value}<br>占比：%{percent:.2%}<extra></extra>",
    )
    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.03,
            xanchor="left",
            x=0,
            font=dict(size=11),
        ),
        margin=dict(t=8, b=76, l=12, r=12),
        height=320,
        uniformtext=dict(minsize=10, mode="hide"),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return _render_clickable_pie(fig, key=key, labels=labels)


def render_bar_chart(
    title: str,
    data: pd.DataFrame,
    x: str,
    y: str,
    *,
    key: str | None = None,
) -> str | None:
    if data is None or data.empty or x not in data.columns or y not in data.columns:
        st.info(f"{title}: 暂无数据")
        return None
    render_chart_title(title)
    fig = px.bar(data.sort_values(x), x=x, y=y, text_auto=True)
    fig.update_traces(marker_color=BLUE, textposition="outside", textfont=dict(color=BLUE))
    fig.update_layout(
        margin=dict(t=12, b=24, l=24, r=24),
        height=300,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title=None,
        yaxis_title=None,
    )
    return _render_selectable_plotly_chart(fig, key=key, point_field="x")


def render_deviation_ranking_chart(
    title: str,
    data: pd.DataFrame,
    category_col: str,
    value_col: str,
    *,
    key: str,
) -> str | None:
    """Clickable horizontal percentage ranking used for unit drill-down."""
    if (
        data is None
        or data.empty
        or category_col not in data.columns
        or value_col not in data.columns
    ):
        st.info(f"{title}: 暂无数据")
        return None

    ranked = data[[category_col, value_col]].copy()
    ranked[value_col] = pd.to_numeric(ranked[value_col], errors="coerce")
    ranked = ranked.dropna(subset=[value_col]).sort_values(value_col)
    colors = [BLUE if value >= 0 else "#F54A45" for value in ranked[value_col]]
    fig = go.Figure(
        go.Bar(
            x=ranked[value_col],
            y=ranked[category_col].astype(str),
            orientation="h",
            marker_color=colors,
            hovertemplate="%{y}<br>进度偏差：%{x:.2%}<extra></extra>",
        )
    )
    for category, value in zip(ranked[category_col].astype(str), ranked[value_col]):
        fig.add_annotation(
            x=1.01,
            xref="paper",
            y=category,
            yref="y",
            text=f"{value:.2%}",
            showarrow=False,
            xanchor="left",
            font=dict(size=11, color="#646A73"),
        )
    render_chart_title(title)
    fig.update_layout(
        margin=dict(t=12, b=24, l=24, r=86),
        height=max(300, 88 + 42 * len(ranked)),
        xaxis=dict(title=None, tickformat=".0%", zeroline=True, zerolinecolor="#C9CDD4"),
        yaxis=dict(title=None),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return _render_selectable_plotly_chart(fig, key=key, point_field="y")


def render_horizontal_ranking_chart(
    title: str,
    data: pd.DataFrame,
    category_col: str,
    value_col: str,
    *,
    key: str,
    value_format: str = ",.2f",
    max_rows: int | None = None,
) -> str | None:
    """Clickable horizontal ranking for money/count metrics."""
    if data is None or data.empty or category_col not in data.columns or value_col not in data.columns:
        st.info(f"{title}: 暂无数据")
        return None
    ranked = data[[category_col, value_col]].copy()
    ranked[value_col] = pd.to_numeric(ranked[value_col], errors="coerce")
    ranked = ranked.dropna(subset=[value_col]).sort_values(value_col, ascending=False)
    if max_rows is not None:
        ranked = ranked.head(max_rows)
    ranked = ranked.sort_values(value_col)
    fig = go.Figure(
        go.Bar(
            x=ranked[value_col],
            y=ranked[category_col].astype(str),
            orientation="h",
            marker_color=BLUE,
            text=[format(float(value), value_format) for value in ranked[value_col]],
            textposition="outside",
            cliponaxis=False,
            customdata=ranked[category_col].astype(str),
            hovertemplate=f"%{{y}}<br>{value_col}：%{{x:{value_format}}}<extra></extra>",
        )
    )
    render_chart_title(title)
    fig.update_layout(
        margin=dict(t=12, b=24, l=24, r=96),
        height=max(300, 88 + 34 * len(ranked)),
        xaxis=dict(title=None, visible=False),
        yaxis=dict(title=None),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return _render_selectable_plotly_chart(fig, key=key, point_field="customdata")


def render_multi_bar_chart(
    title: str,
    data: pd.DataFrame,
    x: str,
    y: str,
    series: str,
    *,
    key: str | None = None,
) -> tuple[str, str] | None:
    """Grouped bars, one color per series (long-form input)."""
    if data is None or data.empty:
        st.info(f"{title}: 暂无数据")
        return None
    chart_data = data.copy()
    chart_data["_drilldown_key"] = (
        chart_data[x].astype(str) + "|||" + chart_data[series].astype(str)
    )
    render_chart_title(title)
    fig = px.bar(
        chart_data,
        x=x,
        y=y,
        color=series,
        barmode="group",
        custom_data=["_drilldown_key"],
        color_discrete_sequence=PALETTE, text_auto=True,
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        legend=dict(orientation="h", yanchor="top", y=-0.12, x=0, title=None, font=dict(size=11)),
        margin=dict(t=12, b=56, l=24, r=24),
        height=340,
        yaxis=dict(visible=False),
        xaxis_title=None,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    selected = _render_selectable_plotly_chart(fig, key=key, point_field="customdata")
    if selected is None or "|||" not in selected:
        return None
    category, metric = selected.split("|||", 1)
    return category, metric


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
    *,
    key: str | None = None,
) -> tuple[str, str] | None:
    """Grouped denominator/numerator bars with the completion rate above each group."""
    needed = [category_col, denominator_col, numerator_col, rate_col]
    if data is None or data.empty or any(col not in data.columns for col in needed):
        st.info(f"{title}: 暂无数据")
        return None

    categories = data[category_col].astype(str).tolist()
    render_chart_title(title)
    fig = go.Figure()
    fig.add_bar(
        name=denominator_label,
        x=categories,
        y=data[denominator_col],
        marker_color="#7FB2FF",
        text=data[denominator_col],
        textposition="outside",
        cliponaxis=False,
        customdata=[f"{category}|||denominator" for category in categories],
    )
    fig.add_bar(
        name=numerator_label,
        x=categories,
        y=data[numerator_col],
        marker_color=BLUE,
        text=data[numerator_col],
        textposition="outside",
        cliponaxis=False,
        customdata=[f"{category}|||numerator" for category in categories],
    )
    top = max(float(data[denominator_col].max()), 1.0)
    fig.add_scatter(
        x=categories,
        y=[top * 1.22] * len(categories),
        mode="text",
        text=[f"{rate_label} <b>{float(rate):.1%}</b>" for rate in data[rate_col]],
        textfont=dict(size=12, color=BLUE),
        customdata=[f"{category}|||rate" for category in categories],
        hovertemplate=f"%{{x}}<br>{rate_label}：%{{text}}<extra></extra>",
        showlegend=False,
    )
    fig.update_layout(
        barmode="group",
        legend=dict(orientation="h", yanchor="top", y=-0.12, x=0, font=dict(size=11)),
        margin=dict(t=12, b=56, l=24, r=24),
        height=360,
        yaxis=dict(range=[0, top * 1.35], visible=False),
        xaxis_title=None,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    selected = _render_selectable_plotly_chart(fig, key=key, point_field="customdata")
    if selected is None or "|||" not in selected:
        return None
    category, measure = selected.split("|||", 1)
    return category, measure


def render_metric_table(title: str, data: pd.DataFrame) -> None:
    st.subheader(title)
    if data is None or data.empty:
        st.info("暂无数据")
        return
    st.dataframe(format_table_for_display(data), use_container_width=True, hide_index=True)


def render_selectable_metric_table(
    title: str,
    data: pd.DataFrame,
    *,
    key: str,
    clickable_columns: set[str] | None = None,
) -> tuple[int, str] | None:
    """Render a table whose metric cells are reliable, repeatable drill-down buttons."""
    st.subheader(title)
    if data is None or data.empty:
        st.info("暂无数据")
        return None

    display = format_table_for_display(data)
    selected: tuple[int, str] | None = None
    column_count = len(display.columns)
    with st.container(key=f"selectable_table_{key}"):
        header_columns = st.columns(column_count, gap=None)
        for column_index, column_name in enumerate(display.columns):
            with header_columns[column_index]:
                st.markdown(
                    f'<div class="selectable-metric-cell selectable-metric-header">'
                    f"{escape(str(column_name))}</div>",
                    unsafe_allow_html=True,
                )

        for row_position, (_, row) in enumerate(display.iterrows()):
            row_columns = st.columns(column_count, gap=None)
            for column_index, column_name in enumerate(display.columns):
                value = str(row[column_name])
                is_clickable = (
                    str(column_name) in clickable_columns
                    if clickable_columns is not None
                    else column_index > 0
                )
                with row_columns[column_index]:
                    if not is_clickable:
                        st.markdown(
                            f'<div class="selectable-metric-cell">{escape(value)}</div>',
                            unsafe_allow_html=True,
                        )
                    elif st.button(
                        value,
                        key=f"metric_cell_{key}_{row_position}_{column_index}",
                        type="tertiary",
                        width="stretch",
                        help=f"查看{value}对应的项目明细",
                    ):
                        selected = (row_position, str(column_name))
    return selected


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
    return any(token in column for token in ["率", "当前进度", "时间进度", "进度偏差", "匹配度"])


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
