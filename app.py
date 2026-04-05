"""
DroneViz: Interactive Streamlit Dashboard for ArduPilot Dataflash Logs
Modern, dark-themed UI with stat cards, interactive 2D map, and switchable panels.
"""

import hashlib
import logging

import streamlit as st

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

# UI imports
from ui.styles import inject_global_css, inject_file_uploader_hide_add_button

# Data imports
from data.loader import load_data_from_bytes, extract_firmware_version

# View imports
from views.summary import render_summary
from views.map import render_map
from views.telemetry import render_panel_toolbar


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Lift & Drone",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _log_file_signature(uploaded_files) -> tuple:
    """Stable id for the current upload set (name + size per file)."""
    if not uploaded_files:
        return ()
    return tuple((f.name, f.size) for f in uploaded_files)


def _fmt_size(nbytes: int) -> str:
    """Match Streamlit chip size text (e.g. 1.4MB)."""
    if nbytes >= 1024 * 1024:
        return f"{nbytes / (1024 * 1024):.1f}MB"
    if nbytes >= 1024:
        return f"{nbytes / 1024:.1f}KB"
    return f"{nbytes} B"


def _load_logs_from_uploads(uploaded_files):
    """Load (data, metrics, firmware) for each uploaded .bin file."""
    logs = []
    for f in uploaded_files:
        f.seek(0)
        raw = f.read()
        data, metrics = load_data_from_bytes(raw)
        firmware = extract_firmware_version(data)
        logs.append(
            {
                "name": f.name,
                "size": f.size,
                "data": data,
                "metrics": metrics,
                "firmware": firmware,
            }
        )
    return logs


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    """Main Streamlit app."""
    inject_global_css()

    data = None
    metrics = None
    color_by = None
    firmware = None

    with st.sidebar:
        st.markdown("## 🚁 Lift & Drone")
        st.markdown("ArduPilot Dataflash Log Analysis")
        st.markdown("---")

        uploaded_files = st.file_uploader(
            "Upload .bin log file(s)",
            type=["bin"],
            accept_multiple_files=True,
            help="Upload up to two logs. With two files, choose the active log with the radio buttons under the file list.",
        )

        if uploaded_files:
            if len(uploaded_files) > 2:
                st.warning("At most **2** log files are supported. Only the first two files are loaded.")
                uploaded_files = uploaded_files[:2]

            sig = _log_file_signature(uploaded_files)
            sig_key = hashlib.md5(repr(sig).encode()).hexdigest()[:16]
            n = len(uploaded_files)

            if n >= 2:
                choice = st.radio(
                    "Choose file to show",
                    options=list(range(n)),
                    format_func=lambda i: f"{uploaded_files[i].name}  ·  {_fmt_size(uploaded_files[i].size)}",
                    horizontal=True,
                    key=f"log_switch_{sig_key}",
                )
                active_idx = int(choice)
            else:
                active_idx = 0

            logs = _load_logs_from_uploads(uploaded_files)
            active = logs[active_idx]
            data = active["data"]
            metrics = active["metrics"]
            firmware = active["firmware"]
            if firmware:
                st.markdown(f"**Firmware:** `{firmware}`")

            st.markdown("---")
            st.markdown("### Display Settings")
            color_by = st.selectbox(
                "Color trajectory by:",
                ["speed", "altitude", "time"],
                index=0,
                help="Choose how to color the 2D map trajectory",
            )

            st.markdown("---")
            st.markdown("### Quick Stats")
            col1, col2 = st.columns(2)

            def display_value(value, default=0, format_str="{:.0f}"):
                if value is None or value == default:
                    return "N/A"
                return format_str.format(value)

            with col1:
                st.metric("Duration", metrics["duration_str"])
                st.metric("Distance", f"{metrics['distance_m']:.0f} m")
            with col2:
                st.metric("Max Speed", f"{metrics['max_total_speed_ms']:.1f} m/s")
                energy_val = display_value(metrics.get("energy_used_mah"), default=0, format_str="{:.0f}")
                st.metric("Energy", f"{energy_val} mAh" if energy_val != "N/A" else "N/A")

        inject_file_uploader_hide_add_button(
            uploaded_files is not None and len(uploaded_files) >= 2
        )

        st.markdown("---")
        st.markdown(
            "<div style='font-size:10px; color:#4b5563; text-align:center; margin-top:2rem'>"
            "Lift & Drone v1.0 by Lift & Coast · ArduPilot Telemetry Dashboard<br>"
            "Powered by Streamlit + Plotly</div>",
            unsafe_allow_html=True,
        )

    if data is not None and metrics is not None:
        render_summary(metrics)
        st.divider()
        render_map(data, color_by)
        st.divider()
        render_panel_toolbar(data, color_by)
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
