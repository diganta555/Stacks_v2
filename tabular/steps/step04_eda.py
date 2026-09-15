"""Exploratory Analytics — distributions, correlations, grouped stats, top/bottom records."""

import pandas as pd
import streamlit as st

from tabular.context import DatasetContext


def render(df: pd.DataFrame, ctx: DatasetContext, tabular_file=None) -> None:
    st.markdown("## Exploratory Analytics")
    st.caption(
        "Explore distributions, relationships, correlations, grouped statistics, "
        "and extreme values."
    )

    numeric_columns = ctx.numeric_columns
    categorical_columns = ctx.categorical_columns

    _render_numeric_analysis(df, numeric_columns)
    _render_categorical_analysis(df, categorical_columns)
    _render_correlation_analysis(df, numeric_columns)
    _render_grouped_analysis(df, categorical_columns, numeric_columns)
    _render_top_bottom(df, numeric_columns)


def _render_numeric_analysis(df, numeric_columns):
    if not numeric_columns:
        return

    st.markdown("### Numeric Analysis")

    selected_eda_numeric = st.selectbox(
        "Select a numeric column", numeric_columns, key="eda_numeric_column"
    )

    numeric_series = pd.to_numeric(df[selected_eda_numeric], errors="coerce").dropna()

    if numeric_series.empty:
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Mean", f"{numeric_series.mean():,.2f}")
    with c2:
        st.metric("Median", f"{numeric_series.median():,.2f}")
    with c3:
        st.metric("Minimum", f"{numeric_series.min():,.2f}")
    with c4:
        st.metric("Maximum", f"{numeric_series.max():,.2f}")

    st.markdown("### Distribution")

    histogram_data = numeric_series.value_counts(bins=20, sort=False).sort_index()
    histogram_data.index = [str(interval) for interval in histogram_data.index]

    st.bar_chart(histogram_data, use_container_width=True)


def _render_categorical_analysis(df, categorical_columns):
    if not categorical_columns:
        return

    st.markdown("### Categorical Analysis")

    selected_eda_categorical = st.selectbox(
        "Select a categorical column", categorical_columns, key="eda_categorical_column"
    )

    category_counts = (
        df[selected_eda_categorical].fillna("Missing").astype(str).value_counts().head(20)
    )

    if category_counts.empty:
        return

    st.markdown(f"### Top Values — `{selected_eda_categorical}`")
    st.bar_chart(category_counts, use_container_width=True)

    category_table = category_counts.reset_index()
    category_table.columns = [selected_eda_categorical, "Count"]
    st.dataframe(category_table, use_container_width=True, hide_index=True)


def _render_correlation_analysis(df, numeric_columns):
    if len(numeric_columns) < 2:
        return

    st.markdown("### Correlation Analysis")

    correlation_matrix = df[numeric_columns].corr()
    st.dataframe(correlation_matrix.round(2), use_container_width=True)

    st.markdown("### Strongest Relationships")

    correlation_pairs = []
    for i in range(len(numeric_columns)):
        for j in range(i + 1, len(numeric_columns)):
            col_a, col_b = numeric_columns[i], numeric_columns[j]
            correlation = correlation_matrix.loc[col_a, col_b]
            if pd.notna(correlation):
                correlation_pairs.append(
                    {
                        "Column 1": col_a,
                        "Column 2": col_b,
                        "Correlation": round(correlation, 3),
                        "Absolute Correlation": round(abs(correlation), 3),
                    }
                )

    if correlation_pairs:
        correlation_df = pd.DataFrame(correlation_pairs).sort_values(
            "Absolute Correlation", ascending=False
        )
        st.dataframe(
            correlation_df[["Column 1", "Column 2", "Correlation"]],
            use_container_width=True,
            hide_index=True,
        )


def _render_grouped_analysis(df, categorical_columns, numeric_columns):
    if not (categorical_columns and numeric_columns):
        return

    st.markdown("### Grouped Analysis")

    g1, g2 = st.columns(2)
    with g1:
        selected_group_column = st.selectbox(
            "Group by", categorical_columns, key="eda_group_column"
        )
    with g2:
        selected_group_value = st.selectbox(
            "Calculate for", numeric_columns, key="eda_group_value"
        )

    aggregation = st.selectbox(
        "Aggregation",
        ["Mean", "Median", "Sum", "Minimum", "Maximum", "Count"],
        key="eda_aggregation",
    )

    grouped_data = df.groupby(selected_group_column, dropna=False)[selected_group_value]

    agg_map = {
        "Mean": grouped_data.mean,
        "Median": grouped_data.median,
        "Sum": grouped_data.sum,
        "Minimum": grouped_data.min,
        "Maximum": grouped_data.max,
        "Count": grouped_data.count,
    }
    grouped_result = agg_map[aggregation]().sort_values(ascending=False).head(20)

    st.markdown(
        f"### {aggregation} of `{selected_group_value}` by `{selected_group_column}`"
    )
    st.bar_chart(grouped_result, use_container_width=True)

    grouped_table = grouped_result.reset_index()
    grouped_table.columns = [selected_group_column, aggregation]
    st.dataframe(grouped_table, use_container_width=True, hide_index=True)


def _render_top_bottom(df, numeric_columns):
    if not numeric_columns:
        return

    st.markdown("### Top / Bottom Records")

    ranking_column = st.selectbox(
        "Rank records by", numeric_columns, key="eda_ranking_column"
    )

    r1, r2 = st.columns(2)
    with r1:
        st.markdown("#### Top 10")
        top_records = df.sort_values(ranking_column, ascending=False).head(10)
        st.dataframe(top_records, use_container_width=True, hide_index=True)

    with r2:
        st.markdown("#### Bottom 10")
        bottom_records = df.sort_values(ranking_column, ascending=True).head(10)
        st.dataframe(bottom_records, use_container_width=True, hide_index=True)
