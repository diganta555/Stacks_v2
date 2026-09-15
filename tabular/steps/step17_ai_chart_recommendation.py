"""AI Chart Recommendation & Generation — AI picks a chart type/columns as
strict JSON, then a validated renderer draws it (no arbitrary code execution)."""

import json

import pandas as pd
import streamlit as st

from tabular.context import DatasetContext
from services.groq_service import get_groq_llm, extract_content
from config import AI_PRIVACY_NOTICE

VALID_CHART_TYPES = ["bar", "line", "scatter", "histogram", "box", "pie"]


def render(df: pd.DataFrame, ctx: DatasetContext, tabular_file=None) -> None:
    st.markdown("## AI Chart Recommendation & Generation")
    st.caption("Describe the visualization you want and let AI recommend the most suitable chart.")
    st.caption(AI_PRIVACY_NOTICE)

    if df is None or df.empty:
        st.info("Upload a dataset to use AI-powered chart generation.")
        return

    chart_request = st.text_input(
        "What would you like to visualize?",
        placeholder="Example: Show total sales by region",
        key="step17_chart_request",
    )

    if st.button("Generate Chart", key="step17_generate_chart"):
        if not chart_request.strip():
            st.warning("Please describe the chart you want.")
        else:
            _generate_chart_plan(df, chart_request)

    chart_plan = st.session_state.get("step17_chart_plan")
    if chart_plan:
        _render_chart_plan(df, chart_plan)


def _generate_chart_plan(df, chart_request):
    chart_context = {
        "rows": len(df),
        "columns": {column: str(df[column].dtype) for column in df.columns},
        "sample_data": df.head(5).to_dict(orient="records"),
    }
    chart_context_json = json.dumps(chart_context, default=str)

    chart_prompt = f"""
You are an expert data visualization assistant.

USER REQUEST:
{chart_request}

DATASET:
{chart_context_json}

Recommend the most appropriate chart.

Allowed chart types ONLY:

- bar
- line
- scatter
- histogram
- box
- pie

Return ONLY valid JSON in this exact structure:

{{
    "chart_type": "bar",
    "x_column": "column_name",
    "y_column": "column_name_or_null",
    "aggregation": "sum",
    "title": "Chart title",
    "reason": "Why this chart is appropriate"
}}

Rules:

- Only use columns that exist in the dataset.
- Do not invent column names.
- For categorical comparisons, prefer bar charts.
- For time-based trends, prefer line charts.
- For relationships between two numeric columns, prefer scatter.
- For distribution of one numeric column, prefer histogram.
- For detecting numeric spread and outliers, prefer box.
- Use pie only when the number of categories is small.
- Aggregation may be:
sum
mean
count
median
min
max
none
"""

    llm = get_groq_llm(temperature=0)
    if llm is None:
        return

    try:
        with st.spinner("AI is selecting the best chart..."):
            response = llm.invoke(chart_prompt)

        chart_response = extract_content(response)
        chart_response = chart_response.replace("```json", "").replace("```", "").strip()

        st.session_state["step17_chart_plan"] = json.loads(chart_response)

    except Exception as e:
        st.error(f"Unable to generate chart plan: {e}")


def _render_chart_plan(df, chart_plan):
    st.markdown("### AI Chart Recommendation")
    st.write(f"**Chart Type:** {chart_plan.get('chart_type', 'N/A')}")
    st.write(f"**X Column:** {chart_plan.get('x_column', 'N/A')}")
    st.write(f"**Y Column:** {chart_plan.get('y_column', 'N/A')}")
    st.write(f"**Aggregation:** {chart_plan.get('aggregation', 'N/A')}")
    st.write(f"**Reason:** {chart_plan.get('reason', 'N/A')}")

    chart_type = chart_plan.get("chart_type")
    x_column = chart_plan.get("x_column")
    y_column = chart_plan.get("y_column")
    aggregation = chart_plan.get("aggregation", "none")

    if chart_type not in VALID_CHART_TYPES:
        st.error("AI returned an unsupported chart type.")
        return
    if x_column not in df.columns:
        st.error(f"Column '{x_column}' does not exist.")
        return
    if y_column and y_column != "null" and y_column not in df.columns:
        st.error(f"Column '{y_column}' does not exist.")
        return

    st.markdown("### Generated Visualization")

    try:
        chart_df = df.copy()

        if chart_type == "histogram":
            _render_histogram(chart_df, x_column)
        elif chart_type == "box":
            _render_box(chart_df, x_column)
        elif chart_type == "scatter":
            _render_scatter(chart_df, x_column, y_column)
        elif chart_type in ("bar", "line", "pie"):
            _render_bar_line_pie(chart_df, chart_type, x_column, y_column, aggregation)

        st.caption(chart_plan.get("title", "Generated Visualization"))

    except Exception as e:
        st.error(f"Unable to generate visualization: {e}")


def _render_histogram(chart_df, x_column):
    if not pd.api.types.is_numeric_dtype(chart_df[x_column]):
        st.error("Histogram requires a numeric column.")
        return
    st.bar_chart(chart_df[x_column].value_counts().sort_index())


def _render_box(chart_df, x_column):
    if not pd.api.types.is_numeric_dtype(chart_df[x_column]):
        st.error("Box plot requires a numeric column.")
        return
    st.dataframe(chart_df[[x_column]].describe(), use_container_width=True)
    st.line_chart(chart_df[[x_column]])


def _render_scatter(chart_df, x_column, y_column):
    if not y_column:
        st.error("Scatter plot requires both X and Y columns.")
        return
    if not (pd.api.types.is_numeric_dtype(chart_df[x_column]) and pd.api.types.is_numeric_dtype(chart_df[y_column])):
        st.error("Scatter plots require numeric X and Y columns.")
        return
    st.scatter_chart(chart_df[[x_column, y_column]].dropna())


def _render_bar_line_pie(chart_df, chart_type, x_column, y_column, aggregation):
    if not y_column:
        grouped_df = chart_df[x_column].value_counts().reset_index()
        grouped_df.columns = [x_column, "Count"]
        st.bar_chart(grouped_df.set_index(x_column))
        return

    agg_map = {
        "sum": lambda g: g.sum(),
        "mean": lambda g: g.mean(),
        "median": lambda g: g.median(),
        "count": lambda g: g.count(),
        "min": lambda g: g.min(),
        "max": lambda g: g.max(),
    }

    if aggregation in agg_map:
        grouped = chart_df.groupby(x_column, dropna=False)[y_column]
        grouped_df = agg_map[aggregation](grouped).reset_index()
    else:
        grouped_df = chart_df[[x_column, y_column]].dropna()

    grouped_df = grouped_df.set_index(x_column)

    if chart_type == "line":
        st.line_chart(grouped_df)
    else:
        st.bar_chart(grouped_df)
