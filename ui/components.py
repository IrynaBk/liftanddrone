"""Reusable UI components for the dashboard."""

import base64
from contextlib import contextmanager
from pathlib import Path
import streamlit as st


def _drone_img_tag(size: int = 48) -> str:
    """Return an <img> tag with drone.png embedded as base64."""
    img_path = Path(__file__).parent.parent / "static" / "drone.png"
    data = base64.b64encode(img_path.read_bytes()).decode()
    return f'<img src="data:image/png;base64,{data}" width="{size}" height="{size}" style="object-fit:contain;">'


_DRONE_SPINNER_HTML = """
<div id="drone-spinner" style="
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2.5rem 1rem;
    gap: 1.2rem;
">
    <div style="
        width: 320px;
        height: 60px;
        position: relative;
        overflow: hidden;
    ">
        <style>
            @keyframes drone-fly {{
                0%   {{ left: -60px; }}
                100% {{ left: 340px; }}
            }}
            @keyframes propeller-spin {{
                from {{ transform: rotate(0deg); }}
                to   {{ transform: rotate(360deg); }}
            }}
            @keyframes trail-fade {{
                0%   {{ opacity: 0.7; width: 40px; }}
                100% {{ opacity: 0; width: 0px; }}
            }}
            #drone-body {{
                position: absolute;
                top: 50%;
                transform: translateY(-50%);
                animation: drone-fly 1.6s linear infinite;
                font-size: 36px;
                line-height: 1;
                filter: drop-shadow(0 0 6px #3b82f6);
            }}
            #drone-trail {{
                position: absolute;
                right: 0;
                top: 50%;
                transform: translateY(-50%);
                height: 3px;
                background: linear-gradient(to left, transparent, #3b82f6);
                border-radius: 2px;
                animation: trail-fade 1.6s linear infinite;
            }}
        </style>
        <div id="drone-trail"></div>
        <div id="drone-body">{drone_img}</div>
    </div>
    <div style="
        font-family: 'IBM Plex Mono', monospace;
        font-size: 13px;
        color: #6b7280;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    ">{message}</div>
</div>
"""


@contextmanager
def drone_spinner(message: str = "Processing flight data…"):
    """Context manager that shows a flying drone animation while work is in progress."""
    placeholder = st.empty()
    placeholder.markdown(
        _DRONE_SPINNER_HTML.format(message=message, drone_img=_drone_img_tag(48)),
        unsafe_allow_html=True,
    )
    try:
        yield
    finally:
        placeholder.empty()


def stat_card(
    label: str,
    value: str,
    unit: str,
    icon: str,
    color: str,
    warning: str | None = None,
) -> str:
    """
    Create a stat card HTML component for big-number display.

    Args:
        label: Metric name (e.g., "Flight Duration")
        value: Formatted number string (e.g., "12:43")
        unit: Unit label (e.g., "mm:ss")
        icon: Emoji or symbol
        color: Hex color for value text

    Returns:
        HTML string for the stat card
    """
    return f"""
    <div style="
        background: #0f1117;
        border: 1px solid #1e2535;
        border-left: 3px solid {color};
        border-radius: 12px;
        padding: 20px 24px;
        margin: 0;
        font-family: 'IBM Plex Mono', monospace;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    ">
        <div style="
            font-size: 11px;
            color: #6b7280;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 12px;
            font-weight: 500;
        ">
            {icon}&nbsp;&nbsp;{label}
        </div>
        <div>
            <div style="
                font-size: 36px;
                font-weight: 700;
                color: {color};
                line-height: 1;
                letter-spacing: -0.02em;
                word-break: break-word;
            ">
                {value}
            </div>
            <div style="
                font-size: 12px;
                color: #9ca3af;
                margin-top: 6px;
            ">
                {unit}
            </div>
        </div>
    </div>
    """
