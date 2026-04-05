"""File I/O layer: parse uploaded log bytes and run the processing pipeline."""

import os
import tempfile
from typing import Dict, Tuple

import streamlit as st

from core.pipeline import process_log_file


@st.cache_data
def load_data_from_bytes(file_bytes: bytes) -> Tuple[Dict, Dict]:
    """Parse log from uploaded bytes and run full telemetry processing pipeline.

    Cached to avoid re-parsing on re-renders.

    Args:
        file_bytes: Raw bytes from uploaded .bin file.

    Returns:
        Tuple of (data dict, metrics dict).
    """
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        return process_log_file(tmp_path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except (PermissionError, OSError):
            pass
