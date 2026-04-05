"""AI Flight Analysis view — Gemini-powered post-flight report."""

from __future__ import annotations

import os
from typing import Dict, Optional

import streamlit as st

from service.ai.flight_analysis import analyse_flight

_SESSION_KEY = "ai_analysis_result"

_MODES = {
    "Short Report":    "short",
    "Detailed Report": "detailed",
    "Custom Question": "custom",
}


def render_ai_analysis(metrics: Dict) -> None:
    """Render the AI flight analysis section."""
    st.markdown("### AI Flight Analysis")

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
        with st.spinner("Gemini is analysing your flight…"):
            try:
                result = analyse_flight(api_key, metrics, mode=mode, custom_question=custom_question)
                st.session_state[_SESSION_KEY] = result
            except Exception as exc:
                st.session_state[_SESSION_KEY] = f"**API Error:** {exc}"

    if _SESSION_KEY in st.session_state:
        st.markdown(st.session_state[_SESSION_KEY])
