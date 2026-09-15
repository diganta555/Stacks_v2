"""
Owns the lifecycle of "the current dataset" for the Tabular tab.

Fixes two bugs from the original app:

1. Uploading a NEW file while a PREVIOUS file's cleaned/transformed data
   sat in session_state didn't reset anything — steps 10/13/14 would keep
   showing leftover state from the old file (they only seeded
   `tabular_df` "if it was still None", and after visiting a previous
   file it wasn't).

2. Cleaning/transformation done in steps 10/13/14 never reached the other
   17 steps, because those steps re-read the dataset straight from the
   uploaded file object every rerun instead of from session_state. Every
   step now reads the same `st.session_state.tabular_df` — clean or
   transform once, see it everywhere.

As a side effect this also fixes a performance issue: the file used to be
re-parsed (pd.read_csv/read_excel) on every single rerun, including
button clicks unrelated to the file. It's now parsed once per distinct
upload and reused from session_state after that.
"""

from typing import Optional

import pandas as pd
import streamlit as st

from tabular.loader import load_and_validate
from config import MAX_UPLOAD_ROWS, MAX_UPLOAD_ROWS_WARNING

# Session-state keys that hold AI output / history tied to a *specific*
# dataset. These get wiped whenever a genuinely new file is uploaded so
# you don't see stale insights from a previous dataset.
_DATASET_SCOPED_KEYS = [
    "ai_quality_report",
    "ai_cleaning_plan",
    "last_cleaning_summary",
    "last_cleaning_operation",
    "step13_last_cleaning",
    "step16_transformation_plan",
    "step17_chart_plan",
    "step18_business_insights",
    "step19_chat_history",
    "complete_analysis_report",
    "tabular_previous_df",
]


def _file_signature(tabular_file):
    """Cheap identity check — name + size. Avoids re-reading (and
    hashing) potentially large file contents just to detect a change."""
    return (tabular_file.name, tabular_file.size)


def clear_dataset_scoped_state() -> None:
    for key in _DATASET_SCOPED_KEYS:
        st.session_state.pop(key, None)
    st.session_state.tabular_previous_df = None


def reset_all_dataset_state() -> None:
    """Full wipe — used by the "Clear Dataset" button."""
    st.session_state.tabular_df = None
    st.session_state.tabular_original_df = None
    st.session_state.tabular_file_name = None
    st.session_state.tabular_file_signature = None
    clear_dataset_scoped_state()


def sync_with_uploaded_file(tabular_file) -> Optional[pd.DataFrame]:
    """Returns the current working dataframe for this upload. Parses +
    validates the file only the first time a given (name, size) is seen;
    every subsequent rerun reuses the already-loaded (and possibly
    cleaned/transformed) copy from session_state."""

    signature = _file_signature(tabular_file)
    is_new_file = signature != st.session_state.get("tabular_file_signature")

    if is_new_file:
        fresh_df = load_and_validate(tabular_file)
        if fresh_df is None:
            return None

        if len(fresh_df) > MAX_UPLOAD_ROWS:
            st.warning(MAX_UPLOAD_ROWS_WARNING.format(rows=len(fresh_df)))

        clear_dataset_scoped_state()
        st.session_state.tabular_df = fresh_df.copy()
        st.session_state.tabular_original_df = fresh_df.copy()
        st.session_state.tabular_file_name = tabular_file.name
        st.session_state.tabular_file_signature = signature
    else:
        st.success(f"Loaded **{tabular_file.name}** successfully.")

    return st.session_state.tabular_df
