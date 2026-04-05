"""
UAV Telemetry Analysis & Dashboard
Parses ArduPilot Dataflash binary logs and renders interactive mission analytics.

Usage:
    python drone_dashboard.py flight.bin
    
Dependencies:
    - pymavlink
    - numpy
    - plotly
    - dash
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import math
from datetime import datetime

import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, Input, Output, State
from pymavlink import mavutil

from services.constants import (
    EARTH_RADIUS_M,
    LOW_VOLTAGE_THRESHOLD,
    MAX_HDOP,
    MIN_SATS,
    MOTOR_MAX_PWM,
    MOTOR_MIN_PWM,
    MOTOR_SATURATION_MARGIN,
    MESSAGE_TYPES,
    VIBE_CRITICAL_THRESHOLD,
    VIBE_WARNING_THRESHOLD,
)
from services.geo import haversine, integrate_velocity, wgs84_to_enu
from services.gps_quality import filter_gps_by_quality
from services.map_view_service import compute_map_view_from_trajectory
from services.mission_bounds_service import compute_mission_bounds_stats
from services.gps_track_metrics_service import compute_gps_track_metrics
from services.gyro_extremes_service import compute_gyro_extremes_warning

# ============================================================================
# LOG PARSING
# ============================================================================


def parse_log(filepath: str) -> Dict[str, List[Dict]]:
    """
    Parse an ArduPilot Dataflash binary log file using pymavlink DFReader.
    
    Args:
        filepath: Path to .bin log file
        
    Returns:
        Dictionary mapping message type names to lists of message dicts.
        Each dict contains all fields from the message, plus 'TimeS' (time in seconds).
    """
    print(f"Parsing {filepath}...")
    
    data = {msg_type: [] for msg_type in MESSAGE_TYPES}
    
    try:
        mlog = mavutil.mavlink_connection(filepath, dialect='ardupilotmega')
    except Exception as e:
        print(f"Error opening log file: {e}")
        sys.exit(1)
    
    first_timestamp_us = None
    msg_counts = {msg_type: 0 for msg_type in MESSAGE_TYPES}
    
    while True:
        msg = mlog.recv_match()
        if msg is None:
            break
        
        msg_type = msg.get_type()
        if msg_type not in MESSAGE_TYPES:
            continue
        
        # Extract TimeUS from message
        if not hasattr(msg, 'TimeUS'):
            continue
        
        time_us = msg.TimeUS
        
        # Set first timestamp reference
        if first_timestamp_us is None:
            first_timestamp_us = time_us
        
        # Convert to relative seconds
        time_s = (time_us - first_timestamp_us) / 1_000_000.0
        
        # Create message dict with all fields
        msg_dict = msg.to_dict()
        msg_dict['TimeS'] = time_s
        
        data[msg_type].append(msg_dict)
        msg_counts[msg_type] += 1
    
    # Close the connection to release file handle
    mlog.close()
    
    # Print summary
    print("\nLog Summary:")
    for msg_type in MESSAGE_TYPES:
        if msg_counts[msg_type] > 0:
            print(f"  ✓ {msg_type}: {msg_counts[msg_type]:,} records")
    
    return data


# ============================================================================
# METRICS COMPUTATION
# ============================================================================


def _smooth(values: list, window: int = 5) -> list:
    """Apply simple moving-average smoothing to a list of floats."""
    if len(values) < window:
        return values
    kernel = np.ones(window) / window
    smoothed = np.convolve(values, kernel, mode='same')
    return smoothed.tolist()


def compute_metrics(data: Dict[str, List[Dict]]) -> Dict:
    """
    Compute all mission metrics from parsed log data.

    Args:
        data: Dictionary of message lists from parse_log()

    Returns:
        Dictionary of computed metrics with human-readable keys
    """
    metrics = {}

    GRAVITY_MS2 = 9.80665  # standard gravity (m/s²)

    # ---- Source data ----
    gps_data = data.get('GPS', [])
    imu_data = data.get('IMU', [])
    bat_data = data.get('BAT', [])

    # ---- Quality-filtered GPS subset (HDop / NSats) ----
    filtered_gps = [
        msg for msg in gps_data
        if msg.get('HDop', 999) < MAX_HDOP and msg.get('NSats', 0) >= MIN_SATS
    ]

    # ---- Flight Duration ----
    if gps_data:
        duration_s = gps_data[-1]['TimeS'] - gps_data[0]['TimeS']
        metrics['duration_s'] = duration_s
        minutes, seconds = divmod(int(duration_s), 60)
        metrics['duration_str'] = f"{minutes}:{seconds:02d}"
    else:
        metrics['duration_s'] = 0
        metrics['duration_str'] = "N/A"

    # ---- Distance Traveled (Haversine) — quality-filtered ----
    if len(filtered_gps) > 1:
        total_distance_m = 0.0
        for i in range(1, len(filtered_gps)):
            lat1 = filtered_gps[i - 1].get('Lat', 0)
            lon1 = filtered_gps[i - 1].get('Lng', 0)
            lat2 = filtered_gps[i].get('Lat', 0)
            lon2 = filtered_gps[i].get('Lng', 0)

            if lat1 != 0 and lon1 != 0 and lat2 != 0 and lon2 != 0:
                total_distance_m += haversine(lat1, lon1, lat2, lon2)

        metrics['distance_m'] = total_distance_m
        metrics['distance_km'] = total_distance_m / 1000.0
    else:
        metrics['distance_m'] = 0.0
        metrics['distance_km'] = 0.0

    # ---- Max Horizontal Speed (GPS ground speed, m/s) ----
    if filtered_gps:
        h_speeds = [msg.get('Spd', 0) for msg in filtered_gps]
        max_h_speed = max(h_speeds)
        metrics['max_h_speed_ms'] = max_h_speed
        metrics['max_h_speed_kmh'] = max_h_speed * 3.6
    else:
        metrics['max_h_speed_ms'] = 0.0
        metrics['max_h_speed_kmh'] = 0.0

    # ---- Vertical Speed — taken directly from GPS VZ field ----
    # VZ is the GPS-reported vertical velocity (m/s, positive = down in NED).
    # Using dAlt/dt caused a boundary artifact: np.convolve(mode='same') pads
    # with zeros, so smoothed altitude near t=0 jumps from 0 to the actual MSL
    # altitude (~584 m), giving a fake dAlt/dt ≈ 584 m/s = 2102 km/h.
    if filtered_gps:
        vz_values = [abs(msg.get('VZ', 0)) for msg in filtered_gps]
        max_v_speed = max(vz_values) if vz_values else 0.0
        metrics['max_v_speed_ms'] = max_v_speed
        metrics['max_v_speed_kmh'] = max_v_speed * 3.6
    else:
        metrics['max_v_speed_ms'] = 0.0
        metrics['max_v_speed_kmh'] = 0.0

    # ---- Max Total (3D) Speed = sqrt(Vh² + Vv²) ----
    if filtered_gps:
        max_total_speed = 0.0
        for msg in filtered_gps:
            h_speed = msg.get('Spd', 0)
            v_speed = abs(msg.get('VZ', 0))
            total_speed = math.sqrt(h_speed ** 2 + v_speed ** 2)
            max_total_speed = max(max_total_speed, total_speed)
        metrics['max_total_speed_ms'] = max_total_speed
        metrics['max_total_speed_kmh'] = max_total_speed * 3.6
    else:
        metrics['max_total_speed_ms'] = 0.0
        metrics['max_total_speed_kmh'] = 0.0

    # ---- Max Altitude Gain ----
    if filtered_gps:
        alts = [msg.get('Alt', 0) for msg in filtered_gps]
        metrics['max_alt_m'] = max(alts)
        metrics['min_alt_m'] = min(alts)
        metrics['alt_gain_m'] = metrics['max_alt_m'] - metrics['min_alt_m']
    else:
        metrics['max_alt_m'] = 0.0
        metrics['min_alt_m'] = 0.0
        metrics['alt_gain_m'] = 0.0

    # ---- Max Acceleration (gravity-compensated) ----
    # IMU AccX/AccY/AccZ include gravity (~9.81 m/s² on Z at rest).
    # We subtract 1 g from the total magnitude so the metric reflects
    # only the dynamic (manoeuvre) acceleration the airframe experiences.
    if imu_data:
        max_accel = 0.0
        for msg in imu_data:
            ax = msg.get('AccX', 0)
            ay = msg.get('AccY', 0)
            az = msg.get('AccZ', 0)
            accel_mag = math.sqrt(ax ** 2 + ay ** 2 + az ** 2)
            dynamic_accel = abs(accel_mag - GRAVITY_MS2)
            max_accel = max(max_accel, dynamic_accel)

        metrics['max_accel_ms2'] = max_accel
    else:
        metrics['max_accel_ms2'] = 0.0

    # ---- IMU-derived velocity via trapezoidal integration ----
    if len(imu_data) > 1:
        imu_times = np.array([msg['TimeS'] for msg in imu_data])
        acc_x = np.array([msg.get('AccX', 0) for msg in imu_data])
        acc_y = np.array([msg.get('AccY', 0) for msg in imu_data])
        # Subtract gravity from Z axis (sensor frame, Z points down in NED)
        acc_z = np.array([msg.get('AccZ', 0) for msg in imu_data]) + GRAVITY_MS2

        vel_x = integrate_velocity(acc_x, imu_times)
        vel_y = integrate_velocity(acc_y, imu_times)
        vel_z = integrate_velocity(acc_z, imu_times)

        imu_speed = np.sqrt(vel_x ** 2 + vel_y ** 2 + vel_z ** 2)
        metrics['max_imu_speed_ms'] = float(np.max(imu_speed))
    else:
        metrics['max_imu_speed_ms'] = 0.0

    # ---- Average GPS Satellites ----
    if filtered_gps:
        sats = [msg.get('NSats', 0) for msg in filtered_gps]
        metrics['avg_sats'] = float(np.mean(sats))
    else:
        metrics['avg_sats'] = 0.0

    # ---- Average Hover Current / Energy ----
    if bat_data:
        currents = [msg.get('Curr', 0) for msg in bat_data]
        metrics['avg_current_a'] = float(np.mean(currents)) if currents else 0.0

        curr_tots = [msg.get('CurrTot', 0) for msg in bat_data]
        metrics['energy_used_mah'] = curr_tots[-1] if curr_tots else 0.0
    else:
        metrics['avg_current_a'] = 0.0
        metrics['energy_used_mah'] = 0.0

    # ---- EKF-fused metrics (if available) ----
    ekf = data.get('EKF')
    if ekf and ekf.get('speed'):
        metrics['ekf_max_speed_ms'] = max(ekf['speed'])
        metrics['ekf_max_speed_kmh'] = metrics['ekf_max_speed_ms'] * 3.6
        metrics['ekf_max_h_speed_ms'] = max(ekf['h_speed'])
        metrics['ekf_max_h_speed_kmh'] = metrics['ekf_max_h_speed_ms'] * 3.6
        metrics['ekf_max_v_speed_ms'] = max(ekf['v_speed'])
        metrics['ekf_max_v_speed_kmh'] = metrics['ekf_max_v_speed_ms'] * 3.6
        metrics['ekf_available'] = True
        metrics['ekf_board_rotation'] = ekf.get('board_rotation_applied', False)
    else:
        metrics['ekf_available'] = False

    # ---- Warning-only metadata from dev1 services (no metric overrides) ----
    track_warnings = compute_gps_track_metrics(filtered_gps if filtered_gps else gps_data)
    metrics['distance_warning'] = track_warnings.get('distance_warning')
    metrics['alt_gain_warning'] = track_warnings.get('alt_gain_warning')
    metrics['battery_warning'] = (
        "No battery telemetry (BAT) in this log; energy and current are unavailable."
        if not bat_data
        else None
    )
    metrics['gyro_extremes_warning'] = compute_gyro_extremes_warning(imu_data)
    metrics['speed_warning'] = None

    return metrics


# DASHBOARD PANELS
# ============================================================================


def build_summary_panel(metrics: Dict, data: Dict) -> go.Figure:
    """
    Create a summary info panel with mission metrics and flight mode timeline.
    
    Args:
        metrics: Dictionary from compute_metrics()
        data: Raw parsed log data
        
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    
    # Build mode timeline if MODE data exists
    mode_data = data.get('MODE', [])
    mode_times = []
    mode_colors = []
    mode_names = []
    mode_color_map = {
        0: 'red', 1: 'orange', 2: 'yellow', 3: 'lime', 4: 'cyan', 5: 'blue',
        6: 'purple', 7: 'pink', 8: 'gray', 9: 'brown', 10: 'magenta'
    }
    
    for i, mode_msg in enumerate(mode_data):
        mode_num = mode_msg.get('ModeNum', -1)
        time_s = mode_msg['TimeS']
        mode_times.append(time_s)
        mode_colors.append(mode_color_map.get(mode_num, 'gray'))
        mode_names.append(f"Mode {mode_num}")
    
    # Create summary table
    summary_data = [
        ["Duration", metrics.get('duration_str', 'N/A')],
        ["Distance", f"{metrics.get('distance_km', 0):.2f} km"],
        ["Max Total Speed", f"{metrics.get('max_total_speed_ms', 0):.1f} m/s ({metrics.get('max_total_speed_kmh', 0):.1f} km/h)"],
        ["Max H. Speed", f"{metrics.get('max_h_speed_ms', 0):.1f} m/s ({metrics.get('max_h_speed_kmh', 0):.1f} km/h)"],
        ["Max V. Speed", f"{metrics.get('max_v_speed_ms', 0):.1f} m/s ({metrics.get('max_v_speed_kmh', 0):.1f} km/h)"],
        ["Max Altitude Gain", f"{metrics.get('alt_gain_m', 0):.1f} m"],
        ["Max Acceleration", f"{metrics.get('max_accel_ms2', 0):.2f} m/s² (gravity-compensated)"],
        ["IMU-derived Speed", f"{metrics.get('max_imu_speed_ms', 0):.1f} m/s (trapezoidal integration)"],
        ["Avg GPS Satellites", f"{metrics.get('avg_sats', 0):.0f}"],
        ["Avg Current", f"{metrics.get('avg_current_a', 0):.1f} A"],
        ["Total Energy", f"{metrics.get('energy_used_mah', 0):.0f} mAh"],
    ]
    
    fig.add_trace(go.Table(
        header=dict(
            values=['<b>Parameter</b>', '<b>Value</b>'],
            fill_color='#1f77b4',
            align='left',
            font=dict(color='white', size=12)
        ),
        cells=dict(
            values=list(zip(*summary_data)),
            fill_color='#111111',
            align='left',
            font=dict(color='white', size=11),
            height=25
        )
    ))
    
    fig.update_layout(
        title="Mission Summary",
        template="plotly_dark",
        height=500,
        margin=dict(l=10, r=10, t=40, b=10)
    )
    
    return fig


