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
            'value': f"{metrics.get('distance_m', 0):.0f}",
            'unit': 'm',
            'icon': '📍',
            'color': '#34d399',
            'warning': metrics.get('distance_warning'),
        },
        {
            'label': 'Max H. Speed',
            'value': f"{metrics.get('max_h_speed_ms', 0):.1f}",
            'unit': 'm/s',
            'icon': '⚡',
            'color': '#f59e0b'
        },
        {
            'label': 'Max V. Speed',
            'value': f"{metrics.get('max_v_speed_ms', 0):.1f}",
            'unit': 'm/s',
            'icon': '↕️',
            'color': '#f59e0b'
        },
        {
            'label': 'Max Altitude Gain(over the sea level)',
            'value': f"{metrics.get('alt_gain_m', 0):.0f}",
            'unit': 'meters',
            'icon': '🏔️',
            'color': '#a78bfa',
            'warning': metrics.get('alt_gain_warning'),
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

    def _render_stat_card(card_data: Dict) -> None:
        card_kwargs = {k: v for k, v in card_data.items() if k != 'warning'}
        st.markdown(stat_card(**card_kwargs), unsafe_allow_html=True)

    # Row 1: First 4 cards
    cols1 = st.columns(4, gap="small")
    for i, card_data in enumerate(cards[:4]):
        with cols1[i]:
            _render_stat_card(card_data)

    # Row 2: Last 4 cards
    cols2 = st.columns(4, gap="small")
    for i, card_data in enumerate(cards[4:]):
        with cols2[i]:
            _render_stat_card(card_data)

    notice_items = [(c['label'], c['warning']) for c in cards if c.get('warning')]
    if notice_items:
        with st.expander(
            f"⚠️ Metric notices ({len(notice_items)})",
            expanded=False,
        ):
            for label, msg in notice_items:
                st.markdown(f"**{label}**")
                st.warning(msg)
