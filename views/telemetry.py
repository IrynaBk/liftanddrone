"""Telemetry Panels view - switchable panels for different telemetry data."""

import streamlit as st
from typing import Dict
from drone_dashboard import (
    build_vibration_motor_panel,
    build_attitude_panel,
    build_events_panel,
    build_3d_trajectory,
    build_battery_panel,
)


def render_panel_toolbar(data: Dict, color_by: str) -> None:
    """Render switchable panel toolbar and selected panel."""
    st.markdown("---")
    st.markdown("### Telemetry Panels")

    panels = {
        "Vibration & Motors": build_vibration_motor_panel,
        "Attitude": build_attitude_panel,
        "Events": build_events_panel,
        "3D Trajectory": None,  # Special case: needs color_by param
        "Battery": build_battery_panel,
    }

    panel_names = list(panels.keys())
    default_idx = 0  # Use first panel as default

    # Use pills if available (Streamlit >= 1.40), else radio
    try:
        selected = st.pills(
            "Select panel:",
            options=panel_names,
            default=panel_names[default_idx]
        )
    except AttributeError:
        selected = st.radio(
            "Select panel:",
            options=panel_names,
            index=default_idx,
            horizontal=True
        )

    # Render selected panel
    if selected == "3D Trajectory":
        fig = build_3d_trajectory(data, color_by=color_by)
    else:
        fig = panels[selected](data)

    st.plotly_chart(fig, width='stretch', config={'responsive': True})
