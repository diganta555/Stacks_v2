"""
Orchestrates the "Tabular Data" tab: renders the sidebar, handles the
upload + validation flow, builds the shared DatasetContext once, and
dispatches to whichever step the sidebar selected.
"""

import streamlit as st

from tabular.context import build_context
from tabular.loader import render_uploader
from tabular.dataset_state import sync_with_uploaded_file
from tabular.router import dispatch
from tabular.sidebar import render_sidebar


def render_tabular_tab() -> None:
    navigation = render_sidebar()

    tabular_file = render_uploader()

    if tabular_file is None:
        return

    try:
        df = sync_with_uploaded_file(tabular_file)
    except Exception as e:
        st.error(f"Unable to read `{tabular_file.name}`: {e}")
        return

    if df is None:
        return

    ctx = build_context(df)

    dispatch(navigation, df, ctx, tabular_file)
