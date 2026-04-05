"""Map view - displays 2D GPS trajectory and mission bounds."""

import streamlit as st
import numpy as np
from typing import Dict

from ui.charts.map_panel import build_2d_map_panel
from infrastructure.geocoding import reverse_geocode
from core.pipeline import get_filtered_gps


def render_map(data: Dict, color_by: str) -> None:
    """Render the 2D map and mission bounds info."""
    st.markdown("### Real-World GPS Trajectory")

    fig = build_2d_map_panel(data, color_by=color_by)
    st.plotly_chart(fig, width='stretch', config={'responsive': True})

    st.markdown("#### Mission Bounds")
    gps_data = data.get('GPS', [])

    if gps_data:
        filtered_gps = get_filtered_gps(data)

        if filtered_gps:
            lats = [msg.get('Lat', 0) for msg in filtered_gps]
            lons = [msg.get('Lng', 0) for msg in filtered_gps]
            hdops = [msg.get('HDop', 0) for msg in filtered_gps]
            nsats = [msg.get('NSats', 0) for msg in filtered_gps]

            col1, col2, col3 = st.columns(3)

            with col1:
                takeoff_loc = reverse_geocode(lats[0], lons[0])
                st.markdown(f"""
**Takeoff Location**

{takeoff_loc['city']}, {takeoff_loc['country']}

Lat: {lats[0]:.5f}° | Lon: {lons[0]:.5f}°

Address: {takeoff_loc['address']}
""")

            with col2:
                landing_loc = reverse_geocode(lats[-1], lons[-1])
                st.markdown(f"""
**Landing Location**

{landing_loc['city']}, {landing_loc['country']}

Lat: {lats[-1]:.5f}° | Lon: {lons[-1]:.5f}°

Address: {landing_loc['address']}
""")

            with col3:
                st.metric(
                    "Valid GPS Points",
                    f"{len(filtered_gps)}/{len(gps_data)}",
                    f"Avg HDOP: {np.mean(hdops):.2f}, Avg Sats: {np.mean(nsats):.0f}",
                    help="Quality-filtered GPS records"
                )
