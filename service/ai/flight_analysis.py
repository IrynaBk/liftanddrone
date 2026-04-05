"""Gemini-powered flight analysis service."""

from __future__ import annotations

from typing import Dict

import google.generativeai as genai


_MODEL_NAME = "gemini-3-flash-preview"

_SYSTEM_PROMPT_BASE = """You are an expert UAV flight analyst with deep knowledge of ArduPilot systems,
multirotor dynamics, and flight safety. You receive structured telemetry metrics from an
ArduPilot Dataflash log.
Tone: professional, concise. Use bullet points inside each section.
Do NOT invent data not present in the metrics. If a value is 0 or N/A, note it as unavailable.
Output in Markdown."""

_SYSTEM_PROMPT_DETAILED = _SYSTEM_PROMPT_BASE + """

Produce a full post-flight analysis report covering ALL of the following sections:
1. **Flight Overview** — duration, distance, general flight character.
2. **Performance Assessment** — speed profile (horizontal, vertical, total), acceleration peaks,
   altitude profile (MSL and above takeoff). Flag anything unusual.
3. **Energy & Efficiency** — battery consumption if available; estimate efficiency (mAh/m)
   when possible.
4. **GPS & Navigation Quality** — satellite count, any warnings.
5. **Vibration & Mechanical Health** — if gyro extremes are present, comment on prop balance,
   motor health, or frame rigidity concerns.
6. **Safety & Anomalies** — highlight any metric that deviates from safe operational norms
   (e.g. excessive vertical speed, very high acceleration, low satellite count).
7. **Recommendations** — 2–4 concrete action items for the pilot or maintenance crew."""

_SYSTEM_PROMPT_SHORT = _SYSTEM_PROMPT_BASE + """

Produce a brief summary (max 150 words) covering only:
- Key flight stats (duration, distance, max speed, max altitude above takeoff).
- One sentence on energy if available.
- Up to 2 safety flags or recommendations if anything is notable."""

_SYSTEM_PROMPT_CUSTOM = _SYSTEM_PROMPT_BASE + """

Answer the pilot's specific question about this flight using only the provided metrics.
Be direct and concise."""


def build_metrics_prompt(metrics: Dict) -> str:
    """Format flight metrics into a structured prompt context block."""

    def _v(key: str, fmt: str = "{}", fallback: str = "N/A") -> str:
        val = metrics.get(key)
        if val is None:
            return fallback
        try:
            return fmt.format(val)
        except (ValueError, TypeError):
            return str(val)

    sections = [
        "## Flight Telemetry Metrics",
        f"- **Flight Duration**: {_v('duration_str')}",
        f"- **Total Distance**: {_v('distance_m', '{:.0f} m')}",

        "\n### Speed",
        f"- Max Total Speed: {_v('max_total_speed_ms', '{:.2f} m/s')}",
        f"- Max Horizontal Speed: {_v('max_h_speed_ms', '{:.2f} m/s')}",
        f"- Max Vertical Speed: {_v('max_v_speed_ms', '{:.2f} m/s')}",

        "\n### Altitude",
        f"- Takeoff Altitude (MSL): {_v('takeoff_alt_m', '{:.1f} m')}",
        f"- Max Altitude (MSL): {_v('max_alt_m', '{:.1f} m')}",
        f"- Max Altitude above Takeoff: {_v('max_alt_above_takeoff_m', '{:.1f} m')}",
        f"- Altitude Gain (max−min): {_v('alt_gain_m', '{:.1f} m')}",

        "\n### Dynamics",
        f"- Max Acceleration (gravity-compensated): {_v('max_accel_ms2', '{:.2f} m/s²')}",

        "\n### Energy",
        f"- Energy Used: {_v('energy_used_mah', '{:.0f} mAh')}",
        f"- Avg Current: {_v('avg_current_a', '{:.1f} A')}",

        "\n### GPS Quality",
        f"- Avg Satellites: {_v('avg_sats', '{:.1f}')}",

        "\n### Warnings",
        f"- Distance: {_v('distance_warning')}",
        f"- Altitude Gain: {_v('alt_gain_warning')}",
        f"- Battery: {_v('battery_warning')}",
        f"- Gyro Extremes: {_v('gyro_extremes_warning')}",
    ]

    if metrics.get("ekf_available"):
        sections += [
            "\n### EKF-Fused Trajectory",
            f"- EKF Max Speed: {_v('ekf_max_speed_ms', '{:.2f} m/s')}",
            f"- EKF Max H. Speed: {_v('ekf_max_h_speed_ms', '{:.2f} m/s')}",
            f"- EKF Max V. Speed: {_v('ekf_max_v_speed_ms', '{:.2f} m/s')}",
        ]

    return "\n".join(sections)


_PROMPTS = {
    "detailed": (_SYSTEM_PROMPT_DETAILED, "Analyse the following ArduPilot flight telemetry and produce a full structured report.\n\n"),
    "short":    (_SYSTEM_PROMPT_SHORT,    "Summarise the following ArduPilot flight telemetry briefly.\n\n"),
    "custom":   (_SYSTEM_PROMPT_CUSTOM,   ""),  # user question is appended by caller
}


def analyse_flight(api_key: str, metrics: Dict, mode: str = "detailed", custom_question: str = "") -> str:
    """
    Run Gemini flight analysis and return the Markdown report.

    Args:
        api_key: Gemini API key.
        metrics: Dict produced by compute_metrics().
        mode: One of "detailed", "short", "custom".
        custom_question: Used only when mode="custom".

    Returns:
        Markdown report string.

    Raises:
        google.generativeai.types.GoogleAPIError: on API failure.
    """
    system_prompt, prompt_prefix = _PROMPTS.get(mode, _PROMPTS["detailed"])

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name=_MODEL_NAME, system_instruction=system_prompt)

    if mode == "custom":
        prompt = f"{custom_question}\n\n{build_metrics_prompt(metrics)}"
    else:
        prompt = prompt_prefix + build_metrics_prompt(metrics)

    response = model.generate_content(prompt)
    return response.text
