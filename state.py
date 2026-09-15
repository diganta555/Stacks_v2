"""
Central place to initialize st.session_state keys used across the app.

Keeping this in one module means every session-state key the app relies on
is discoverable in a single file instead of scattered `if "x" not in
st.session_state` checks throughout the codebase.
"""

import streamlit as st


def init_session_state() -> None:
    defaults = {
        "tabular_df": None,
        "tabular_file_name": None,
        "tabular_original_df": None,
        "tabular_previous_df": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
