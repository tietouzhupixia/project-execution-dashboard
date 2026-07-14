"""Responsive wrapper around streamlit-plotly-events.

The upstream 0.0.6 component sets its React Plotly element to ``width: 100%``
but does not enable Plotly's resize handler.  When a Streamlit column changes
width, the iframe grows while the SVG keeps its original width.  This module
uses the installed component frontend and applies the one missing
``useResizeHandler`` prop in a temporary build directory.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import tempfile
from pathlib import Path

import streamlit.components.v1 as components


_BUILD_REVISION = "v2"
_RESIZE_MARKER = "frames:t.frames,useResizeHandler:!0,onClick:"
_UPSTREAM_MARKER = "frames:t.frames,onClick:"


def _prepare_frontend() -> Path:
    spec = importlib.util.find_spec("streamlit_plotly_events")
    if spec is None or spec.origin is None:
        raise RuntimeError("缺少 streamlit-plotly-events 运行依赖")

    source = Path(spec.origin).resolve().parent / "frontend" / "build"
    index_text = (source / "index.html").read_text(encoding="utf-8")
    match = re.search(r"static/js/(main\.[^.]+\.chunk\.js)", index_text)
    if match is None:
        raise RuntimeError("无法定位饼图点击组件的前端脚本")

    target = Path(tempfile.gettempdir()) / f"project_dashboard_plotly_events_{_BUILD_REVISION}"
    target_main = target / "static" / "js" / match.group(1)
    if target_main.exists() and _RESIZE_MARKER in target_main.read_text(encoding="utf-8"):
        return target

    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    (target / "index.html").write_text(index_text, encoding="utf-8")
    script_paths = re.findall(r'<script src="\./(static/js/[^"]+\.js)"', index_text)
    for relative_name in script_paths:
        source_script = source / relative_name
        target_script = target / relative_name
        target_script.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_script, target_script)

    script = target_main.read_text(encoding="utf-8")
    if _UPSTREAM_MARKER not in script:
        raise RuntimeError("饼图点击组件版本发生变化，无法启用响应式缩放")
    target_main.write_text(
        script.replace(_UPSTREAM_MARKER, _RESIZE_MARKER, 1),
        encoding="utf-8",
    )
    return target


_component_func = components.declare_component(
    "responsive_plotly_events",
    path=str(_prepare_frontend()),
)


def plotly_events(plot_fig, *, override_height: int = 320, key: str | None = None) -> list[dict]:
    """Render a container-width Plotly figure and return click event points."""
    component_value = _component_func(
        plot_obj=plot_fig.to_json(),
        override_height=override_height,
        override_width="100%",
        key=key,
        click_event=True,
        select_event=False,
        hover_event=False,
        default="[]",
    )
    return json.loads(component_value)
