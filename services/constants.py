"""Shared thresholds and configuration for telemetry analysis."""

EARTH_RADIUS_M = 6_371_000  # WGS-84 Earth radius in meters
LOW_VOLTAGE_THRESHOLD = 3.5  # Volts per cell
VIBE_WARNING_THRESHOLD = 30  # m/s²
VIBE_CRITICAL_THRESHOLD = 60  # m/s²
MOTOR_MAX_PWM = 2000  # Microseconds (μs)
MOTOR_MIN_PWM = 1000  # Microseconds (μs)
MOTOR_SATURATION_MARGIN = 50  # PWM units from max/min

# GPS filtering thresholds
MIN_SATS = 6  # Minimum satellite count for valid fix
MAX_HDOP = 2.5  # Maximum HDOP for valid fix
_ALT_MEDIAN_K = 7  # median filter window (odd, capped by track length)
_MAX_PLAUSIBLE_H_SPEED = 200.0  # m/s; reject GPS segments implying higher horizontal speed

# Message types to extract
MESSAGE_TYPES = [
    'ATT', 'GPS', 'BAT', 'VIBE', 'RCOU', 'RCIN', 'IMU', 'MODE', 'ERR', 'MSG', 'EV', 'BARO'
]

# Padding around the GPS path when framing the 2D map: 20% of trajectory span per axis
MAP_TRAJECTORY_PADDING_FRAC = 0.2