def build_battery_panel(data: Dict) -> go.Figure:
    """
    Create a dual-axis battery health chart (voltage left, current right).
    
    Args:
        data: Raw parsed log data
        
    Returns:
        Plotly Figure object
    """
    bat_data = data.get('BAT', [])
    
    if not bat_data:
        fig = go.Figure()
        fig.add_annotation(text="No battery data available")
        return fig
    
    times = [msg['TimeS'] for msg in bat_data]
    volts = [msg.get('Volt', 0) for msg in bat_data]
    currents = [msg.get('Curr', 0) for msg in bat_data]
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Voltage trace (left axis)
    fig.add_trace(
        go.Scatter(x=times, y=volts, name='Voltage',
                   line=dict(color='red', width=2),
                   hovertemplate='<b>Voltage</b><br>Time: %{x:.1f}s<br>V: %{y:.2f}V<extra></extra>'),
        secondary_y=False
    )
    
    # Current trace (right axis)
    fig.add_trace(
        go.Scatter(x=times, y=currents, name='Current',
                   line=dict(color='cyan', width=2),
                   hovertemplate='<b>Current</b><br>Time: %{x:.1f}s<br>A: %{y:.1f}A<extra></extra>'),
        secondary_y=True
    )
    
    # Add low voltage threshold line
    low_volt_cells = LOW_VOLTAGE_THRESHOLD * 4  # Assuming 4S battery (adjust as needed)
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


