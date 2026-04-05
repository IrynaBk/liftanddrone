# Run the service (step by step)

The main application is the **Streamlit** dashboard in `app.py`. Run it from the **repository root** so Python can import `data`, `views`, `ui`, and `service`.

---

## 1. Get the project

Clone the repository and enter the folder:

```bash
git clone https://github.com/IrynaBk/liftanddrone.git
cd liftanddrone
```

If you already have the code, open a terminal and `cd` to that directory.

---

## 2. Use a virtual environment

Create and activate a venv (recommended so dependencies do not clash with other projects).

=== "macOS / Linux"

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

=== "Windows (cmd)"

    ```bat
    py -m venv venv
    venv\Scripts\activate.bat
    ```

=== "Windows (PowerShell)"

    ```powershell
    py -m venv venv
    .\venv\Scripts\Activate.ps1
    ```

You should see your shell prompt prefixed with `(venv)` when activation worked.

---

## 3. Install Python dependencies

With the venv active:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Wait until the install finishes without errors.

---

## 4. Enable AI flight analysis (Gemini)

The **AI Flight Analysis** section uses Google Gemini. Set **`GEMINI_API_KEY`** in **`.streamlit/secrets.toml`** at the project root (create the `.streamlit` folder if needed):

```toml
# .streamlit/secrets.toml — do not commit real keys to git
GEMINI_API_KEY = "your_key_here"
```

Get a key from [Google AI Studio](https://aistudio.google.com/app/apikey).  
If this key is missing, the rest of the dashboard still works; you can paste a key in the sidebar for the current session, or add it in `secrets.toml` as above.

---

## 5. Start the Streamlit app

From the **repository root** (`liftanddrone/`, where `app.py` lives):

```bash
streamlit run app.py
```

The terminal prints a local URL, typically:

- [http://localhost:8501](http://localhost:8501)

Open that address in your browser.

!!! tip "Custom port"

    If port `8501` is busy:

    ```bash
    streamlit run app.py --server.port 8502
    ```

---

## 6. Use the dashboard

1. In the **sidebar**, use **Upload .bin log file(s)** and select one or two ArduPilot Dataflash `.bin` files.
2. If you uploaded two files, pick the active log with the **radio buttons** under the file list.
3. Adjust **Color trajectory by** (speed, altitude, or time) if you want.
4. Scroll the main area for **mission summary**, **map**, **AI analysis** (if configured), and **telemetry panels** (battery, vibration, attitude, events, 3D trajectory).

---

## 7. Stop the server

In the terminal where Streamlit is running, press **Ctrl+C** to stop.

---

## Troubleshooting

| Issue | What to try |
|--------|-------------|
| `ModuleNotFoundError` | Ensure the venv is activated and `pip install -r requirements.txt` completed. Run `streamlit run app.py` from the repo root. |
| Port already in use | Use `--server.port` with another port (see above). |
| AI section asks for a key | Set `GEMINI_API_KEY` in `.streamlit/secrets.toml` or paste a key in the sidebar. |
| Blank or broken page | Check the terminal for tracebacks; confirm you are using a supported Python version (3.10+ recommended). |

For the **legacy Dash** dashboard and static HTML export, see [Getting started](getting-started.md#run-the-legacy-dash-dashboard).
