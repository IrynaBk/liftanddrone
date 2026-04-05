"""Vibration and motor output chart."""

from typing import Dict

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from core.constants import (
    VIBE_CRITICAL_THRESHOLD,
    VIBE_WARNING_THRESHOLD,
    MOTOR_MAX_PWM,
    MOTOR_MIN_PWM,
    MOTOR_SATURATION_MARGIN,
)


def build_vibration_motor_panel(data: Dict) -> go.Figure:
    """Create a split panel showing vibration (top) and motor outputs (bottom)."""
    vibe_data = data.get('VIBE', [])
    rcou_data = data.get('RCOU', [])

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("Vibration Levels", "Motor Outputs"),
        vertical_spacing=0.15
    )

    if vibe_data:
        times = [msg['TimeS'] for msg in vibe_data]
        vibe_x = [msg.get('VibeX', 0) for msg in vibe_data]
        vibe_y = [msg.get('VibeY', 0) for msg in vibe_data]
        vibe_z = [msg.get('VibeZ', 0) for msg in vibe_data]

        y_max = max(max(vibe_x), max(vibe_y), max(vibe_z), VIBE_CRITICAL_THRESHOLD) * 1.1

        fig.add_hrect(y0=VIBE_CRITICAL_THRESHOLD, y1=y_max,
                      fillcolor="red", opacity=0.1, line_width=0,
                      row=1, col=1, annotation_text="CRITICAL")
        fig.add_hrect(y0=VIBE_WARNING_THRESHOLD, y1=VIBE_CRITICAL_THRESHOLD,
                      fillcolor="orange", opacity=0.1, line_width=0,
                      row=1, col=1, annotation_text="WARNING")

        fig.add_hline(y=VIBE_WARNING_THRESHOLD, line_dash="dash", line_color="orange", row=1, col=1)
        fig.add_hline(y=VIBE_CRITICAL_THRESHOLD, line_dash="dash", line_color="red", row=1, col=1)

        fig.add_trace(go.Scatter(x=times, y=vibe_x, name='VibeX', line=dict(color='red'),
                                 hovertemplate='<b>VibeX</b><br>%{x:.1f}s: %{y:.1f} m/s²<extra></extra>'),
                      row=1, col=1)
        fig.add_trace(go.Scatter(x=times, y=vibe_y, name='VibeY', line=dict(color='green'),
                                 hovertemplate='<b>VibeY</b><br>%{x:.1f}s: %{y:.1f} m/s²<extra></extra>'),
                      row=1, col=1)
        fig.add_trace(go.Scatter(x=times, y=vibe_z, name='VibeZ', line=dict(color='blue'),
                                 hovertemplate='<b>VibeZ</b><br>%{x:.1f}s: %{y:.1f} m/s²<extra></extra>'),
                      row=1, col=1)
    else:
        fig.add_annotation(text="No vibration data", row=1, col=1)

    if rcou_data:
        times = [msg['TimeS'] for msg in rcou_data]
        c1 = [msg.get('C1', 0) for msg in rcou_data]
        c2 = [msg.get('C2', 0) for msg in rcou_data]
        c3 = [msg.get('C3', 0) for msg in rcou_data]
        c4 = [msg.get('C4', 0) for msg in rcou_data]

        fig.add_hrect(y0=MOTOR_MAX_PWM - MOTOR_SATURATION_MARGIN, y1=MOTOR_MAX_PWM,
                      fillcolor="red", opacity=0.1, line_width=0, row=2, col=1)
        fig.add_hrect(y0=MOTOR_MIN_PWM, y1=MOTOR_MIN_PWM + MOTOR_SATURATION_MARGIN,
                      fillcolor="red", opacity=0.1, line_width=0, row=2, col=1)

        fig.add_trace(go.Scatter(x=times, y=c1, name='M1', line=dict(color='red'),
                                 hovertemplate='<b>Motor 1</b><br>%{x:.1f}s: %{y:.0f} µs<extra></extra>'),
                      row=2, col=1)
        fig.add_trace(go.Scatter(x=times, y=c2, name='M2', line=dict(color='green'),
                                 hovertemplate='<b>Motor 2</b><br>%{x:.1f}s: %{y:.0f} µs<extra></extra>'),
                      row=2, col=1)
        fig.add_trace(go.Scatter(x=times, y=c3, name='M3', line=dict(color='blue'),
                                 hovertemplate='<b>Motor 3</b><br>%{x:.1f}s: %{y:.0f} µs<extra></extra>'),
                      row=2, col=1)
        fig.add_trace(go.Scatter(x=times, y=c4, name='M4', line=dict(color='yellow'),
                                 hovertemplate='<b>Motor 4</b><br>%{x:.1f}s: %{y:.0f} µs<extra></extra>'),
                      row=2, col=1)
    else:
        fig.add_annotation(text="No motor output data", row=2, col=1)

    fig.update_yaxes(title_text="Accel (m/s²)", row=1, col=1)
    fig.update_yaxes(title_text="PWM (µs)", row=2, col=1)
    fig.update_xaxes(title_text="Time (s)", row=2, col=1)

    fig.update_layout(
        title="Vibration & Motor Outputs",
        template="plotly_dark",
        hovermode='x unified',
        height=600,
        margin=dict(l=10, r=10, t=60, b=40)
    )

    return fig
