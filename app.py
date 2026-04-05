"""
DroneViz: Interactive Streamlit Dashboard for ArduPilot Dataflash Logs
Modern, dark-themed UI with stat cards, interactive 2D map, and switchable panels.
"""

import logging

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

from ui.styles import inject_global_css

from ui.views.sidebar import render_sidebar
from ui.views.summary import render_summary
from ui.views.map import render_map
from ui.views.telemetry import render_panel_toolbar
from ui.views.ai_analysis import render_ai_analysis

st.set_page_config(
    page_title="Lift & Drone",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    inject_global_css()

    if "app_loaded" not in st.session_state:
        st.session_state["app_loaded"] = True

    ctx = render_sidebar()

    if ctx:
        render_summary(ctx.metrics)
        st.divider()
        render_map(ctx.data, ctx.color_by)
        st.divider()
        render_ai_analysis(ctx.metrics, file_key=ctx.file_key)
        st.divider()
        render_panel_toolbar(ctx.data, ctx.color_by)
    else:
        st.markdown("---")
        st.info(
            "👈 **Upload one or two .bin Dataflash logs**\n\n"
            "With two files, use the **radio buttons under the file list** in the sidebar to choose which log the dashboard shows.\n\n"
            "Supported formats:\n"
            "- ArduCopter logs\n"
            "- ArduPlane logs\n"
            "- Rover logs"
        )


if __name__ == "__main__":
    main()
