"""Statistical Analysis — numeric column summary table + per-column detail metrics."""

import pandas as pd
import streamlit as st

from tabular.context import DatasetContext


def render(df: pd.DataFrame, ctx: DatasetContext, tabular_file=None) -> None:
    st.markdown("## Statistical Analysis")

    numeric_columns = ctx.numeric_columns

    if not numeric_columns:
        st.info("No numeric columns were detected.")
        return

    st.markdown("### Numeric Column Summary")

    statistical_summary = pd.DataFrame(
        {
            "Column": numeric_columns,
            "Count": [int(df[col].count()) for col in numeric_columns],
            "Mean": [round(df[col].mean(), 2) for col in numeric_columns],
            "Median": [round(df[col].median(), 2) for col in numeric_columns],
            "Std Dev": [round(df[col].std(), 2) for col in numeric_columns],
            "Min": [round(df[col].min(), 2) for col in numeric_columns],
            "25%": [round(df[col].quantile(0.25), 2) for col in numeric_columns],
            "50%": [round(df[col].quantile(0.50), 2) for col in numeric_columns],
            "75%": [round(df[col].quantile(0.75), 2) for col in numeric_columns],
            "Max": [round(df[col].max(), 2) for col in numeric_columns],
        }
    )

    st.dataframe(statistical_summary, use_container_width=True, hide_index=True)

    st.divider()

    st.markdown("### Detailed Statistics")

    selected_numeric_column = st.selectbox(
        "Select a numeric column", numeric_columns, key="statistical_column"
    )

    selected_series = pd.to_numeric(
        df[selected_numeric_column], errors="coerce"
    ).dropna()

    if selected_series.empty:
        st.info(f"No valid numeric data found in `{selected_numeric_column}`.")
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Mean", f"{selected_series.mean():,.2f}")
    with c2:
        st.metric("Median", f"{selected_series.median():,.2f}")
    with c3:
        st.metric("Minimum", f"{selected_series.min():,.2f}")
    with c4:
        st.metric("Maximum", f"{selected_series.max():,.2f}")

    st.divider()

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.metric("Std Dev", f"{selected_series.std():,.2f}")
    with c6:
        st.metric("25th Percentile", f"{selected_series.quantile(0.25):,.2f}")
    with c7:
        st.metric("75th Percentile", f"{selected_series.quantile(0.75):,.2f}")
    with c8:
        st.metric("Non-Null Count", f"{selected_series.count():,}")