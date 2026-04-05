"""Attitude tracking chart (actual vs desired roll/pitch/yaw)."""

from typing import Dict

import plotly.graph_objects as go


def build_attitude_panel(data: Dict) -> go.Figure:
    """Create an overlay plot of actual vs desired attitude."""
    att_data = data.get('ATT', [])

    if not att_data:
        fig = go.Figure()
        fig.add_annotation(text="No attitude data available")
        return fig

    times = [msg['TimeS'] for msg in att_data]
    roll = [msg.get('Roll', 0) for msg in att_data]
    des_roll = [msg.get('DesRoll', 0) for msg in att_data]
    pitch = [msg.get('Pitch', 0) for msg in att_data]
    des_pitch = [msg.get('DesPitch', 0) for msg in att_data]
    yaw = [msg.get('Yaw', 0) for msg in att_data]
    des_yaw = [msg.get('DesYaw', 0) for msg in att_data]

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=times, y=roll, name='Roll (actual)',
                             line=dict(color='blue', width=2)))
    fig.add_trace(go.Scatter(x=times, y=des_roll, name='Roll (desired)',
                             line=dict(color='blue', width=1, dash='dash')))

    fig.add_trace(go.Scatter(x=times, y=pitch, name='Pitch (actual)',
                             line=dict(color='orange', width=2)))
    fig.add_trace(go.Scatter(x=times, y=des_pitch, name='Pitch (desired)',
                             line=dict(color='orange', width=1, dash='dash')))

    fig.add_trace(go.Scatter(x=times, y=yaw, name='Yaw (actual)',
                             line=dict(color='green', width=2)))
    fig.add_trace(go.Scatter(x=times, y=des_yaw, name='Yaw (desired)',
                             line=dict(color='green', width=1, dash='dash')))

    fig.update_xaxes(title_text="Time (s)")
    fig.update_yaxes(title_text="Angle (degrees)")

    fig.update_layout(
        title="Attitude Tracking",
        template="plotly_dark",
        hovermode='x unified',
        height=400,
        margin=dict(l=10, r=10, t=40, b=40)
    )

    return fig
