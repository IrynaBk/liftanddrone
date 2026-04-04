#!/usr/bin/env python3
"""
Example usage and quickstart guide for UAV Telemetry Dashboard
"""

# ============================================================================
# QUICKSTART EXAMPLES
# ============================================================================

"""
1. BASIC USAGE - Launch interactive dashboard
   
   $ python drone_dashboard.py your_flight.bin
   
   Then navigate to: http://localhost:8050
   
   The dashboard will show:
   - Mission Summary Card (metrics table)
   - Battery Health (voltage/current over time)
   - Vibration & Motor Outputs (dual panel)
   - Attitude Tracking (roll/pitch/yaw actual vs desired)
   - GPS Health (satellites, HDOP, altitude)
   - Events Timeline (errors, mode changes)
   - 3D Trajectory (with tabs for speed/time coloring)

---

2. EXPORT TO STATIC HTML (no server required)
   
   $ python drone_dashboard.py your_flight.bin --export report.html
   
   Creates a self-contained HTML file that can be:
   - Emailed or shared
   - Opened in any web browser
   - Saved as a permanent record

---

3. USE CUSTOM PORT (if 8050 is busy)
   
   $ python drone_dashboard.py your_flight.bin --port 8080
   
   Then navigate to: http://localhost:8080

---

4. COMBINE: Export AND later view in browser
   
   $ python drone_dashboard.py your_flight.bin --export my_mission_report.html
   $ open my_mission_report.html   # macOS
   $ start my_mission_report.html  # Windows
   $ xdg-open my_mission_report.html # Linux

---

5. ANALYZE MULTIPLE FLIGHTS
   
   $ python drone_dashboard.py flight1.bin --export flight1_report.html
   $ python drone_dashboard.py flight2.bin --export flight2_report.html
   $ python drone_dashboard.py flight3.bin --export flight3_report.html
   
   Compare reports side-by-side in browser.

---

6. BATCH PROCESSING (shell script)
   
   for logfile in logs/*.bin; do
       python drone_dashboard.py "$logfile" --export "${logfile%.bin}_report.html"
   done

---

7. HELP & OPTIONS
   
   $ python drone_dashboard.py --help
   
   Output:
   usage: drone_dashboard.py [-h] [--export EXPORT] [--port PORT] logfile
   
   positional arguments:
     logfile              Path to ArduPilot Dataflash .bin log file
   
   optional arguments:
     -h, --help           show this help message and exit
     --export EXPORT      Export to HTML file instead of launching Dash server
     --port PORT          Port for Dash server (default: 8050)

---

8. PROGRAMMATIC USE (import as module)
   
   from drone_dashboard import parse_log, compute_metrics, build_battery_panel
   import plotly.io as pio
   
   # Parse log
   data = parse_log('flight.bin')
   
   # Compute metrics
   metrics = compute_metrics(data)
   print(f"Flight duration: {metrics['duration_str']}")
   print(f"Distance: {metrics['distance_m']:.0f} m")
   
   # Extract specific panel
   battery_fig = build_battery_panel(data)
   pio.write_html(battery_fig, 'battery_report.html')

---

9. DOCKER DEPLOYMENT (for CI/CD)
   
   # Dockerfile
   FROM python:3.10-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY drone_dashboard.py .
   
   # Run dashboard in container
   $ docker build -t drone-analyzer .
   $ docker run -p 8050:8050 drone-analyzer python drone_dashboard.py flight.bin

"""

# ============================================================================
# INTERPRETATION GUIDE
# ============================================================================

