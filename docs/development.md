# Development

## Layout (Streamlit app)

The primary UI is driven by `app.py`, which wires Streamlit page config, data loading, and view modules:

| Area | Role |
|------|------|
| `app.py` | Entry point, session state, orchestrates views |
| `data/` | Loading and parsing helpers for uploaded log bytes |
| `views/` | Streamlit panels: summary, map, telemetry toolbar, AI analysis |
| `ui/` | Shared styles and components |
| `service/` | Backend logic (e.g. AI flight analysis) |

## Legacy Dash dashboard

`drone_dashboard.py` is a self-contained Dash application: constants, `parse_log()`, `compute_metrics()`, panel builders, and CLI (`main`). It remains useful for the classic all-panels-at-once layout and HTML export.

## Dependencies

Runtime libraries are listed in `requirements.txt` (pymavlink, numpy, plotly, dash, streamlit, geopy, optional Google AI, python-dotenv). Documentation tooling is isolated in `requirements-docs.txt` so production installs do not require MkDocs.

## Tests and quality

Add or run tests according to your workflow; this page only reflects the current structure. When extending message types or metrics, keep parsing and analytics changes consistent between Dash and Streamlit paths if both are still supported.
