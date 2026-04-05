# Lift & Drone

**UAV telemetry analysis and interactive dashboards** for ArduPilot Dataflash binary logs: parsing, mission metrics, 2D maps, 3D trajectory, and a modern Streamlit UI.

## Capabilities

See **[Functionality](functionality.md)** for a full walkthrough of the pipeline, UI, and legacy Dash mode.

- **Log parsing** — ArduPilot `.bin` via pymavlink; relative timestamps and common message types (ATT, GPS, BAT, VIBE, RCOU, and more).
- **Analytics** — Distance (Haversine), velocity integration, duration, speeds, altitude, battery energy, and related metrics.
- **Streamlit app** (`app.py`) — Sidebar upload, mission summary, interactive map, and switchable telemetry panels (battery, vibration, attitude, events, 3D path, optional AI analysis).
- **Legacy Dash dashboard** (`drone_dashboard.py`) — Full multi-panel layout and optional static HTML export.

## Where to go next

1. [Getting started](getting-started.md) — Prerequisites, venv, quick commands for Streamlit, Dash, docs build, and exports.
2. [Run the service](run-service.md) — Full walkthrough: clone → install → Gemini key in `secrets.toml` → run → using the UI.
3. [Functionality](functionality.md) — What the app does: pipeline, Streamlit areas, panels, Dash export, and how it maps to the code.
4. [AI flight analysis](ai-flight-analysis.md) — Gemini integration: modes, metrics sent to the API, keys, caching.
5. [Why math works](why-math.md) — Theory behind the code: Euler vs gimbal lock, IMU integration, Haversine.
6. [Development](development.md) — Repository layout and how it relates to the legacy Dash app.

For the full narrative (features, troubleshooting, advanced tweaks), see the [README](https://github.com/IrynaBk/liftanddrone/blob/main/README.md) in the repository.
