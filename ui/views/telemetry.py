"""Telemetry Panels view - switchable panels for different telemetry data."""

import streamlit as st
from typing import Dict

from ui.charts.vibration import build_vibration_motor_panel
from ui.charts.attitude import build_attitude_panel
from ui.charts.events import build_events_panel
from ui.charts.trajectory import build_3d_trajectory
from ui.charts.battery import build_battery_panel


def render_panel_toolbar(data: Dict, color_by: str) -> None:
    """Render switchable panel toolbar and selected panel."""
    st.markdown("### Telemetry Panels")

    panels = {
        "Vibration & Motors": build_vibration_motor_panel,
        "Attitude": build_attitude_panel,
        "Events": build_events_panel,
        "3D Trajectory": None,  # Special case: needs color_by param
        "Battery": build_battery_panel,
    }

    panel_names = list(panels.keys())

    try:
        selected = st.pills("Select panel:", options=panel_names, default=panel_names[0])
    except AttributeError:
        selected = st.radio("Select panel:", options=panel_names, index=0, horizontal=True)

    if selected == "3D Trajectory":
        fig = build_3d_trajectory(data, color_by=color_by)
    else:
        fig = panels[selected](data)

    st.plotly_chart(fig, width='stretch', config={'responsive': True})
