"""AI Flight Analysis view — Gemini-powered post-flight report."""

from __future__ import annotations

import os
from typing import Dict, Optional

import streamlit as st

from service.ai.flight_analysis import analyse_flight
from ui.components import drone_spinner

_CACHE_KEY = "ai_analysis_cache"  # dict: file_key -> result str

_MODES = {
    "Short Report":    "short",
    "Detailed Report": "detailed",
    "Custom Question": "custom",
}


def render_ai_analysis(metrics: Dict, file_key: str = "") -> None:
    """Render the AI flight analysis section.

    Args:
        metrics:  flight metrics dict from compute_metrics().
        file_key: stable id for the current log file (sig_key + active_idx).
                  Used to cache and restore analysis results per file.
    """
    st.markdown("### AI Flight Analysis")

    # Ensure cache dict exists
    if _CACHE_KEY not in st.session_state:
        st.session_state[_CACHE_KEY] = {}

    api_key: Optional[str] = os.environ.get("GEMINI_API_KEY") or ""

    if not api_key:
        with st.expander("Gemini API Key", expanded=True):
            input_key = st.text_input(
                "API key",
                type="password",
                label_visibility="collapsed",
                placeholder="AIza...",
                help="Get your key at https://aistudio.google.com/app/apikey",
            )
            if input_key:
                api_key = input_key

    if not api_key:
        st.info("Enter your Gemini API key above to enable AI analysis.")
        return

    selected_label = st.radio(
        "Analysis mode",
        options=list(_MODES.keys()),
        index=1,
        horizontal=True,
        label_visibility="collapsed",
    )
    mode = _MODES[selected_label]

    custom_question = ""
    if mode == "custom":
        custom_question = st.text_area(
            "Your question",
            placeholder="e.g. Was the battery usage efficient for this distance?",
            label_visibility="collapsed",
        )

    button_disabled = mode == "custom" and not custom_question.strip()
    if st.button("Analyse flight with Gemini", type="primary", use_container_width=True, disabled=button_disabled):
        with drone_spinner("Gemini is analysing your flight…"):
            try:
                result = analyse_flight(api_key, metrics, mode=mode, custom_question=custom_question)
            except Exception as exc:
                result = f"**API Error:** {exc}"
        # Cache per file_key (mode+question included so switching mode reruns)
        cache_entry_key = f"{file_key}:{mode}:{custom_question}"
        st.session_state[_CACHE_KEY][cache_entry_key] = result

    # Show cached result for current file+mode if available
    cache_entry_key = f"{file_key}:{mode}:{custom_question if mode == 'custom' else ''}"
    cached = st.session_state[_CACHE_KEY].get(cache_entry_key)
    if cached:
        st.markdown(cached)
