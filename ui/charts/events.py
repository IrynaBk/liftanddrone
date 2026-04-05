"""Errors and events timeline chart."""

from typing import Dict

import plotly.graph_objects as go


def build_events_panel(data: Dict) -> go.Figure:
    """Create a timeline scatter plot of errors and events."""
    fig = go.Figure()

    err_data = data.get('ERR', [])
    mode_data = data.get('MODE', [])
    ev_data = data.get('EV', [])

    mode_colors_map = {
        0: 'red', 1: 'orange', 2: 'yellow', 3: 'lime', 4: 'cyan', 5: 'blue',
        6: 'purple', 7: 'pink'
    }

    if err_data:
        times = [msg['TimeS'] for msg in err_data]
        subsys = [msg.get('Subsys', 0) for msg in err_data]
        ecodes = [msg.get('ECode', 0) for msg in err_data]
        labels = [f"ERR S{s} E{e}" for s, e in zip(subsys, ecodes)]

        fig.add_trace(go.Scatter(
            x=times, y=[1] * len(times), mode='markers',
            marker=dict(size=8, color='red', symbol='x'),
            name='Errors',
            text=labels,
            hovertemplate='<b>%{text}</b><br>Time: %{x:.1f}s<extra></extra>'
        ))

    if mode_data:
        times = [msg['TimeS'] for msg in mode_data]
        modes = [msg.get('ModeNum', 0) for msg in mode_data]
        colors = [mode_colors_map.get(m, 'gray') for m in modes]
        labels = [f"Mode {m}" for m in modes]

        fig.add_trace(go.Scatter(
            x=times, y=[2] * len(times), mode='markers',
            marker=dict(size=10, color=colors, symbol='diamond'),
            name='Mode Changes',
            text=labels,
            hovertemplate='<b>%{text}</b><br>Time: %{x:.1f}s<extra></extra>'
        ))

    if ev_data:
        times = [msg['TimeS'] for msg in ev_data]
        event_ids = [msg.get('Id', 0) for msg in ev_data]
        labels = [f"Event {eid}" for eid in event_ids]

        fig.add_trace(go.Scatter(
            x=times, y=[3] * len(times), mode='markers',
            marker=dict(size=8, color='cyan', symbol='circle'),
            name='Events',
            text=labels,
            hovertemplate='<b>%{text}</b><br>Time: %{x:.1f}s<extra></extra>'
        ))

    fig.update_xaxes(title_text="Time (s)")
    fig.update_yaxes(tickvals=[1, 2, 3], ticktext=['Errors', 'Modes', 'Events'])

    fig.update_layout(
        title="Errors & Events Timeline",
        template="plotly_dark",
        hovermode='x unified',
        height=300,
        margin=dict(l=10, r=10, t=40, b=40),
        showlegend=True
    )

    return fig
