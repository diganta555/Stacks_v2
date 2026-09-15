"""Automatic Visualization — chart-type picker driven by dataset structure."""

import pandas as pd
import streamlit as st

from tabular.context import DatasetContext


def render(df: pd.DataFrame, ctx: DatasetContext, tabular_file=None) -> None:
    st.markdown("## Automatic Visualization")
    st.caption(
        "Generate visualizations automatically based on the structure of your dataset."
    )

    numeric_columns = ctx.numeric_columns
    categorical_columns = ctx.categorical_columns

    available_chart_types = []
    if numeric_columns:
        available_chart_types.extend(["Numeric Distribution", "Numeric Trend"])
    if categorical_columns:
        available_chart_types.append("Category Frequency")
    if len(numeric_columns) >= 2:
        available_chart_types.extend(["Scatter Plot", "Correlation Matrix"])
    if categorical_columns and numeric_columns:
        available_chart_types.append("Category vs Numeric")

    if not available_chart_types:
        st.info("Not enough columns available to generate a visualization.")
        return

    selected_chart_type = st.selectbox(
        "Select visualization", available_chart_types, key="automatic_chart_type"
    )

    handlers = {
        "Numeric Distribution": _numeric_distribution,
        "Numeric Trend": _numeric_trend,
        "Category Frequency": _category_frequency,
        "Scatter Plot": _scatter_plot,
        "Correlation Matrix": _correlation_matrix,
        "Category vs Numeric": _category_vs_numeric,
    }
    handlers[selected_chart_type](df, numeric_columns, categorical_columns)


def _numeric_distribution(df, numeric_columns, categorical_columns):
    selected = st.selectbox(
        "Select numeric column", numeric_columns, key="visual_numeric_distribution"
    )
    series = pd.to_numeric(df[selected], errors="coerce").dropna()

    if series.empty:
        st.warning("No valid numeric values available.")
        return

    distribution_data = series.value_counts(bins=20, sort=False).sort_index()
    distribution_data.index = [str(interval) for interval in distribution_data.index]
    st.bar_chart(distribution_data, use_container_width=True)


def _numeric_trend(df, numeric_columns, categorical_columns):
    selected = st.selectbox(
        "Select numeric column", numeric_columns, key="visual_trend_column"
    )
    trend_data = pd.to_numeric(df[selected], errors="coerce").dropna().reset_index(drop=True)

    if trend_data.empty:
        return

    trend_df = pd.DataFrame({"Row": range(1, len(trend_data) + 1), selected: trend_data})
    trend_df = trend_df.set_index("Row")
    st.line_chart(trend_df, use_container_width=True)


def _category_frequency(df, numeric_columns, categorical_columns):
    selected = st.selectbox(
        "Select categorical column", categorical_columns, key="visual_frequency_column"
    )
    frequency_data = df[selected].fillna("Missing").astype(str).value_counts().head(20)

    if frequency_data.empty:
        return

    st.bar_chart(frequency_data, use_container_width=True)

    frequency_table = frequency_data.reset_index()
    frequency_table.columns = [selected, "Count"]
    st.dataframe(frequency_table, use_container_width=True, hide_index=True)


def _scatter_plot(df, numeric_columns, categorical_columns):
    c1, c2 = st.columns(2)
    with c1:
        scatter_x = st.selectbox("X-axis", numeric_columns, key="visual_scatter_x")
    with c2:
        scatter_y = st.selectbox(
            "Y-axis",
            numeric_columns,
            index=1 if len(numeric_columns) > 1 else 0,
            key="visual_scatter_y",
        )

    scatter_df = df[[scatter_x, scatter_y]].copy()
    scatter_df[scatter_x] = pd.to_numeric(scatter_df[scatter_x], errors="coerce")
    scatter_df[scatter_y] = pd.to_numeric(scatter_df[scatter_y], errors="coerce")
    scatter_df = scatter_df.dropna()

    if scatter_df.empty:
        return

    st.scatter_chart(scatter_df, x=scatter_x, y=scatter_y, use_container_width=True)

    correlation_value = scatter_df[scatter_x].corr(scatter_df[scatter_y])
    if pd.notna(correlation_value):
        st.metric("Correlation", f"{correlation_value:.3f}")


def _correlation_matrix(df, numeric_columns, categorical_columns):
    correlation_visual = df[numeric_columns].corr()
    st.dataframe(correlation_visual.round(2), use_container_width=True)
    st.caption(
        "Values near +1 indicate a strong positive relationship. Values near -1 "
        "indicate a strong negative relationship."
    )


def _category_vs_numeric(df, numeric_columns, categorical_columns):
    c1, c2 = st.columns(2)
    with c1:
        selected_category = st.selectbox(
            "Category", categorical_columns, key="visual_category_column"
        )
    with c2:
        selected_numeric = st.selectbox(
            "Numeric value", numeric_columns, key="visual_category_numeric"
        )

    aggregation = st.selectbox(
        "Aggregation",
        ["Mean", "Sum", "Median", "Minimum", "Maximum", "Count"],
        key="visual_category_aggregation",
    )

    grouped = df.groupby(selected_category, dropna=False)[selected_numeric]
    agg_map = {
        "Mean": grouped.mean,
        "Sum": grouped.sum,
        "Median": grouped.median,
        "Minimum": grouped.min,
        "Maximum": grouped.max,
        "Count": grouped.count,
    }
    result = agg_map[aggregation]().sort_values(ascending=False).head(20)

    if result.empty:
        return

    st.bar_chart(result, use_container_width=True)

    table = result.reset_index()
    table.columns = [selected_category, aggregation]
    st.dataframe(table, use_container_width=True, hide_index=True)
