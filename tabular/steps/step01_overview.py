"""Dataset Overview — top-line metrics, data preview, column info table."""

import pandas as pd
import streamlit as st

from tabular.context import DatasetContext


def render(df: pd.DataFrame, ctx: DatasetContext, tabular_file=None) -> None:
    st.markdown("## Dataset Overview")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Rows", f"{ctx.total_rows:,}")
    with c2:
        st.metric("Columns", f"{ctx.total_columns:,}")
    with c3:
        st.metric("Numeric Columns", f"{len(ctx.numeric_columns):,}")
    with c4:
        st.metric("Categorical Columns", f"{len(ctx.categorical_columns):,}")
        
    st.divider()
    
    c5, c6, c7 = st.columns(3)
    with c5:
        st.metric("Date Columns", f"{len(ctx.date_columns):,}")
    with c6:
        st.metric("Missing Values", f"{ctx.missing_values:,}")
    with c7:
        st.metric("Duplicate Rows", f"{ctx.duplicate_rows:,}")

    st.divider()

    st.markdown("### Data Preview")
    st.dataframe(df.head(100), use_container_width=True, hide_index=True)

    st.divider()

    st.markdown("### Column Information")

    column_info = pd.DataFrame(
        {
            "Column": df.columns,
            "Data Type": [str(df[column].dtype) for column in df.columns],
            "Non-Null": [int(df[column].notna().sum()) for column in df.columns],
            "Null": [int(df[column].isna().sum()) for column in df.columns],
            "Unique": [int(df[column].nunique()) for column in df.columns],
        }
    )

    st.dataframe(column_info, use_container_width=True, hide_index=True)