"""Gemini-powered flight analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import google.generativeai as genai

from core.ai import prompts

_MODEL_NAME = "gemini-3-flash-preview"


@dataclass(frozen=True)
class PromptConfig:
    system: str
    prefix: str


_CONFIGS: Dict[str, PromptConfig] = {
    "detailed": PromptConfig(prompts.DETAILED, "Analyse the following ArduPilot flight telemetry and produce a full structured report.\n\n"),
    "short":    PromptConfig(prompts.SHORT,    "Summarise the following ArduPilot flight telemetry briefly.\n\n"),
    "custom":   PromptConfig(prompts.CUSTOM,   ""),
}


def _build_metrics_prompt(metrics: Dict) -> str:
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


class FlightAnalyser:
    """Gemini-powered flight analysis. Initialise once per API key."""

    def __init__(self, api_key: str) -> None:
        genai.configure(api_key=api_key)
        self._models: Dict[str, genai.GenerativeModel] = {}

    def _get_model(self, system_prompt: str) -> genai.GenerativeModel:
        if system_prompt not in self._models:
            self._models[system_prompt] = genai.GenerativeModel(
                model_name=_MODEL_NAME,
                system_instruction=system_prompt,
            )
        return self._models[system_prompt]

    def analyse(
        self,
        metrics: Dict,
        mode: str = "detailed",
        custom_question: str = "",
    ) -> str:
        """Run Gemini analysis and return a Markdown report.

        Args:
            metrics: Dict produced by compute_metrics().
            mode: One of "detailed", "short", "custom".
            custom_question: Used only when mode="custom".

        Returns:
            Markdown report string.

        Raises:
            google.generativeai.types.GoogleAPIError: on API failure.
        """
        config = _CONFIGS.get(mode, _CONFIGS["detailed"])
        model = self._get_model(config.system)

        if mode == "custom":
            prompt = f"{custom_question}\n\n{_build_metrics_prompt(metrics)}"
        else:
            prompt = config.prefix + _build_metrics_prompt(metrics)

        response = model.generate_content(prompt)
        return response.text
