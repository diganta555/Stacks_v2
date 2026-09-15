"""
Handles the CSV / Excel upload widget, basic validation, and loading into
a DataFrame. Returns None (after rendering the appropriate st.info /
st.error) when there's nothing usable to work with yet.
"""

from typing import Optional

import pandas as pd
import streamlit as st


def render_uploader():
    """Renders the file_uploader widget and returns the UploadedFile
    (or None if nothing has been uploaded)."""

    st.markdown(
        '<div class="stacks-label">Structured / Tabular Data</div>',
        unsafe_allow_html=True,
    )

    st.caption(
        "Upload CSV or Excel files to explore, analyze, visualize, "
        "and query your dataset using natural language."
    )

    tabular_file = st.file_uploader(
        "Upload CSV / Excel",
        type=["csv", "xlsx", "xls"],
        key="tabular_uploader",
    )

    if tabular_file is None:
        st.info(
            "Upload a CSV or Excel file to start the tabular analytics workflow."
        )

    return tabular_file


def load_and_validate(tabular_file) -> Optional[pd.DataFrame]:
    """Reads the uploaded file into a DataFrame and validates it. Returns
    None (having already rendered an error/warning) if the file can't be
    used. Raises normally on unexpected I/O errors — callers should wrap
    this in a try/except to show a friendly message."""

    file_name = tabular_file.name.lower()

    if file_name.endswith(".csv"):
        df = pd.read_csv(tabular_file)
    elif file_name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(tabular_file)
    else:
        st.error("Unsupported file format.")
        return None

    if df is None:
        st.error("Dataset loading returned None.")
        return None

    if not isinstance(df, pd.DataFrame):
        st.error(f"Invalid dataset type: {type(df)}")
        return None

    if df.empty:
        st.warning("The uploaded dataset is empty.")
        return None

    st.success(f"Loaded **{tabular_file.name}** successfully.")
    return df
