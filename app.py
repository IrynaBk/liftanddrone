"""
DroneViz: Interactive Streamlit Dashboard for ArduPilot Dataflash Logs
Modern, dark-themed UI with stat cards, interactive 2D map, and switchable panels.
"""

import streamlit as st

# UI imports
from ui.styles import inject_global_css

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


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    """Main Streamlit app."""
    # Inject global CSS
    inject_global_css()

    # Sidebar for upload and settings
    with st.sidebar:
        st.markdown("## 🚁 Lift & Drone")
        st.markdown("ArduPilot Dataflash Log Analysis")
        st.markdown("---")

        # File uploader
        uploaded_file = st.file_uploader("Upload .bin log file", type=["bin"])

        data = None
        metrics = None
        color_by = None
        firmware = None

        if uploaded_file is not None:
            # Show file metadata
            st.markdown("### Log Information")
            st.markdown(f"**File:** `{uploaded_file.name}`")
            st.markdown(f"**Size:** {uploaded_file.size / 1024:.1f} KB")

            # Load data
            with st.spinner("Processing log file..."):
                data, metrics = load_data_from_bytes(uploaded_file.read())

            # Extract firmware
            firmware = extract_firmware_version(data)
            if firmware:
                st.markdown(f"**Firmware:** `{firmware}`")

            st.markdown("---")

            # Display settings
            st.markdown("### Display Settings")
            color_by = st.selectbox(
                "Color trajectory by:",
                ["speed", "altitude", "time"],
                index=0,
                help="Choose how to color the 2D map trajectory"
            )

            st.markdown("---")

            # Quick stats sidebar
            st.markdown("### Quick Stats")
            col1, col2 = st.columns(2)
            
            # Helper to show N/A if value is unavailable (0 or None)
            def display_value(value, default=0, format_str="{:.0f}"):
                if value is None or value == default:
                    return "N/A"
                return format_str.format(value)
            
            with col1:
                st.metric("Duration", metrics['duration_str'])
                st.metric("Distance", f"{metrics['distance_km']:.2f} km")
            with col2:
                st.metric("Max Speed", f"{metrics['max_h_speed_kmh']:.1f} km/h")
                energy_val = display_value(metrics.get('energy_used_mah'), default=0, format_str="{:.0f}")
                st.metric("Energy", f"{energy_val} mAh" if energy_val != "N/A" else "N/A")

        st.markdown("---")
        st.markdown(
            "<div style='font-size:10px; color:#4b5563; text-align:center; margin-top:2rem'>"
            "Lift & Drone v1.0 by Lift & Coast · ArduPilot Telemetry Dashboard<br>"
            "Powered by Streamlit + Plotly</div>",
            unsafe_allow_html=True
        )

    # Main content area
    if data is not None and metrics is not None:
        # Render main content in full-width layout
        render_summary(metrics)
        st.divider()
        render_map(data, color_by)
        st.divider()
        render_panel_toolbar(data, color_by)
    else:
        # Empty state
        st.markdown("---")
        st.info(
            "👈 **Upload a .bin Dataflash log to get started**\n\n"
            "Supported formats:\n"
            "- ArduCopter logs\n"
            "- ArduPlane logs\n"
            "- Rover logs"
        )


if __name__ == "__main__":
    main()
