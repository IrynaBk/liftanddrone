"""Mission Summary view - displays key metrics as stat cards."""

import streamlit as st
from typing import Dict

from ui.components import stat_card, format_metric_value


def render_summary(metrics: Dict) -> None:
    """Render mission summary as stat cards in a 4x2 grid."""
    st.markdown("### Mission Summary")

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
            'unit': 'meters',
            'icon': '📍',
            'color': '#34d399',
            'warning': metrics.get('distance_warning'),
        },
        {
            'label': 'Max Total Speed',
            'value': f"{metrics.get('max_total_speed_ms', 0):.1f}",
            'unit': 'm/s',
            'icon': '🚀',
            'color': '#e879f9'
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
            'label': 'Max Altitude (ASL)',
            'value': f"{metrics.get('max_alt_m', 0):.0f}",
            'unit': 'meters above sea level',
            'icon': '🌍',
            'color': '#a78bfa',
            'warning': metrics.get('alt_gain_warning'),
        },
        {
            'label': 'Max Altitude',
            'value': f"{metrics.get('max_alt_above_takeoff_m', 0):.0f}",
            'unit': 'meters above takeoff',
            'icon': '🏔️',
            'color': '#a78bfa',
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
            'value': format_metric_value(metrics.get('energy_used_mah'), default=0, format_str="{:.0f}"),
            'unit': 'mAh',
            'icon': '🔋',
            'color': '#fb923c',
            'warning': metrics.get('battery_warning'),
            'color': '#fb923c',
            'warning': metrics.get('battery_warning'),
        },
        {
            'label': 'Avg GPS Satellites',
            'value': format_metric_value(metrics.get('avg_sats'), default=0, format_str="{:.0f}"),
            'unit': 'sats',
            'icon': '📡',
            'color': '#22d3ee'
        },
    ]

    def _render_stat_card(card_data: Dict) -> None:
        card_kwargs = {k: v for k, v in card_data.items() if k != 'warning'}
        st.markdown(stat_card(**card_kwargs), unsafe_allow_html=True)

    cards_per_row = 4
    for start_idx in range(0, len(cards), cards_per_row):
        row_cards = cards[start_idx:start_idx + cards_per_row]
        cols = st.columns(cards_per_row, gap="small")
        for i, card_data in enumerate(row_cards):
            with cols[i]:
                _render_stat_card(card_data)
        st.markdown('<div style="margin-bottom: 1.5rem;"></div>', unsafe_allow_html=True)

    notice_items = [(c['label'], c['warning']) for c in cards if c.get('warning')]
    if metrics.get('gyro_extremes_warning'):
        notice_items.append(('Gyroscope Extremes', metrics['gyro_extremes_warning']))
    if metrics.get('gyro_extremes_warning'):
        notice_items.append(('Gyroscope Extremes', metrics['gyro_extremes_warning']))
    if notice_items:
        with st.expander(f"⚠️ Metric notices ({len(notice_items)})", expanded=False):
            for label, msg in notice_items:
                st.markdown(f"**{label}**")
                st.warning(msg)
