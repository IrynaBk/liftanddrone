"""CSV export service for parsed flight data and metrics."""

from __future__ import annotations

import io
import csv
from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd


def export_metrics_to_csv(metrics: Dict) -> io.StringIO:
    """
    Export computed flight metrics to CSV format.
    One metric per row: name, value, unit.
    
    Args:
        metrics: Dictionary of computed flight metrics
        
    Returns:
        StringIO object containing CSV data
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Metric', 'Value', 'Unit'])
    
    # Define metrics with their units
    metric_definitions = [
        ('Duration', metrics.get('duration_str'), 'mm:ss'),
        ('Duration (seconds)', metrics.get('duration_s'), 's'),
        ('Total Distance', metrics.get('distance_m'), 'm'),
        ('Total Distance', metrics.get('distance_km'), 'km'),
        ('Max Total Speed', metrics.get('max_total_speed_ms'), 'm/s'),
        ('Max Total Speed', metrics.get('max_total_speed_kmh'), 'km/h'),
        ('Max Horizontal Speed', metrics.get('max_h_speed_ms'), 'm/s'),
        ('Max Horizontal Speed', metrics.get('max_h_speed_kmh'), 'km/h'),
        ('Max Vertical Speed', metrics.get('max_v_speed_ms'), 'm/s'),
        ('Max Vertical Speed', metrics.get('max_v_speed_kmh'), 'km/h'),
        ('Takeoff Altitude (ASL)', metrics.get('takeoff_alt_m'), 'm'),
        ('Max Altitude (ASL)', metrics.get('max_alt_m'), 'm'),
        ('Max Altitude Above Takeoff', metrics.get('max_alt_above_takeoff_m'), 'm'),
        ('Altitude Gain', metrics.get('alt_gain_m'), 'm'),
        ('Max Acceleration (gravity-compensated)', metrics.get('max_accel_ms2'), 'm/s²'),
        ('Average Current', metrics.get('avg_current_a'), 'A'),
        ('Energy Used', metrics.get('energy_used_mah'), 'mAh'),
        ('Average Satellites', metrics.get('avg_sats'), ''),
        ('Max IMU Speed', metrics.get('max_imu_speed_ms'), 'm/s'),
    ]
    
    # Add EKF metrics if available
    if metrics.get('ekf_available'):
        metric_definitions.extend([
            ('EKF Max Speed', metrics.get('ekf_max_speed_ms'), 'm/s'),
            ('EKF Max Speed', metrics.get('ekf_max_speed_kmh'), 'km/h'),
            ('EKF Max Horizontal Speed', metrics.get('ekf_max_h_speed_ms'), 'm/s'),
            ('EKF Max Horizontal Speed', metrics.get('ekf_max_h_speed_kmh'), 'km/h'),
            ('EKF Max Vertical Speed', metrics.get('ekf_max_v_speed_ms'), 'm/s'),
            ('EKF Max Vertical Speed', metrics.get('ekf_max_v_speed_kmh'), 'km/h'),
        ])
    
    # Write metrics
    for metric_name, value, unit in metric_definitions:
        if value is not None:
            writer.writerow([metric_name, value, unit])
    
    # Warnings section
    writer.writerow([])
    writer.writerow(['Warnings', '', ''])
    
    warnings = [
        ('Distance Warning', metrics.get('distance_warning')),
        ('Altitude Gain Warning', metrics.get('alt_gain_warning')),
        ('Battery Warning', metrics.get('battery_warning')),
        ('Gyro Extremes Warning', metrics.get('gyro_extremes_warning')),
        ('Speed Warning', metrics.get('speed_warning')),
    ]
    
    for warning_name, warning_val in warnings:
        if warning_val:
            writer.writerow([warning_name, warning_val, ''])
    
    output.seek(0)
    return output


def export_message_data_to_csv(data: Dict, message_type: str = 'GPS') -> Tuple[io.StringIO, str]:
    """
    Export raw message data (GPS, IMU, BAT, etc.) to CSV format.
    One message per row with all available fields.
    
    Args:
        data: Dictionary of parsed message streams
        message_type: Which message type to export (e.g., 'GPS', 'IMU', 'BAT')
        
    Returns:
        Tuple of (StringIO object with CSV data, filename suggestion)
    """
    messages = data.get(message_type, [])
    
    if not messages:
        # Return empty CSV with message type header
        output = io.StringIO()
        output.write(f"# No {message_type} messages found in this log\n")
        output.seek(0)
        return output, f"{message_type}_data.csv"
    
    # Use pandas for easier CSV generation from list of dicts
    df = pd.DataFrame(messages)
    
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    return output, f"{message_type}_data.csv"


def export_all_telemetry_to_csv(data: Dict) -> io.StringIO:
    """
    Export all available telemetry data to a single multi-sheet-like CSV
    with sections for each message type.
    
    Args:
        data: Dictionary of parsed message streams
        
    Returns:
        StringIO object containing comprehensive CSV data
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    message_types = [msg_type for msg_type in data.keys() if isinstance(data[msg_type], list)]
    
    for i, msg_type in enumerate(message_types):
        messages = data[msg_type]
        
        if i > 0:
            writer.writerow([])  # Blank line separator
        
        # Section header
        writer.writerow([f"=== {msg_type} Data ==="])
        
        if not messages:
            writer.writerow([f"No {msg_type} messages found"])
            continue
        
        # Get all possible field names
        all_fields = set()
        for msg in messages:
            all_fields.update(msg.keys())
        all_fields = sorted(list(all_fields))
        
        # Write header
        writer.writerow(all_fields)
        
        # Write data rows
        for msg in messages:
            row = [msg.get(field, '') for field in all_fields]
            writer.writerow(row)
    
    output.seek(0)
    return output


def generate_csv_filename(prefix: str = "flight") -> str:
    """Generate a timestamped CSV filename."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.csv"