def build_vibration_motor_panel(data: Dict) -> go.Figure:
    """
    Create a split panel showing vibration (top) and motor outputs (bottom).
    
    Args:
        data: Raw parsed log data
        
    Returns:
        Plotly Figure object
    """
    vibe_data = data.get('VIBE', [])
    rcou_data = data.get('RCOU', [])
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("Vibration Levels", "Motor Outputs"),
        vertical_spacing=0.15
    )
    
    # ---- Vibration Panel ----
    if vibe_data:
        times = [msg['TimeS'] for msg in vibe_data]
        vibe_x = [msg.get('VibeX', 0) for msg in vibe_data]
        vibe_y = [msg.get('VibeY', 0) for msg in vibe_data]
        vibe_z = [msg.get('VibeZ', 0) for msg in vibe_data]
        
        # Add shaded zones for vibration levels
        y_max = max(max(vibe_x), max(vibe_y), max(vibe_z), VIBE_CRITICAL_THRESHOLD) * 1.1
        
        fig.add_hrect(y0=VIBE_CRITICAL_THRESHOLD, y1=y_max,
                      fillcolor="red", opacity=0.1, line_width=0,
                      row=1, col=1, annotation_text="CRITICAL")
        fig.add_hrect(y0=VIBE_WARNING_THRESHOLD, y1=VIBE_CRITICAL_THRESHOLD,
                      fillcolor="orange", opacity=0.1, line_width=0,
                      row=1, col=1, annotation_text="WARNING")
        
        # Reference lines
        fig.add_hline(y=VIBE_WARNING_THRESHOLD, line_dash="dash", line_color="orange",
                      row=1, col=1)
        fig.add_hline(y=VIBE_CRITICAL_THRESHOLD, line_dash="dash", line_color="red",
                      row=1, col=1)
        
        # Vibration traces
        fig.add_trace(
            go.Scatter(x=times, y=vibe_x, name='VibeX', line=dict(color='red'),
                       hovertemplate='<b>VibeX</b><br>%{x:.1f}s: %{y:.1f} m/s²<extra></extra>'),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=times, y=vibe_y, name='VibeY', line=dict(color='green'),
                       hovertemplate='<b>VibeY</b><br>%{x:.1f}s: %{y:.1f} m/s²<extra></extra>'),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=times, y=vibe_z, name='VibeZ', line=dict(color='blue'),
                       hovertemplate='<b>VibeZ</b><br>%{x:.1f}s: %{y:.1f} m/s²<extra></extra>'),
            row=1, col=1
        )
    else:
        fig.add_annotation(text="No vibration data", row=1, col=1)
    
    # ---- Motor Outputs Panel ----
    if rcou_data:
        times = [msg['TimeS'] for msg in rcou_data]
        c1 = [msg.get('C1', 0) for msg in rcou_data]
        c2 = [msg.get('C2', 0) for msg in rcou_data]
        c3 = [msg.get('C3', 0) for msg in rcou_data]
        c4 = [msg.get('C4', 0) for msg in rcou_data]
        
        # Add saturation zone (top 1%)
        fig.add_hrect(y0=MOTOR_MAX_PWM - MOTOR_SATURATION_MARGIN, y1=MOTOR_MAX_PWM,
                      fillcolor="red", opacity=0.1, line_width=0, row=2, col=1)
        fig.add_hrect(y0=MOTOR_MIN_PWM, y1=MOTOR_MIN_PWM + MOTOR_SATURATION_MARGIN,
                      fillcolor="red", opacity=0.1, line_width=0, row=2, col=1)
        
        fig.add_trace(
            go.Scatter(x=times, y=c1, name='M1', line=dict(color='red'),
                       hovertemplate='<b>Motor 1</b><br>%{x:.1f}s: %{y:.0f} µs<extra></extra>'),
            row=2, col=1
        )
        fig.add_trace(
            go.Scatter(x=times, y=c2, name='M2', line=dict(color='green'),
                       hovertemplate='<b>Motor 2</b><br>%{x:.1f}s: %{y:.0f} µs<extra></extra>'),
            row=2, col=1
        )
        fig.add_trace(
            go.Scatter(x=times, y=c3, name='M3', line=dict(color='blue'),
                       hovertemplate='<b>Motor 3</b><br>%{x:.1f}s: %{y:.0f} µs<extra></extra>'),
            row=2, col=1
        )
        fig.add_trace(
            go.Scatter(x=times, y=c4, name='M4', line=dict(color='yellow'),
                       hovertemplate='<b>Motor 4</b><br>%{x:.1f}s: %{y:.0f} µs<extra></extra>'),
            row=2, col=1
        )
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


