"""AI Business Insights & Decision Support — answers a business question using
only what's derivable from the dataset context."""

import json

import pandas as pd
import streamlit as st

from tabular.context import DatasetContext
from services.groq_service import get_groq_llm, extract_content
from config import AI_PRIVACY_NOTICE


def render(df: pd.DataFrame, ctx: DatasetContext, tabular_file=None) -> None:
    st.markdown("## AI Business Insights & Decision Support")
    st.caption(
        "Generate business-focused insights, risks, trends, and actionable "
        "recommendations from the current dataset."
    )
    st.caption(AI_PRIVACY_NOTICE)

    if df is None or df.empty:
        st.info("Upload a dataset to generate business insights.")
        return

    business_question = st.text_area(
        "What business question do you want to answer?",
        placeholder="Example: Which products are performing best and where should we focus?",
        key="step18_business_question",
    )

    if st.button("Generate Business Insights", key="step18_generate_insights"):
        if not business_question.strip():
            st.warning("Please enter a business question.")
        else:
            _generate_insights(df, ctx, business_question)

    insights = st.session_state.get("step18_business_insights")
    if insights:
        st.markdown("### Business Analysis")
        st.markdown(insights)

        st.download_button(
            label="Download Business Insights",
            data=insights.encode("utf-8"),
            file_name="business_insights.txt",
            mime="text/plain",
            key="step18_download_insights",
        )


def _generate_insights(df, ctx, business_question):
    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    categorical_columns = df.select_dtypes(include=["object", "category"]).columns.tolist()

    dataset_summary = {
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": df.columns.tolist(),
        "data_types": {column: str(df[column].dtype) for column in df.columns},
        "missing_values": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
    }

    numeric_summary = {}
    for column in numeric_columns:
        series = df[column].dropna()
        if series.empty:
            continue
        numeric_summary[column] = {
            "mean": round(float(series.mean()), 3),
            "median": round(float(series.median()), 3),
            "min": round(float(series.min()), 3),
            "max": round(float(series.max()), 3),
            "std": round(float(series.std()), 3),
        }

    categorical_summary = {}
    for column in categorical_columns:
        series = df[column].dropna()
        if series.empty:
            continue
        top_values = series.value_counts().head(5)
        categorical_summary[column] = {
            "unique_values": int(series.nunique()),
            "top_values": {str(k): int(v) for k, v in top_values.items()},
        }

    business_context = {
        "dataset": dataset_summary,
        "numeric_analysis": numeric_summary,
        "categorical_analysis": categorical_summary,
        "sample_data": df.head(10).to_dict(orient="records"),
    }
    business_context_json = json.dumps(business_context, default=str)

    business_prompt = f"""
You are a senior business data analyst.

Answer the user's business question using ONLY the
information available in the dataset context.

BUSINESS QUESTION:
{business_question}

DATASET CONTEXT:
{business_context_json}

Create a concise executive-level analysis.

Use exactly these sections:

1. Executive Answer
2. Key Findings
3. Important Trends
4. Business Risks
5. Recommended Actions
6. Confidence

Rules:

- Do not invent facts.
- Do not claim causation when the dataset only shows correlation.
- Clearly distinguish observations from recommendations.
- Quantify findings whenever possible.
- If the dataset does not contain enough information to answer
the question, explicitly say so.
- Do not recommend decisions that require information unavailable
in the dataset.
- Keep recommendations practical.
- Confidence must be one of:
HIGH
MEDIUM
LOW

The final answer should be understandable to a non-technical
business stakeholder.
"""

    llm = get_groq_llm(temperature=0.1)
    if llm is None:
        return

    try:
        with st.spinner("AI is analyzing the dataset for business insights..."):
            response = llm.invoke(business_prompt)
        st.session_state["step18_business_insights"] = extract_content(response)
    except Exception as e:
        st.error(f"Unable to generate business insights: {e}")
