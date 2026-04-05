"""Mission Summary view - displays key metrics as stat cards."""

import streamlit as st
from typing import Dict
from ui.components import stat_card


def render_summary(metrics: Dict) -> None:
    """Render mission summary as stat cards in a 4x2 grid."""
    st.markdown("### Mission Summary")

    # Helper function to format values or show N/A if unavailable
    def metric_value(value, default=0, format_str="{:.0f}"):
        if value is None or value == default:
            return "N/A"
        return format_str.format(value)

    # Define stat cards with order and styling
    cards = [
        {
            'label': 'Flight Duration',
            'value': metrics.get('duration_str', 'N/A'),
            'unit': 'mm:ss',
            'icon': '🕐',
            'color': '#60a5fa'
        },
        {
            'label': 'Total Distance',
            'value': f"{metrics.get('distance_km', 0):.2f}",
            'unit': 'km',
            'icon': '📍',
            'color': '#34d399'
        },
        {
            'label': 'Max Total Speed',
            'value': f"{metrics.get('max_total_speed_kmh', 0):.1f}",
            'unit': 'km/h',
            'icon': '🚀',
            'color': '#e879f9'
        },
        {
            'label': 'Max H. Speed',
            'value': f"{metrics.get('max_h_speed_kmh', 0):.1f}",
            'unit': 'km/h',
            'icon': '⚡',
            'color': '#f59e0b'
        },
        {
            'label': 'Max V. Speed',
            'value': f"{metrics.get('max_v_speed_kmh', 0):.1f}",
            'unit': 'km/h',
            'icon': '↕️',
            'color': '#f59e0b'
        },
        {
            'label': 'Max Altitude Gain',
            'value': f"{metrics.get('alt_gain_m', 0):.0f}",
            'unit': 'meters',
            'icon': '🏔️',
            'color': '#a78bfa'
        },
        {
            'label': 'Max Acceleration',
            'value': f"{metrics.get('max_accel_ms2', 0):.2f}",
            'unit': 'm/s²',
            'icon': '💥',
            'color': '#fb7185'
        },
        {
            'label': 'Energy Used',
            'value': metric_value(metrics.get('energy_used_mah'), default=0, format_str="{:.0f}"),
            'unit': 'mAh',
            'icon': '🔋',
            'color': '#fb923c'
        },
        {
            'label': 'Avg GPS Satellites',
            'value': metric_value(metrics.get('avg_sats'), default=0, format_str="{:.0f}"),
            'unit': 'sats',
            'icon': '📡',
            'color': '#22d3ee'
        },
    ]

    # Row 1: First 5 cards
    cols1 = st.columns(5, gap="small")
    for i, card_data in enumerate(cards[:5]):
        with cols1[i]:
            st.markdown(stat_card(**card_data), unsafe_allow_html=True)

    # Row 2: Remaining cards
    cols2 = st.columns(5, gap="small")
    for i, card_data in enumerate(cards[5:]):
        with cols2[i]:
            st.markdown(stat_card(**card_data), unsafe_allow_html=True)
