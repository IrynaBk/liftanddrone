# Getting started

!!! info "Step-by-step walkthrough"

    For a full numbered guide (clone → venv → install → Gemini key in `secrets.toml` → run → use the UI), see **[Run the service](run-service.md)**.

## Prerequisites

- Python 3.10+ recommended (match your environment; the project ships with typical scientific Python deps).
- A virtual environment is recommended.

## Install application dependencies

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run the Streamlit dashboard

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501). Use the sidebar to upload `.bin` logs and explore summary, map, and telemetry panels.

## Run the legacy Dash dashboard

```bash
python drone_dashboard.py path/to/your_flight.bin
```

Default URL: [http://localhost:8050](http://localhost:8050).

### Export static HTML (Dash)

```bash
python drone_dashboard.py your_flight.bin --export report.html
```

## Gemini API (AI flight analysis)

Configure **`GEMINI_API_KEY`** in **`.streamlit/secrets.toml`** at the project root (same level as `app.py`). Streamlit loads this file; do not commit real keys to git.

```toml
# .streamlit/secrets.toml
GEMINI_API_KEY = "your_key_here"
```

See [Run the service — step 4](run-service.md#4-enable-ai-flight-analysis-gemini).

## Build this documentation site

```bash
pip install -r requirements-docs.txt
mkdocs serve
```

Then open the local URL printed in the terminal (usually [http://127.0.0.1:8000](http://127.0.0.1:8000)). For a static build:

```bash
mkdocs build
```

Output is written to `site/` (ignored by git).
