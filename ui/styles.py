"""Global CSS styling and theme injection for the dashboard."""

import streamlit as st


def inject_global_css():
    """Inject dark theme CSS and custom styling."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;700&display=swap');

    /* Main app background */
    .stApp {
        background-color: #080b12;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #0a0d16;
        border-right: 1px solid #1e2535;
    }

    /* Reduce default padding */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1.5rem;
    }

    /* Text colors */
    body, .stMarkdown, .stText {
        color: #e5e7eb;
    }

    /* Metric widgets */
    div[data-testid="stMetric"] {
        background: #0f1117;
        border: 1px solid #1e2535;
        border-radius: 10px;
        padding: 16px;
    }

    div[data-testid="stMetricValue"] {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 18px !important;
        color: #e5e7eb !important;
        font-weight: 600;
    }

    div[data-testid="stMetricLabel"] {
        font-size: 11px !important;
        color: #6b7280 !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-weight: 500;
    }

    /* Pills/Radio styling */
    div[data-testid="stPills"] {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
    }

    div[data-testid="stPills"] button {
        background: #0f1117 !important;
        border: 1px solid #1e2535 !important;
        border-radius: 8px !important;
        color: #9ca3af !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 12px !important;
        padding: 6px 14px !important;
        transition: all 0.15s ease;
    }

    div[data-testid="stPills"] button[aria-selected="true"] {
        background: #1d4ed8 !important;
        border-color: #3b82f6 !important;
        color: #ffffff !important;
    }

    div[data-testid="stPills"] button:hover {
        border-color: #3b82f6 !important;
        color: #e5e7eb !important;
    }

    /* Plotly chart styling */
    .js-plotly-plot {
        border-radius: 12px;
    }

    /* Divider styling */
    hr {
        border-color: #1e2535;
        margin: 1.5rem 0;
    }

    /* File uploader */
    div[data-testid="stFileUploadDropzone"] {
        background: #0f1117;
        border: 1px dashed #1e2535;
        border-radius: 10px;
    }

    /* Selectbox styling */
    div[data-testid="stSelectbox"] > div:first-child {
        background: #0f1117;
        border: 1px solid #1e2535;
        border-radius: 8px;
    }

    /* Heading styling */
    h1, h2, h3 {
        font-family: 'IBM Plex Mono', monospace;
        color: #e5e7eb;
    }

    h1 {
        font-size: 28px;
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    h2 {
        font-size: 20px;
        font-weight: 600;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }

    h3 {
        font-size: 14px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #9ca3af;
    }

    /* Link styling */
    a {
        color: #3b82f6;
    }

    a:hover {
        color: #60a5fa;
    }

    /* Code styling */
    code {
        background: #0f1117;
        border: 1px solid #1e2535;
        border-radius: 6px;
        padding: 2px 6px;
        color: #86efac;
        font-family: 'IBM Plex Mono', monospace;
    }

    </style>
    """, unsafe_allow_html=True)
