"""2D GPS trajectory map chart."""

from typing import Dict

import plotly.graph_objects as go

from core.geo.gps_quality import filter_gps_by_quality
from core.geo.map_view import compute_map_view_from_trajectory


def build_2d_map_panel(data: Dict, color_by: str = 'speed') -> go.Figure:
    """Build an interactive 2D map of the drone's real-world GPS trajectory.

    Args:
        data: Parsed log dict containing 'GPS' records.
        color_by: 'speed', 'altitude', or 'time'.
    """
    gps_data = data.get('GPS', [])

    if not gps_data:
        fig = go.Figure()
        fig.add_annotation(text="No GPS data available for 2D map")
        return fig

    filtered_gps = filter_gps_by_quality(gps_data)

    if len(filtered_gps) < 10:
        fig = go.Figure()
        fig.add_annotation(text=f"Insufficient GPS data: Only {len(filtered_gps)} valid points (need >= 10)")
        return fig

    lats = [msg.get('Lat', 0) for msg in filtered_gps]
    lons = [msg.get('Lng', 0) for msg in filtered_gps]
    alts = [msg.get('Alt', 0) for msg in filtered_gps]
    speeds = [msg.get('Spd', 0) for msg in filtered_gps]
    times = [msg['TimeS'] for msg in filtered_gps]

    time_min = min(times)
    time_max = max(times)
    times_normalized = [(t - time_min) / (time_max - time_min + 1e-6) for t in times]

    if color_by == 'speed':
        color_array = speeds
        colorscale = 'Plasma'
        colorbar_title = "Speed (m/s)"
    elif color_by == 'altitude':
        color_array = alts
        colorscale = 'Viridis'
        colorbar_title = "Altitude (m)"
    else:
        color_array = times_normalized
        colorscale = 'Turbo'
        colorbar_title = "Time (normalized)"

    lat_center, lon_center, zoom = compute_map_view_from_trajectory(lats, lons)

    fig = go.Figure()

    fig.add_trace(go.Scattermap(
        lon=lons, lat=lats,
        mode='lines',
        line=dict(color='rgba(100, 180, 255, 0.5)', width=3),
        hovertemplate='<b>Trajectory</b><br>Lat: %{lat:.6f}<br>Lon: %{lon:.6f}<extra></extra>',
        name='Flight Path',
        showlegend=False
    ))

    hover_times = [f"{int(t // 60):02d}:{int(t % 60):02d}" for t in times]

    fig.add_trace(go.Scattermap(
        lon=lons, lat=lats,
        mode='markers',
        marker=dict(
            size=5, opacity=0.7, color=color_array, colorscale=colorscale,
            showscale=True, colorbar=dict(title=colorbar_title, thickness=15, len=0.7)
        ),
        text=[
            f"<b>Position</b><br>Time: {ts}<br>Speed: {spd:.1f} m/s<br>Alt: {alt:.0f}m<br>Lat: {lat:.6f}<br>Lon: {lon:.6f}"
            for ts, spd, alt, lat, lon in zip(hover_times, speeds, alts, lats, lons)
        ],
        hovertemplate='%{text}<extra></extra>',
        name='Position',
        showlegend=False
    ))

    fig.add_trace(go.Scattermap(
        lon=[lons[0]], lat=[lats[0]],
        mode='markers',
        marker=dict(size=14, color='green', symbol='circle'),
        text=f"<b>Takeoff</b><br>Lat: {lats[0]:.6f}<br>Lon: {lons[0]:.6f}<br>Alt: {alts[0]:.0f}m",
        hovertemplate='%{text}<extra></extra>',
        name='Takeoff',
    ))

    fig.add_trace(go.Scattermap(
        lon=[lons[-1]], lat=[lats[-1]],
        mode='markers',
        marker=dict(size=14, color='red', symbol='circle'),
        text=f"<b>Landing</b><br>Lat: {lats[-1]:.6f}<br>Lon: {lons[-1]:.6f}<br>Alt: {alts[-1]:.0f}m",
        hovertemplate='%{text}<extra></extra>',
        name='Landing',
    ))

    fig.update_layout(
        title="Flight Trajectory — Real World GPS",
        map=dict(
            style="open-street-map",
            center=dict(lat=lat_center, lon=lon_center),
            zoom=zoom,
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        height=600,
        template="plotly_dark",
        hovermode='closest',
        showlegend=True
    )

    return fig
