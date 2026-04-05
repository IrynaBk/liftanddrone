# Functionality

Lift & Drone ingests **ArduPilot Dataflash `.bin` logs**, runs a single processing pipeline, and presents results in a **Streamlit** UI (`app.py`). A **legacy Plotly Dash** app (`drone_dashboard.py`) reuses the same plot builders for an all-in-one layout and optional HTML export.

---

## End-to-end pipeline

When you upload a log, the app parses the binary file and runs:

1. **`parse_log`** — extract typed message streams (GPS, IMU, BAT, etc.).
2. **`run_ekf_on_log`** — optional EKF fusion for derived motion (when the pipeline produces data).
3. **`compute_metrics`** — mission metrics (distance, speeds, altitude, battery, warnings, etc.).

Orchestration is centralized in `service/orchestrator.py`; the Streamlit loader calls `process_log_file()` so views do not import parser/metrics modules directly.

---

## Log parsing

- **Format**: Dataflash binary via **pymavlink**.
- **Message types** used across analytics and UI include: **ATT, GPS, BAT, VIBE, RCOU, RCIN, IMU, MODE, ERR, MSG, EV, BARO** (and related fields inside those streams).
- **Time**: Microsecond timestamps are normalized to **seconds relative to mission start** for plotting and metrics.

---

## Metrics and warnings

Mission metrics (distance, duration, GPS speeds, IMU acceleration and integrated speed, altitude bands, battery current and energy, EKF peaks when available, gyro-extremes notice, etc.) are computed in `service/metrics/metrics.py`. The **Mission Summary** stat cards surface the main values; an expander lists **metric notices** (distance, altitude gain, battery, gyro) when warnings exist.

For a field-level description of how distance, speeds, IMU, and battery numbers are defined, see the **Analytics & Metrics** section in the [project README](https://github.com/IrynaBk/liftanddrone/blob/main/README.md).

---

## Streamlit application (`app.py`)

### Sidebar

- Upload **one or two** `.bin` files; with two logs, **radio buttons** choose which file drives the dashboard.
- **Color trajectory by**: speed, altitude, or elapsed time (affects **2D map** and **3D trajectory** coloring).
- **Quick stats**: duration, distance, max speed, energy (when available).
- **Firmware** line when a version string is found in **MSG** records.

### Mission Summary

A grid of **stat cards** (duration, distance, speed breakdown, altitude ASL and above takeoff, max acceleration, energy, average satellites, etc.) with optional per-metric warnings.

### Real-world GPS trajectory (2D)

Interactive **Plotly** map with OpenStreetMap tiles, trajectory coloring from sidebar settings, takeoff/landing context, and **mission bounds** details: reverse-geocoded **takeoff/landing** hints (Nominatim), coordinates, and **valid GPS points** vs total with average HDOP/satellites for filtered points.

### AI Flight Analysis

**Google Gemini** post-flight text based on the **metrics dict only** (not the raw log): **Short** / **Detailed** reports or a **Custom question**, with results cached per log and mode. Configure **`GEMINI_API_KEY`** in **`.streamlit/secrets.toml`**, or paste a key in the sidebar expander for the current session.

For model id, prompts, what data is sent to the API, and privacy notes, see **[AI flight analysis (Gemini)](ai-flight-analysis.md)**.

### Telemetry panels (toolbar)

Switchable **Plotly** views (pills or radio, depending on Streamlit version):

| Panel | Content |
|--------|---------|
| **Battery** | Voltage and current over time |
| **Vibration & Motors** | Vibration axes and motor PWM outputs |
| **Attitude** | Actual vs desired attitude |
| **Events** | Mode changes, errors, and events timeline |
| **3D Trajectory** | Local **E–N–U** path with coloring tied to the same **speed / altitude / time** choice as the map |

Panel builders live in `drone_dashboard.py` and are imported by `views/telemetry.py`.

---

## Legacy Dash dashboard (`drone_dashboard.py`)

- **CLI**: `python drone_dashboard.py path/to/log.bin` — serves a multi-panel layout (typically port **8050**).
- **Static export**: `--export report.html` writes a standalone HTML file.
- Includes a **GPS health** style panel in the classic layout that is not wired into the Streamlit toolbar (Streamlit focuses the map + filtered GPS stats instead).

---

## Theming and assets

The Streamlit app uses project **CSS** under `ui/` and `.streamlit/config.toml` for a dark, dashboard-style appearance.

---

## Related docs

- [Why math works](why-math.md) — mathematical rationale in comments (Euler, IMU, Haversine).
- [AI flight analysis](ai-flight-analysis.md) — Gemini modes, prompts, and API behaviour.
- [Run the service](run-service.md) — install and launch the Streamlit app step by step.
- [Development](development.md) — repository layout for contributors.
