"""Battery health chart."""

from typing import Dict

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from core.constants import LOW_VOLTAGE_THRESHOLD


def build_battery_panel(data: Dict) -> go.Figure:
    """Create a dual-axis battery health chart (voltage left, current right)."""
    bat_data = data.get('BAT', [])

    if not bat_data:
        fig = go.Figure()
        fig.add_annotation(text="No battery data available")
        return fig

    times = [msg['TimeS'] for msg in bat_data]
    volts = [msg.get('Volt', 0) for msg in bat_data]
    currents = [msg.get('Curr', 0) for msg in bat_data]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(x=times, y=volts, name='Voltage',
                   line=dict(color='red', width=2),
                   hovertemplate='<b>Voltage</b><br>Time: %{x:.1f}s<br>V: %{y:.2f}V<extra></extra>'),
        secondary_y=False
    )

    fig.add_trace(
        go.Scatter(x=times, y=currents, name='Current',
                   line=dict(color='cyan', width=2),
                   hovertemplate='<b>Current</b><br>Time: %{x:.1f}s<br>A: %{y:.1f}A<extra></extra>'),
        secondary_y=True
    )

    low_volt_cells = LOW_VOLTAGE_THRESHOLD * 4
    fig.add_hline(y=low_volt_cells, line_dash="dash", line_color="orange",
                  secondary_y=False, annotation_text="Low Voltage Warning")

    fig.update_xaxes(title_text="Time (s)")
    fig.update_yaxes(title_text="Voltage (V)", secondary_y=False)
    fig.update_yaxes(title_text="Current (A)", secondary_y=True)

    fig.update_layout(
        title="Battery Health",
        template="plotly_dark",
        hovermode='x unified',
        height=400,
        margin=dict(l=10, r=10, t=40, b=40)
    )

    return fig
