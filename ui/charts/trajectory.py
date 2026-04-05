"""3D trajectory viewer."""

from typing import Dict

import plotly.graph_objects as go

from core.geo.geodesy import wgs84_to_enu


def build_3d_trajectory(data: Dict, color_by: str = 'speed') -> go.Figure:
    """Create an interactive 3D trajectory viewer.

    Uses EKF-fused trajectory when available, falls back to raw GPS + WGS-84→ENU.

    Args:
        data: Parsed log data (may contain 'EKF' key with fused output).
        color_by: 'speed', 'altitude', or 'time'.
    """
    ekf = data.get('EKF')
    source_label = "GPS"

    if ekf and ekf.get('east'):
        east_list = ekf['east']
        north_list = ekf['north']
        up_list = ekf['up']
        speeds = ekf['speed']
        times = ekf['time_s']
        source_label = "EKF-fused"
    else:
        gps_data = data.get('GPS', [])

        if not gps_data:
            fig = go.Figure()
            fig.add_annotation(text="No GPS data available for 3D trajectory")
            return fig

        lat0, lon0, alt0 = None, None, None
        for msg in gps_data:
            lat = msg.get('Lat', 0)
            lon = msg.get('Lng', 0)
            alt = msg.get('Alt', 0)
            if lat != 0 and lon != 0:
                lat0, lon0, alt0 = lat, lon, alt
                break

        if lat0 is None:
            fig = go.Figure()
            fig.add_annotation(text="No valid GPS coordinates for 3D trajectory")
            return fig

        east_list, north_list, up_list, speeds, times = [], [], [], [], []

        for msg in gps_data:
            lat = msg.get('Lat', 0)
            lon = msg.get('Lng', 0)
            alt = msg.get('Alt', 0)
            spd = msg.get('Spd', 0)

            if lat == 0 or lon == 0:
                continue

            e, n, u = wgs84_to_enu(lat, lon, alt, lat0, lon0, alt0)
            east_list.append(e)
            north_list.append(n)
            up_list.append(u)
            speeds.append(spd)
            times.append(msg['TimeS'])

    if not east_list:
        fig = go.Figure()
        fig.add_annotation(text="No trajectory data available")
        return fig

    if color_by == 'speed' and speeds:
        color_vals = speeds
        colorbar_title = "Speed (m/s)"
        colorscale = 'Viridis'
    elif color_by == 'altitude' and up_list:
        color_vals = up_list
        colorbar_title = "Altitude (m)"
        colorscale = 'Viridis'
    else:
        color_vals = times
        colorbar_title = "Time (s)"
        colorscale = 'Plasma'

    c_min = min(color_vals)
    c_max = max(color_vals)
    color_norm = [(v - c_min) / (c_max - c_min + 1e-6) for v in color_vals]

    fig = go.Figure()

    fig.add_trace(go.Scatter3d(
        x=east_list, y=north_list, z=up_list,
        mode='lines',
        line=dict(color=color_norm, colorscale=colorscale, showscale=False, width=4),
        hovertemplate='<b>Position</b><br>E: %{x:.1f}m<br>N: %{y:.1f}m<br>Alt: %{z:.1f}m<extra></extra>',
        name='Trajectory'
    ))

    fig.add_trace(go.Scatter3d(
        x=east_list, y=north_list, z=up_list,
        mode='markers',
        marker=dict(size=3, color=color_norm, colorscale=colorscale,
                    showscale=True, colorbar=dict(title=colorbar_title), line=dict(width=0)),
        hovertemplate='<b>Position</b><br>E: %{x:.1f}m<br>N: %{y:.1f}m<br>Alt: %{z:.1f}m<extra></extra>',
        name='Position'
    ))

    fig.add_trace(go.Scatter3d(
        x=[east_list[0]], y=[north_list[0]], z=[up_list[0]],
        mode='markers',
        marker=dict(size=12, color='green', symbol='diamond'),
        name='Takeoff',
        hovertemplate='<b>Takeoff</b><br>E: %{x:.1f}m<br>N: %{y:.1f}m<br>Alt: %{z:.1f}m<extra></extra>'
    ))

    fig.add_trace(go.Scatter3d(
        x=[east_list[-1]], y=[north_list[-1]], z=[up_list[-1]],
        mode='markers',
        marker=dict(size=12, color='red', symbol='diamond'),
        name='Landing',
        hovertemplate='<b>Landing</b><br>E: %{x:.1f}m<br>N: %{y:.1f}m<br>Alt: %{z:.1f}m<extra></extra>'
    ))

    fig.update_layout(
        title=f"3D Trajectory — {source_label} (colored by {color_by.title()})",
        template="plotly_dark",
        scene=dict(
            xaxis=dict(title='East (m)', backgroundcolor='rgb(10, 10, 10)', gridcolor='rgb(50, 50, 50)'),
            yaxis=dict(title='North (m)', backgroundcolor='rgb(10, 10, 10)', gridcolor='rgb(50, 50, 50)'),
            zaxis=dict(title='Altitude (m)', backgroundcolor='rgb(10, 10, 10)', gridcolor='rgb(50, 50, 50)'),
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.2))
        ),
        height=700,
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=True
    )

    return fig