def build_attitude_panel(data: Dict) -> go.Figure:
    """
    Create an overlay plot of actual vs desired attitude (roll, pitch, yaw).
    
    Args:
        data: Raw parsed log data
        
    Returns:
        Plotly Figure object
    """
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
    
    # Roll
    fig.add_trace(go.Scatter(x=times, y=roll, name='Roll (actual)',
                            line=dict(color='blue', width=2)))
    fig.add_trace(go.Scatter(x=times, y=des_roll, name='Roll (desired)',
                            line=dict(color='blue', width=1, dash='dash')))
    
    # Pitch
    fig.add_trace(go.Scatter(x=times, y=pitch, name='Pitch (actual)',
                            line=dict(color='orange', width=2)))
    fig.add_trace(go.Scatter(x=times, y=des_pitch, name='Pitch (desired)',
                            line=dict(color='orange', width=1, dash='dash')))
    
    # Yaw
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


def build_gps_panel(data: Dict) -> go.Figure:
    """
    Create a GPS health panel with satellite count, HDOP, and altitude profile.
    
    Args:
        data: Raw parsed log data
        
    Returns:
        Plotly Figure object
    """
    gps_data = data.get('GPS', [])
    
    if not gps_data:
        fig = go.Figure()
        fig.add_annotation(text="No GPS data available")
        return fig
    
    times = [msg['TimeS'] for msg in gps_data]
    nsats = [msg.get('NSats', 0) for msg in gps_data]
    hdop = [msg.get('HDop', 999) for msg in gps_data]
    alts = [msg.get('Alt', 0) for msg in gps_data]
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Satellite count (left)
    fig.add_trace(
        go.Scatter(x=times, y=nsats, name='Satellites',
                   marker=dict(color='lime', size=4),
                   hovertemplate='<b>NSats</b><br>%{x:.1f}s: %{y:.0f}<extra></extra>'),
        secondary_y=False
    )
    
    # HDOP (right, inverted scale — lower is better)
    fig.add_trace(
        go.Scatter(x=times, y=hdop, name='HDOP',
                   line=dict(color='orange', width=2),
                   hovertemplate='<b>HDOP</b><br>%{x:.1f}s: %{y:.1f}<extra></extra>'),
        secondary_y=True
    )
    
    # Altitude trace (bar chart on left axis)
    fig.add_trace(
        go.Bar(x=times, y=alts, name='Altitude', opacity=0.4,
               marker=dict(color='cyan'),
               hovertemplate='<b>Alt</b><br>%{x:.1f}s: %{y:.0f}m<extra></extra>'),
        secondary_y=False
    )
    
    fig.update_xaxes(title_text="Time (s)")
    fig.update_yaxes(title_text="Satellites / Altitude (m)", secondary_y=False)
    fig.update_yaxes(title_text="HDOP", secondary_y=True)
    
    fig.update_layout(
        title="GPS Health",
        template="plotly_dark",
        hovermode='x unified',
        height=400,
        margin=dict(l=10, r=10, t=40, b=40)
    )
    
    return fig


