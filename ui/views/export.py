"""Data export view - provides UI for exporting parsed data and metrics to CSV."""

import streamlit as st
from typing import Dict

from core.export.csv_exporter import (
    export_metrics_to_csv,
    export_message_data_to_csv,
    export_all_telemetry_to_csv,
    generate_csv_filename,
)


def render_export_panel(data: Dict, metrics: Dict) -> None:
    """
    Render data export controls with options for metrics and raw telemetry.
    
    Args:
        data: Dictionary of parsed message streams
        metrics: Dictionary of computed flight metrics
    """
    with st.expander("📊 **Export Data**", expanded=False):
        st.markdown("Export parsed flight data and computed metrics to CSV files.")
        
        col1, col2, col3 = st.columns(3)
        
        # Export metrics
        with col1:
            st.markdown("**Flight Metrics**")
            metrics_csv = export_metrics_to_csv(metrics)
            st.download_button(
                label="📊 Download Metrics",
                data=metrics_csv.getvalue(),
                file_name=generate_csv_filename(prefix="flight_metrics"),
                mime="text/csv",
                use_container_width=True,
                help="Download: duration, distance, speed, altitude, energy, GPS quality, warnings"
            )
        
        # Export all telemetry
        with col2:
            st.markdown("**All Telemetry Data**")
            telemetry_csv = export_all_telemetry_to_csv(data)
            st.download_button(
                label="📤 Download All Data",
                data=telemetry_csv.getvalue(),
                file_name=generate_csv_filename(prefix="flight_telemetry_all"),
                mime="text/csv",
                use_container_width=True,
                help="Download: GPS, IMU, battery, vibration, motor, attitude, and all sensor data"
            )
        
        # Export specific message type
        with col3:
            available_types = sorted([
                msg_type for msg_type in data.keys() 
                if isinstance(data[msg_type], list) and len(data[msg_type]) > 0
            ])
            
            if available_types:
                st.markdown("**Specific Message Type**")
                selected_type = st.selectbox(
                    "Select message type:",
                    available_types,
                    key="msg_type_select",
                    label_visibility="collapsed"
                )
                
                csv_data, suggested_filename = export_message_data_to_csv(data, selected_type)
                st.download_button(
                    label=f"📋 Download {selected_type}",
                    data=csv_data.getvalue(),
                    file_name=suggested_filename,
                    mime="text/csv",
                    use_container_width=True,
                    help=f"Download all {selected_type} message records"
                )
        
        st.markdown("---")
        st.markdown("""
        **Export options:**
        - **Flight Metrics**: Computed statistics (duration, distance, speed, altitude, energy, GPS quality, warnings, EKF data)
        - **All Telemetry Data**: Raw sensor data from all message types (GPS, IMU, battery, vibration, motors, attitude, events, etc.)
        - **Specific Message Type**: Export a single data stream (e.g., just GPS coordinates or just battery readings)
        
        All files are timestamped and ready for analysis in Excel, Python, R, databases, or other tools.
        """)