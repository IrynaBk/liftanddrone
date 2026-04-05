# AI flight analysis (Gemini)

The **AI Flight Analysis** block in the Streamlit app (`views/ai_analysis.py`) calls **Google Gemini** to turn **already-computed mission metrics** into a short text report or a custom question-and-answer reply. It does **not** send the raw `.bin` log or full time series—only the structured `metrics` dict from `compute_metrics()`.

---

## What runs where

| Piece | Role |
|--------|------|
| `views/ai_analysis.py` | Streamlit UI: API key, mode picker, button, result display, session cache |
| `service/ai/flight_analysis.py` | Builds the metrics text block, picks system prompts, calls the Gemini API |
| `google-genai` (`import google.genai`) | Python client (see `requirements.txt`) |

The legacy **Dash** app (`drone_dashboard.py`) does **not** include this feature.

---

## API key

Set **`GEMINI_API_KEY`** in **`.streamlit/secrets.toml`** at the project root. The app also reads **`GEMINI_API_KEY`** from the process environment (`app.py` calls `load_dotenv()`, so a project-root **`.env`** may be used if you prefer). If unset, the UI shows an expander where you can paste a key for the current session (password field). Keys are obtained from [Google AI Studio](https://aistudio.google.com/app/apikey).

Setup is described in [Run the service — step 4](run-service.md#4-enable-ai-flight-analysis-gemini).

---

## Model

The service uses a single model id:

- **`gemini-3-flash-preview`** (`_MODEL_NAME` in `service/ai/flight_analysis.py`)

Google may rename or retire preview models; if generation fails after an API change, update `_MODEL_NAME` to a current Gemini model your key supports.

---

## Analysis modes

| UI label | Internal `mode` | Behaviour |
|----------|------------------|-----------|
| **Short Report** | `short` | Brief summary (system prompt caps at ~150 words): key stats, optional energy line, up to two safety notes |
| **Detailed Report** | `detailed` | Full structured report: overview, performance, energy, GPS quality, vibration/mechanical comments from gyro warnings, safety, recommendations |
| **Custom Question** | `custom` | Your question in a text area, plus the same metrics context block |

System instructions ask for **professional, concise Markdown**, **bullet points inside sections**, and **no invented numbers**—if a metric is missing or N/A, the model is told to say so.

---

## What is sent to the model

`build_metrics_prompt()` serializes the metrics dict into a fixed Markdown-style block, including when present:

- Duration, distance  
- Max total / horizontal / vertical speed  
- Takeoff and max altitude (MSL), max above takeoff, altitude gain  
- Max gravity-compensated acceleration  
- Energy (mAh), average current  
- Average satellites  
- Warning strings: distance, altitude gain, battery, gyro extremes  

If **`ekf_available`** is true, **EKF max speeds** (total, horizontal, vertical) are appended.

The user **custom** mode prepends your question, then appends this metrics block. Other modes prepend a task-specific instruction (“summarise…”, “produce a full report…”) before the metrics block.

---

## UI behaviour

- **Run**: Click **Analyse flight with Gemini** (disabled in custom mode until the question is non-empty). A spinner runs while `generate_content` executes.  
- **Errors**: Exceptions are shown as Markdown starting with `**API Error:**`.  
- **Cache**: Results are stored in **`st.session_state`** under a key that includes **`file_key`** (which log is active), **`mode`**, and **custom question** text, so switching files or modes does not overwrite unrelated results.

---

## Privacy and cost

Sending a report invokes **Google’s generative AI API** with the metrics text above. Treat the API key like any secret; restrict keys in Google Cloud / AI Studio as you would for production. Usage may be **metered or billed** according to your Google account and model pricing.

---

## Related

- [Functionality](functionality.md) — where AI fits in the Streamlit layout  
- [Run the service](run-service.md) — `secrets.toml` and running Streamlit locally  