"""
INTERPRETING DASHBOARD METRICS:

1. MISSION SUMMARY
   - Duration: Total flight time from first to last GPS fix
   - Distance: Path length using geodetic (Haversine) calculation
   - Max H. Speed: Fastest ground speed (GPS reported)
   - Max V. Speed: Fastest altitude change rate
   - Max Acceleration: Peak IMU-derived acceleration magnitude
   - Energy Used: Total mAh drawn from battery

2. BATTERY HEALTH
   - Look for voltage sags during high-current events
   - Green zone: Healthy operation
   - Orange band: Low voltage warning area
   - Red zones: Critical voltage (land immediately!)
   - Current peaks correlate with aggressive maneuvers

3. VIBRATION & MOTORS
   - Top panel: Vibration acceleration (X, Y, Z axes)
     * Green zone: <30 m/s² (safe)
     * Yellow zone: 30-60 m/s² (warning - check props)
     * Red zone: >60 m/s² (critical - bad vibration)
   - Bottom panel: Motor PWM outputs
     * Red zones at top/bottom = saturation (controller maxed out)
     * Symmetrical traces = balanced flight
     * Asymmetrical = possible damage/imbalance

4. ATTITUDE TRACKING
   - Blue (Roll), Orange (Pitch), Green (Yaw)
   - Solid lines = actual measured attitude
   - Dashed lines = pilot/autopilot commanded attitude
   - Gaps between actual vs desired = control lag or saturation
   - Jittery traces = possible vibration or sensor noise

5. GPS HEALTH
   - Blue bars: Altitude profile over time
   - Green markers: Number of satellites locked
   - Orange line: HDOP (Horizontal Dilution of Precision)
     * Lower HDOP = better accuracy (1-2 is excellent)
     * HDOP > 5 = degraded accuracy (consider GPS issues)

6. ERRORS & EVENTS
   - Red Xs: Errors logged (hover for details)
   - Colored diamonds: Flight mode changes
   - Cyan circles: Custom events
   - Look for error clusters which may indicate hardware issues

7. 3D TRAJECTORY
   - Green marker: Takeoff location
   - Red marker: Landing location
   - Colored line: Flight path
   - Speed coloring: Viridis scale (blue=slow, yellow=fast)
   - Time coloring: Plasma scale (purple=start, yellow=end)
   - Use 3D controls: rotate, zoom, pan

---

TROUBLESHOOTING PATTERNS:

Issue: Frequent voltage sags
→ Check battery health, capacity may be degraded

Issue: Vibration >60 m/s²
→ Check propellers for nicks, check motor bearings, rebalance

Issue: High error count
→ Check for compass interference, sensor calibration

Issue: Attitude lag (desired vs actual)
→ Check control loop tuning, may need faster response

Issue: GPS dropouts
→ Check GPS antenna placement and orientation
→ Consider GPS module failure if persistent

"""

# ============================================================================
# CUSTOMIZATION EXAMPLES
# ============================================================================

"""
MODIFYING THRESHOLDS:

Edit drone_dashboard.py constants section to adjust alert levels:

Current:
    LOW_VOLTAGE_THRESHOLD = 3.5  # Volts per cell
    VIBE_WARNING_THRESHOLD = 30   # m/s²
    VIBE_CRITICAL_THRESHOLD = 60  # m/s²

For 3S LiPo battery:
    LOW_VOLTAGE_THRESHOLD = 3.0  # Lower threshold for older batteries

For high-vibration airframes:
    VIBE_WARNING_THRESHOLD = 50   # Raise tolerance
    VIBE_CRITICAL_THRESHOLD = 100

---

ADDING CUSTOM MESSAGE TYPES:

1. Add to MESSAGE_TYPES list:
   MESSAGE_TYPES = [..., 'BARO', 'CUSTOM']

2. Extract in parse_log() - already handles unknown types gracefully

3. Create visualization function:
   def build_custom_panel(data):
       custom_data = data.get('CUSTOM', [])
       ...

4. Add to dashboard in create_app()

---

EXTENDED ANALYSIS (programmatic):

from drone_dashboard import *
import matplotlib.pyplot as plt

data = parse_log('flight.bin')
metrics = compute_metrics(data)

# Extract GPS for additional analysis
gps = data['GPS']
lats = [msg['Lat'] for msg in gps]
lons = [msg['Lng'] for msg in gps]

# Plot on map using your favorite GIS library
# import folium
# m = folium.Map(location=[lats[0], lons[0]], zoom_start=15)
# folium.PolyLine([(lat, lon) for lat, lon in zip(lats, lons)]).add_to(m)
# m.save('flight_map.html')

"""

print(__doc__)
