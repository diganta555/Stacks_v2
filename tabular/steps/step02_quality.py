"""Data Quality — missing values, duplicates, constant columns, overall verdict."""

import pandas as pd
import streamlit as st

from tabular.context import DatasetContext


def render(df: pd.DataFrame, ctx: DatasetContext, tabular_file=None) -> None:
    st.markdown("## Data Quality")

    quality_df = ctx.quality_df

    st.markdown("### Missing Values")
    st.dataframe(
        quality_df[["Column", "Data Type", "Missing", "Missing %", "Unique"]],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Duplicate Rows")
    if ctx.duplicate_rows == 0:
        st.success("No duplicate rows found.")
    else:
        duplicate_percentage = (
            round((ctx.duplicate_rows / len(df)) * 100, 2) if len(df) > 0 else 0
        )
        st.warning(
            f"{ctx.duplicate_rows:,} duplicate rows found "
            f"({duplicate_percentage}% of the dataset)."
        )

    columns_with_missing = quality_df[quality_df["Missing"] > 0]

    if not columns_with_missing.empty:
        st.markdown("### Columns With Missing Values")
        st.dataframe(
            columns_with_missing[["Column", "Missing", "Missing %"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("No missing values found in any column.")

    st.markdown("### Constant Columns")
    if ctx.constant_columns:
        st.warning(
            f"Found {len(ctx.constant_columns)} constant column(s): "
            + ", ".join(ctx.constant_columns)
        )
    else:
        st.success("No constant columns found.")

    st.markdown("### Overall Quality")

    total_cells = df.shape[0] * df.shape[1]
    missing_percentage = (
        (ctx.missing_values / total_cells) * 100 if total_cells > 0 else 0
    )

    if ctx.duplicate_rows == 0 and ctx.missing_values == 0:
        st.success("Excellent — no missing values or duplicate rows detected.")
    elif missing_percentage <= 5 and ctx.duplicate_rows <= len(df) * 0.05:
        st.info("Good — a small amount of data cleaning may be required.")
    else:
        st.warning(
            "Attention required — the dataset contains significant missing "
            "values or duplicate rows."
        )
