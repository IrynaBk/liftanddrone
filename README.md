# UAV Telemetry Analysis & Dashboard

A complete, production-ready Python application for analyzing ArduPilot Dataflash binary logs and rendering interactive mission analytics with 3D trajectory visualization.

**Documentation:** full documentation — [Run the service](https://irynabk.github.io/liftanddrone/run-service/).

## Features

### Log Parsing
- **Binary Format Support**: Parses ArduPilot Dataflash `.bin` files using `pymavlink`
- **12 Message Types**: ATT, GPS, BAT, VIBE, RCOU, RCIN, IMU, MODE, ERR, MSG, EV, BARO
- **Relative Timestamping**: Converts microsecond timestamps to seconds relative to mission start

### Analytics & Metrics
Computed in `service/metrics/metrics.py` (inputs prepared in `service/orchestrator.py`).

- **Track distance**: Sum of **Haversine** segment lengths along the GPS path; segments faster than a plausibility cap are dropped; **distance warning** if the track fails that filter.
- **Duration**: `mm:ss` from first to last GPS **`TimeS`** (or `N/A` without GPS).
- **GPS speeds** (after `filter_gps_by_quality`): **max horizontal** (`Spd`), **max vertical** (`|VZ|`), **max 3D speed**, **mean satellite count**.
- **IMU**: **Max dynamic acceleration** = peak specific-force magnitude minus **gravity** (~9.81 m/s²). **Max IMU speed** = peak magnitude of velocity obtained by trapezoidal integration per axis, with **+g on the Z accelerometer component** before integrating (`compute_metrics` + `integrate_velocity`) — a rough display metric, not an INS velocity.
- **Altitude** (median-smoothed GPS alt): **max**, **min**, **gain** (max − min), **takeoff alt** (first fix), **max above takeoff**; **altitude gain warning** on suspicious vertical steps.
- **Battery**: **average current** and **energy used (mAh)** from the last **`CurrTot`** sample; message if BAT is absent.
- **EKF** (when present in the log pipeline): peak **EKF** horizontal/vertical/total speeds.
- **Gyro extremes** warning from IMU (vibration-style sanity check).

### Streamlit Web UI (`app.py`)

- **Sidebar**: Upload one or two `.bin` logs (radio pick when two), **Color trajectory by** (speed / altitude / time — drives the **2D map** and **3D trajectory** coloring), quick stats, firmware line when present.
- **Mission Summary**: Ten stat cards (four columns) with optional metric notices in an expander.
- **2D map**: OpenStreetMap tiles, trajectory colored from the sidebar, takeoff/landing markers, mission bounds (reverse geocoding via geopy where available).
- **AI Flight Analysis**: Gemini text from computed metrics only (configure `GEMINI_API_KEY` in `.streamlit/secrets.toml` or paste a key in the UI); not part of the Dash app.
- **Telemetry panels** (single switchable strip — same Plotly builders as Dash, imported from `drone_dashboard.py`): **Vibration & Motors**, **Attitude**, **Events**, **3D Trajectory**, **Battery**. There is **no** separate GPS Health chart in Streamlit; map + filtered GPS stats cover navigation context instead.
- **Theming**: CSS under `ui/` plus `.streamlit/config.toml` (dark dashboard style).

### Legacy Dash dashboard (`drone_dashboard.py`)

All panels are on **one scrollable page** (port **8050**), in this **top-to-bottom** order:

1. **Mission Summary** — key metrics table and flight-mode timeline  
2. **Battery** — dual-axis voltage/current with low-voltage styling  
3. **Vibration & Motors** — vibration axes (with thresholds) and motor PWM  
4. **Attitude** — actual vs desired roll/pitch/yaw  
5. **GPS Health** — satellites, HDOP, altitude profile, fix type  
6. **Events** — errors, mode changes, and events over time  
7. **2D map** — trajectory with a **Color by** dropdown (speed / altitude / time)  
8. **Mission bounds** — text block with takeoff/landing hints and GPS quality notes  
9. **3D trajectory** — tabs for coloring by **speed** or **time** (Dash builds two figures; Streamlit uses one 3D view tied to the sidebar color mode, including altitude)

### 3D Trajectory Viewer
- **WGS-84 to ENU**: Local **E–N–U** path (EKF-fused when available, else GPS-based), same helper as Dash/Streamlit.
- **Dynamic coloring** (`build_3d_trajectory`): **Viridis** for speed or altitude, **Plasma** for time — in **Streamlit**, the choice matches **Color trajectory by** in the sidebar; **Dash** exposes separate tabs for speed vs time only.
- **Interaction**: Rotate, zoom, pan; takeoff/landing markers; color bar with units; hover for position/velocity where Plotly provides it.

## Installation

### 1. Clone or download this repository
```bash
git clone https://github.com/IrynaBk/liftanddrone.git
cd liftanddrone
```

### 2. Create a virtual environment (recommended)
```bash
python -m venv venv
```

On Windows:
```bash
venv\Scripts\activate
```

On macOS/Linux:
```bash
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### Documentation site (MkDocs)

To build and preview the project docs (Material for MkDocs):

```bash
pip install -r requirements-docs.txt
mkdocs serve
```

Static output is generated with `mkdocs build` into `site/` (gitignored).

## Usage

### Streamlit Web App (Recommended)
```bash
streamlit run app.py
```

Opens at `http://localhost:8501` with the layout described above: **Mission Summary** → **2D map** → **AI Flight Analysis** → **Telemetry panels** (Vibration & Motors, Attitude, Events, 3D Trajectory, Battery).

### Legacy Dash Dashboard
```bash
python drone_dashboard.py your_flight.bin
```

Opens at `http://localhost:8050` with the **nine stacked sections** listed under *Legacy Dash dashboard* (including GPS Health, 2D map, mission bounds, and 3D trajectory tabs).

### Export to Static HTML
```bash
python drone_dashboard.py your_flight.bin --export report.html
```

## Output Example

```
Parsing flight.bin...

Log Summary:
  ✓ ATT: 14,302 records
  ✓ GPS: 3,847 records
  ✓ BAT: 3,201 records
  ✓ VIBE: 3,150 records
  ✓ RCOU: 14,280 records
  ✓ IMU: 28,500 records
  ✓ MODE: 5 records
  ✓ ERR: 2 records

============================================================
MISSION SUMMARY
============================================================
Duration:          12:43
Distance:          4.72 km
Max H. Speed:      18.3 m/s (65.9 km/h)
Max V. Speed:      4.1 m/s
Max Altitude Gain: 87.4 m
Max Acceleration:  12.6 m/s²
Avg Current:       8.2 A
Energy Used:       3,241 mAh
============================================================

Launching dashboard at http://localhost:8050
```

## Code Structure

```
drone_dashboard.py
├── CONSTANTS
│   ├── EARTH_RADIUS_M
│   ├── LOW_VOLTAGE_THRESHOLD
│   ├── VIBE_WARNING_THRESHOLD
│   ├── VIBE_CRITICAL_THRESHOLD
│   └── MESSAGE_TYPES
│
├── UTILITY FUNCTIONS
│   ├── haversine()                    # WGS-84 distance
│   ├── integrate_velocity()           # Trapezoidal acceleration integration
│   ├── wgs84_to_enu()                 # Coordinate conversion
│
├── LOG PARSING
│   └── parse_log()                    # Binary file reader
│
├── ANALYTICS
│   └── compute_metrics()              # Metric calculations
│
├── DASHBOARD PANELS
│   ├── build_summary_panel()
│   ├── build_battery_panel()
│   ├── build_vibration_motor_panel()
│   ├── build_attitude_panel()
│   ├── build_gps_panel()
│   ├── build_events_panel()
│   ├── build_2d_map_panel()
│   ├── build_mission_bounds_info()
│   └── build_3d_trajectory()
│
├── APPLICATION
│   ├── create_app()                   # Dash app factory
│   ├── main()                         # CLI entry point
│   └── __main__                       # Script execution
```

## Dependencies

| Package | Purpose |
|---------|---------|
| **pymavlink** | Binary Dataflash log parsing |
| **numpy** | Numerical computation & integration |
| **plotly** | Interactive visualizations & 3D rendering |
| **dash** | Web framework & dashboard layout |
| **streamlit** | Modern web UI (`app.py`) |
| **geopy** | Reverse geocoding for map / mission bounds |
| **google-genai** | Gemini API (AI flight analysis) |
| **python-dotenv** | Load `.env` at startup (optional local config) |

For exact versions and constraints, see `requirements.txt`.

## Data Quality

The application gracefully handles missing data:
- Missing message types show "No data available" placeholders
- Malformed timestamps are skipped
- Zero GPS coordinates are filtered out
- Time deltas ≤ 0 are guarded against

## Performance

- Typical log file (30 min flight, ~500k records): **1-3 seconds parse time**
- Dashboard rendering: **<500ms** for all panels
- 3D trajectory with 10k+ points: **smooth 60fps interaction**

## Advanced Usage

### Modify Voltage Threshold
Edit line in `drone_dashboard.py`:
```python
LOW_VOLTAGE_THRESHOLD = 3.5  # Adjust for different cell count
```

### Add Custom Thresholds
Edit vibration/motor constants:
```python
VIBE_WARNING_THRESHOLD = 30
VIBE_CRITICAL_THRESHOLD = 60
```

### Extend for Custom Message Types
Add to `MESSAGE_TYPES` list and create extraction functions in `parse_log()`.

## Troubleshooting

### "Module not found: pymavlink"
```bash
pip install pymavlink --upgrade
```

### "Port 8050 already in use"
Use `--port` flag to specify different port:
```bash
python drone_dashboard.py flight.bin --port 8080
```

### "No battery data available"
Ensure log file contains BAT messages. Some log files may not include all message types.

## License

[Your License Here]

## Contributing

Contributions welcome! Please extend message type support or add new dashboard panels as needed.