def build_events_panel(data: Dict) -> go.Figure:
    """
    Create a timeline scatter plot of errors and events.
    
    Args:
        data: Raw parsed log data
        
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    
    # Extract error messages
    err_data = data.get('ERR', [])
    mode_data = data.get('MODE', [])
    ev_data = data.get('EV', [])
    
    # Color maps for event types
    error_colors = {}
    mode_colors_map = {
        0: 'red', 1: 'orange', 2: 'yellow', 3: 'lime', 4: 'cyan', 5: 'blue',
        6: 'purple', 7: 'pink'
    }
    
    # Add errors
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
    
    # Add mode changes
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
    
    # Add events
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


def build_3d_trajectory(data: Dict, color_by: str = 'speed') -> go.Figure:
    """
    Create an interactive 3D trajectory viewer with optional coloring.
    Uses EKF-fused trajectory when available, falls back to raw GPS + WGS-84→ENU.

    Args:
        data: Raw parsed log data (may contain 'EKF' key with fused output)
        color_by: 'speed', 'altitude', or 'time' — how to color the trajectory

    Returns:
        Plotly Figure object
    """
    ekf = data.get('EKF')
    source_label = "GPS"

    if ekf and ekf.get('east'):
        # Use EKF-fused trajectory (NED → ENU for display)
        east_list = ekf['east']
        north_list = ekf['north']
        up_list = ekf['up']
        speeds = ekf['speed']
        times = ekf['time_s']
        source_label = "EKF-fused"
    else:
        # Fallback: raw GPS → ENU via flat-Earth
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

        east_list = []
        north_list = []
        up_list = []
        speeds = []
        times = []

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
    # Determine color scale
    if color_by == 'speed' and speeds:
        color_scale_vals = speeds
        colorbar_title = "Speed (m/s)"
        colorscale = 'Viridis'
    elif color_by == 'altitude' and up_list:
        color_scale_vals = up_list
        colorbar_title = "Altitude (m)"
        colorscale = 'Viridis'
    else:  # color by time
        color_scale_vals = times
        colorbar_title = "Time (s)"
        colorscale = 'Plasma'

    # Normalize color values to [0, 1]
    color_min = min(color_scale_vals)
    color_max = max(color_scale_vals)
    color_norm = [(v - color_min) / (color_max - color_min + 1e-6) for v in color_scale_vals]

    fig = go.Figure()

    # Main trajectory line
    fig.add_trace(go.Scatter3d(
        x=east_list, y=north_list, z=up_list,
        mode='lines',
        line=dict(
            color=color_norm,
            colorscale=colorscale,
            showscale=False,
            width=4
        ),
        hovertemplate='<b>Position</b><br>E: %{x:.1f}m<br>N: %{y:.1f}m<br>Alt: %{z:.1f}m<extra></extra>',
        name='Trajectory'
    ))

    # Scatter points for trajectory (with colorbar)
    fig.add_trace(go.Scatter3d(
        x=east_list, y=north_list, z=up_list,
        mode='markers',
        marker=dict(
            size=3,
            color=color_norm,
            colorscale=colorscale,
            showscale=True,
            colorbar=dict(title=colorbar_title),
            line=dict(width=0)
        ),
        hovertemplate='<b>Position</b><br>E: %{x:.1f}m<br>N: %{y:.1f}m<br>Alt: %{z:.1f}m<extra></extra>',
        name='Position'
    ))

    # Start marker (green diamond)
    fig.add_trace(go.Scatter3d(
        x=[east_list[0]], y=[north_list[0]], z=[up_list[0]],
        mode='markers',
        marker=dict(size=12, color='green', symbol='diamond'),
        name='Takeoff',
        hovertemplate='<b>Takeoff</b><br>E: %{x:.1f}m<br>N: %{y:.1f}m<br>Alt: %{z:.1f}m<extra></extra>'
    ))

    # End marker (red diamond)
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
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.2)
            )
        ),
        height=700,
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=True
    )

    return fig


def build_2d_map_panel(data: Dict, color_by: str = 'speed') -> go.Figure:
    """
    Builds an interactive 2D map of the drone's real-world GPS trajectory.
    
    Filters GPS records for quality (HDop < MAX_HDOP, NSats >= MIN_SATS)
    and renders trajectory with dynamic coloring.
    
    Args:
        data: parsed log dict containing 'GPS' records
        color_by: 'speed', 'altitude', or 'time'
        
    Returns:
        A Plotly Figure using Scattermap with trajectory, start/end markers, and dynamic coloring.
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
    
    # Extract parallel arrays
    lats = [msg.get('Lat', 0) for msg in filtered_gps]
    lons = [msg.get('Lng', 0) for msg in filtered_gps]
    alts = [msg.get('Alt', 0) for msg in filtered_gps]
    speeds = [msg.get('Spd', 0) for msg in filtered_gps]
    times = [msg['TimeS'] for msg in filtered_gps]
    
    # Normalize times to [0, 1]
    time_min = min(times)
    time_max = max(times)
    times_normalized = [(t - time_min) / (time_max - time_min + 1e-6) for t in times]
    
    # Determine color array based on color_by parameter
    if color_by == 'speed':
        color_array = speeds
        colorscale = 'Plasma'
        colorbar_title = "Speed (m/s)"
    elif color_by == 'altitude':
        color_array = alts
        colorscale = 'Viridis'
        colorbar_title = "Altitude (m)"
    else:  # 'time'
        color_array = times_normalized
        colorscale = 'Turbo'
        colorbar_title = "Time (normalized)"
    
    # Frame takeoff → full trajectory → landing, plus MAP_TRAJECTORY_PADDING_FRAC of span per side
    lat_center, lon_center, zoom = compute_map_view_from_trajectory(lats, lons)
    
    fig = go.Figure()
    
    # Layer 1: Trajectory line (solid color, no per-point coloring for Scattermap)
    fig.add_trace(go.Scattermap(
        lon=lons, lat=lats,
        mode='lines',
        line=dict(
            color='rgba(100, 180, 255, 0.5)',
            width=3
        ),
        hovertemplate='<b>Trajectory</b><br>Lat: %{lat:.6f}<br>Lon: %{lon:.6f}<extra></extra>',
        name='Flight Path',
        showlegend=False
    ))
    
    # Layer 2: Trajectory points with dynamic coloring and colorbar
    hover_times_formatted = [
        f"{int(t // 60):02d}:{int(t % 60):02d}"
        for t in times
    ]
    
    fig.add_trace(go.Scattermap(
        lon=lons, lat=lats,
        mode='markers',
        marker=dict(
            size=5,
            opacity=0.7,
            color=color_array,
            colorscale=colorscale,
            showscale=True,
            colorbar=dict(
                title=colorbar_title,
                thickness=15,
                len=0.7
            )
        ),
        text=[
            f"<b>Position</b><br>Time: {time_str}<br>Speed: {spd:.1f} m/s<br>Alt: {alt:.0f}m<br>Lat: {lat:.6f}<br>Lon: {lon:.6f}"
            for time_str, spd, alt, lat, lon in zip(hover_times_formatted, speeds, alts, lats, lons)
        ],
        hovertemplate='%{text}<extra></extra>',
        name='Position',
        showlegend=False
    ))
    
    # Layer 3: Start marker (green)
    fig.add_trace(go.Scattermap(
        lon=[lons[0]], lat=[lats[0]],
        mode='markers',
        marker=dict(
            size=14,
            color='green',
            symbol='circle'
        ),
        text=f"<b>Takeoff</b><br>Lat: {lats[0]:.6f}<br>Lon: {lons[0]:.6f}<br>Alt: {alts[0]:.0f}m",
        hovertemplate='%{text}<extra></extra>',
        name='Takeoff',
        showlegend=True
    ))
    
    # Layer 4: End marker (red)
    fig.add_trace(go.Scattermap(
        lon=[lons[-1]], lat=[lats[-1]],
        mode='markers',
        marker=dict(
            size=14,
            color='red',
            symbol='circle'
        ),
        text=f"<b>Landing</b><br>Lat: {lats[-1]:.6f}<br>Lon: {lons[-1]:.6f}<br>Alt: {alts[-1]:.0f}m",
        hovertemplate='%{text}<extra></extra>',
        name='Landing',
        showlegend=True
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


def build_mission_bounds_info(data: Dict) -> html.Div:
    """
    Build a styled info box showing mission geographical bounds and GPS quality stats.
    
    Args:
        data: parsed log dict containing 'GPS' records
        
    Returns:
        A Dash html.Div component with mission statistics
    """
    gps_data = data.get('GPS', [])
    stats = compute_mission_bounds_stats(gps_data)
    
    if stats is None:
        return html.Div([
            html.P("No valid GPS data available")
        ], style={'padding': '20px', 'color': '#666'})
    
    takeoff_loc = stats.takeoff_loc
    landing_loc = stats.landing_loc
    bounds_box = stats.bounds_box
    num_valid = stats.num_valid
    num_total = stats.num_total
    avg_hdop = stats.avg_hdop
    avg_sats = stats.avg_sats
    
    stats_table = html.Table([
        html.Tr([html.Th("Field", style={'textAlign': 'left', 'padding': '8px', 'borderBottom': '1px solid #444'}),
                 html.Th("Value", style={'textAlign': 'left', 'padding': '8px', 'borderBottom': '1px solid #444'})]),
        html.Tr([html.Td("Takeoff Location", style={'padding': '8px', 'borderBottom': '1px solid #222'}),
                 html.Td(takeoff_loc, style={'padding': '8px', 'borderBottom': '1px solid #222'})]),
        html.Tr([html.Td("Landing Location", style={'padding': '8px', 'borderBottom': '1px solid #222'}),
                 html.Td(landing_loc, style={'padding': '8px', 'borderBottom': '1px solid #222'})]),
        html.Tr([html.Td("Bounding Box", style={'padding': '8px', 'borderBottom': '1px solid #222'}),
                 html.Td(bounds_box, style={'padding': '8px', 'borderBottom': '1px solid #222'})]),
        html.Tr([html.Td("GPS Points (valid)", style={'padding': '8px', 'borderBottom': '1px solid #222'}),
                 html.Td(f"{num_valid} / {num_total} total", style={'padding': '8px', 'borderBottom': '1px solid #222'})]),
        html.Tr([html.Td("GPS Quality", style={'padding': '8px'}),
                 html.Td(f"Avg HDOP: {avg_hdop:.2f}, Avg Sats: {avg_sats:.0f}", style={'padding': '8px'})]),
    ], style={
        'width': '100%',
        'borderCollapse': 'collapse',
        'color': '#ddd',
        'fontSize': '14px'
    })
    
    return html.Div([
        html.H3("Mission Bounds Information", style={'marginBottom': '15px', 'color': '#fff'}),
        stats_table
    ], style={
        'backgroundColor': '#1a1a1a',
        'border': '1px solid #333',
        'borderRadius': '5px',
        'padding': '20px',
        'marginTop': '20px',
        'marginBottom': '20px'
    })


# ============================================================================
# DASH APPLICATION
# ============================================================================


def create_app(data: Dict, metrics: Dict) -> dash.Dash:
    """
    Create a Dash application with all dashboard panels.
    
    Args:
        data: Raw parsed log data
        metrics: Computed metrics dictionary
        
    Returns:
        Dash app instance
    """
    app = dash.Dash(__name__)
    
    # Build all panels
    summary_fig = build_summary_panel(metrics, data)
    battery_fig = build_battery_panel(data)
    vibration_fig = build_vibration_motor_panel(data)
    attitude_fig = build_attitude_panel(data)
    gps_fig = build_gps_panel(data)
    events_fig = build_events_panel(data)
    trajectory_fig_speed = build_3d_trajectory(data, color_by='speed')
    trajectory_fig_time = build_3d_trajectory(data, color_by='time')
    map_fig = build_2d_map_panel(data, color_by='speed')
    mission_bounds_info = build_mission_bounds_info(data)
    
    app.layout = html.Div(
        style={'backgroundColor': '#111111', 'color': 'white', 'fontFamily': 'Arial'},
        children=[
            html.H1("UAV Mission Analysis Dashboard", style={'textAlign': 'center', 'padding': '20px'}),
            
            # Row 1: Summary
            html.Div([
                dcc.Graph(figure=summary_fig, config={'responsive': True})
            ], style={'width': '100%', 'padding': '10px'}),
            
            # Row 2: Battery
            html.Div([
                dcc.Graph(figure=battery_fig, config={'responsive': True})
            ], style={'width': '100%', 'padding': '10px'}),
            
            # Row 3: Vibration & Motors
            html.Div([
                dcc.Graph(figure=vibration_fig, config={'responsive': True})
            ], style={'width': '100%', 'padding': '10px'}),
            
            # Row 4: Attitude
            html.Div([
                dcc.Graph(figure=attitude_fig, config={'responsive': True})
            ], style={'width': '100%', 'padding': '10px'}),
            
            # Row 5: GPS Health
            html.Div([
                dcc.Graph(figure=gps_fig, config={'responsive': True})
            ], style={'width': '100%', 'padding': '10px'}),
            
            # Row 6: Events Timeline
            html.Div([
                dcc.Graph(figure=events_fig, config={'responsive': True})
            ], style={'width': '100%', 'padding': '10px'}),
            
            # Row 7: 2D Map with dropdown selector
            html.Div([
                html.Div([
                    html.Label("Color by:", style={'marginRight': '10px', 'display': 'inline-block'}),
                    dcc.Dropdown(
                        id='map-color-dropdown',
                        options=[
                            {'label': 'Speed (m/s)', 'value': 'speed'},
                            {'label': 'Altitude (m)', 'value': 'altitude'},
                            {'label': 'Time (normalized)', 'value': 'time'},
                        ],
                        value='speed',
                        style={
                            'width': '200px',
                            'display': 'inline-block',
                            'backgroundColor': '#222',
                            'color': 'white',
                            'borderRadius': '4px'
                        },
                        clearable=False
                    )
                ], style={'padding': '10px', 'backgroundColor': '#1a1a1a', 'marginBottom': '10px'}),
                dcc.Graph(id='map-panel', figure=map_fig, config={'responsive': True})
            ], style={'width': '100%', 'padding': '10px'}),
            
            # Row 8: Mission Bounds Information
            html.Div([
                mission_bounds_info
            ], style={'width': '100%', 'padding': '10px'}),
            
            # Row 9: 3D Trajectory (tabs for different color modes)
            html.Div([
                dcc.Tabs(id='trajectory-tabs', value='speed', children=[
                    dcc.Tab(label='3D Trajectory (by Speed)', value='speed', children=[
                        dcc.Graph(figure=trajectory_fig_speed, config={'responsive': True})
                    ]),
                    dcc.Tab(label='3D Trajectory (by Time)', value='time', children=[
                        dcc.Graph(figure=trajectory_fig_time, config={'responsive': True})
                    ]),
                ])
            ], style={'width': '100%', 'padding': '10px'}),
        ]
    )
    
    # Callback for map color-by selector
    @app.callback(
        Output('map-panel', 'figure'),
        Input('map-color-dropdown', 'value')
    )
    def update_map(color_by: str) -> go.Figure:
        """Update map coloring when dropdown changes."""
        return build_2d_map_panel(data, color_by=color_by)
    
    return app


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================


def main():
    """
    Main entry point: parse CLI arguments, load log, compute metrics, and launch dashboard.
    """
    parser = argparse.ArgumentParser(
        description="UAV Telemetry Analysis & Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python drone_dashboard.py flight.bin
  python drone_dashboard.py flight.bin --export dashboard.html
        """
    )
    parser.add_argument('logfile', help='Path to ArduPilot Dataflash .bin log file')
    parser.add_argument('--export', type=str, default=None,
                       help='Export to HTML file instead of launching Dash server')
    parser.add_argument('--port', type=int, default=8050,
                       help='Port for Dash server (default: 8050)')
    
    args = parser.parse_args()
    
    # Validate input file
    log_path = Path(args.logfile)
    if not log_path.exists():
        print(f"Error: Log file '{args.logfile}' not found")
        sys.exit(1)
    
    # Parse log
    data = parse_log(str(log_path))
    
    # Compute metrics
    metrics = compute_metrics(data)
    
    # Print mission summary
    print("\n" + "=" * 60)
    print("MISSION SUMMARY")
    print("=" * 60)
    print(f"Duration:          {metrics.get('duration_str', 'N/A')}")
    print(f"Distance:          {metrics.get('distance_m', 0):.0f} m")
    print(f"Max H. Speed:      {metrics.get('max_h_speed_ms', 0):.1f} m/s")
    print(f"Max V. Speed:      {metrics.get('max_v_speed_ms', 0):.1f} m/s")
    print(f"Max Altitude Gain: {metrics.get('alt_gain_m', 0):.1f} m")
    print(f"Max Acceleration:  {metrics.get('max_accel_ms2', 0):.2f} m/s²")
    print(f"Avg Current:       {metrics.get('avg_current_a', 0):.1f} A")
    print(f"Energy Used:       {metrics.get('energy_used_mah', 0):.0f} mAh")
    print("=" * 60 + "\n")
    
    # Create Dash app
    app = create_app(data, metrics)
    
    # Export or launch
    if args.export:
        print(f"Exporting dashboard to {args.export}...")
        # Build combined HTML by exporting each figure
        import plotly.io as pio
        
        html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>UAV Mission Analysis Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body { background-color: #111111; color: white; font-family: Arial, sans-serif; margin: 0; padding: 20px; }
        h1 { text-align: center; margin-bottom: 30px; }
        .chart-container { background-color: #222222; margin: 20px 0; padding: 10px; border-radius: 5px; }
        .info-container { background-color: #1a1a1a; border: 1px solid #333; border-radius: 5px; padding: 20px; margin: 20px 0; }
        table { width: 100%; border-collapse: collapse; color: #ddd; font-size: 14px; }
        table th, table td { text-align: left; padding: 8px; border-bottom: 1px solid #444; }
        table th { border-bottom: 1px solid #666; }
    </style>
</head>
<body>
    <h1>UAV Mission Analysis Dashboard</h1>
"""
        
        # Add summary
        summary_fig = build_summary_panel(metrics, data)
        html_content += f"<div class='chart-container'>{pio.to_html(summary_fig, div_id='summary', include_plotlyjs=False)}</div>"
        
        # Add other panels
        battery_fig = build_battery_panel(data)
        html_content += f"<div class='chart-container'>{pio.to_html(battery_fig, div_id='battery', include_plotlyjs=False)}</div>"
        
        vibration_fig = build_vibration_motor_panel(data)
        html_content += f"<div class='chart-container'>{pio.to_html(vibration_fig, div_id='vibration', include_plotlyjs=False)}</div>"
        
        attitude_fig = build_attitude_panel(data)
        html_content += f"<div class='chart-container'>{pio.to_html(attitude_fig, div_id='attitude', include_plotlyjs=False)}</div>"
        
        gps_fig = build_gps_panel(data)
        html_content += f"<div class='chart-container'>{pio.to_html(gps_fig, div_id='gps', include_plotlyjs=False)}</div>"
        
        events_fig = build_events_panel(data)
        html_content += f"<div class='chart-container'>{pio.to_html(events_fig, div_id='events', include_plotlyjs=False)}</div>"
        
        # Add 2D map panel
        map_fig = build_2d_map_panel(data, color_by='speed')
        html_content += f"<div class='chart-container'><h2>Flight Trajectory — Real World GPS</h2>{pio.to_html(map_fig, div_id='map', include_plotlyjs=False)}</div>"
        
        trajectory_fig = build_3d_trajectory(data, color_by='speed')
        html_content += f"<div class='chart-container'>{pio.to_html(trajectory_fig, div_id='trajectory', include_plotlyjs=False)}</div>"
        
        html_content += """
</body>
</html>
"""
        
        with open(args.export, 'w') as f:
            f.write(html_content)
        
        print(f"✓ Dashboard exported to {args.export}")
    else:
        print(f"Launching dashboard at http://localhost:{args.port}")
        print("Press Ctrl+C to stop the server")
        app.run(debug=False, port=args.port)


if __name__ == '__main__':
    main()
