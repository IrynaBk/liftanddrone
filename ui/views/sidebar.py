"""Sidebar view — file upload, log selection, display settings, quick stats."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

import streamlit as st

from core.parsing.log_parser import get_firmware_version
from core.export.csv_exporter import export_metrics_to_csv, export_all_telemetry_to_csv, generate_csv_filename
from infrastructure.log_loader import load_data_from_bytes
from ui.components import drone_spinner, format_metric_value
from ui.styles import inject_file_uploader_hide_add_button


@dataclass
class SidebarContext:
    data: dict
    metrics: dict
    color_by: str
    file_key: str


def _fmt_size(nbytes: int) -> str:
    if nbytes >= 1024 * 1024:
        return f"{nbytes / (1024 * 1024):.1f}MB"
    if nbytes >= 1024:
        return f"{nbytes / 1024:.1f}KB"
    return f"{nbytes} B"


def _log_file_signature(uploaded_files) -> tuple:
    return tuple((f.name, f.size) for f in uploaded_files)


def _load_logs(uploaded_files) -> list:
    logs = []
    for f in uploaded_files:
        f.seek(0)
        data, metrics = load_data_from_bytes(f.read())
        logs.append({
            "name": f.name,
            "size": f.size,
            "data": data,
            "metrics": metrics,
            "firmware": get_firmware_version(data),
        })
    return logs


def render_sidebar() -> Optional[SidebarContext]:
    """Render the sidebar and return a SidebarContext if a log is loaded, else None."""
    with st.sidebar:
        st.markdown("""
            <div class="sidebar-header">
                <h2>🚁 Lift & Drone</h2>
                <p class="sidebar-subtext">ArduPilot Dataflash Log Analysis</p>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("---")

        uploaded_files = st.file_uploader(
            "Upload .bin log file(s)",
            type=["bin"],
            accept_multiple_files=True,
            help="Upload up to two logs. With two files, choose the active log with the radio buttons under the file list.",
        )

        ctx = None

        if uploaded_files:
            if len(uploaded_files) > 2:
                st.warning("At most **2** log files are supported. Only the first two files are loaded.")
                uploaded_files = uploaded_files[:2]

            sig_key = hashlib.md5(repr(_log_file_signature(uploaded_files)).encode()).hexdigest()[:16]

            active_idx = 0
            if len(uploaded_files) >= 2:
                active_idx = int(st.radio(
                    "Choose file to show",
                    options=list(range(len(uploaded_files))),
                    format_func=lambda i: f"{uploaded_files[i].name}  ·  {_fmt_size(uploaded_files[i].size)}",
                    horizontal=True,
                    key=f"log_switch_{sig_key}",
                ))

            with drone_spinner("Parsing flight log…"):
                logs = _load_logs(uploaded_files)

            active = logs[active_idx]
            if active["firmware"]:
                st.markdown(f"**Firmware:** `{active['firmware']}`")

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
            metrics = active["metrics"]
            ekf_available = metrics.get("ekf_available", False)
            max_speed = (
                metrics.get("ekf_max_speed_ms", 0) if ekf_available
                else metrics.get("max_total_speed_ms", 0)
            )
            speed_label = "Max Speed (EKF)" if ekf_available else "Max Speed (GPS)"
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Duration", metrics["duration_str"])
                st.metric("Distance", f"{metrics['distance_m']:.0f} m")
            with col2:
                st.metric(speed_label, f"{max_speed:.1f} m/s")
                energy_val = format_metric_value(metrics.get("energy_used_mah"), default=0, format_str="{:.0f}")
                st.metric("Energy", f"{energy_val} mAh" if energy_val != "N/A" else "N/A")

            st.markdown("---")
            st.markdown("### Quick Export")
            export_col1, export_col2 = st.columns(2)
            with export_col1:
                st.download_button(
                    label="📊 Metrics CSV",
                    data=export_metrics_to_csv(metrics).getvalue(),
                    file_name=generate_csv_filename(prefix="metrics"),
                    mime="text/csv",
                    use_container_width=True,
                    help="Download computed flight metrics",
                )
            with export_col2:
                st.download_button(
                    label="📤 All Data CSV",
                    data=export_all_telemetry_to_csv(active["data"]).getvalue(),
                    file_name=generate_csv_filename(prefix="telemetry_all"),
                    mime="text/csv",
                    use_container_width=True,
                    help="Download all sensor telemetry data",
                )

            ctx = SidebarContext(
                data=active["data"],
                metrics=metrics,
                color_by=color_by,
                file_key=f"{sig_key}_{active_idx}",
            )

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

    return ctx
