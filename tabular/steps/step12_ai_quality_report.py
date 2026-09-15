"""AI Data Quality Report — dataset profile converted into a business-readable report."""

import json

import pandas as pd
import streamlit as st

from tabular.context import DatasetContext
from services.groq_service import get_groq_llm, extract_content
from config import AI_PRIVACY_NOTICE


def render(df: pd.DataFrame, ctx: DatasetContext, tabular_file=None) -> None:
    st.markdown("## AI Data Quality Report")
    st.caption(
        "Use AI to convert dataset profiling and quality findings into "
        "actionable business recommendations."
    )
    st.caption(AI_PRIVACY_NOTICE)

    if df is None or df.empty:
        st.info("Upload a dataset to generate an AI data quality report.")
        return

    generate_ai_report = st.button("Generate AI Data Quality Report", key="generate_ai_quality_report")

    if generate_ai_report:
        total_rows = len(df)
        total_missing = int(df.isna().sum().sum())
        duplicate_count = int(df.duplicated().sum())
        constant_columns = [c for c in df.columns if df[c].nunique(dropna=False) <= 1]

        numeric_columns_for_ai = df.select_dtypes(include="number").columns.tolist()
        categorical_columns_for_ai = df.select_dtypes(include=["object", "category"]).columns.tolist()

        missing_details = {}
        for column in df.columns:
            missing_count = int(df[column].isna().sum())
            if missing_count > 0:
                missing_details[column] = {
                    "missing_count": missing_count,
                    "missing_percentage": round(missing_count / total_rows * 100, 2),
                }

        numeric_summary = {}
        for column in numeric_columns_for_ai:
            series = df[column].dropna()
            if series.empty:
                continue
            numeric_summary[column] = {
                "mean": round(float(series.mean()), 3),
                "median": round(float(series.median()), 3),
                "minimum": round(float(series.min()), 3),
                "maximum": round(float(series.max()), 3),
                "standard_deviation": round(float(series.std()), 3),
            }

        categorical_summary = {}
        for column in categorical_columns_for_ai:
            series = df[column].dropna()
            if series.empty:
                continue
            value_counts = series.value_counts().head(5)
            categorical_summary[column] = {
                "unique_values": int(series.nunique()),
                "top_values": {str(k): int(v) for k, v in value_counts.items()},
            }

        ai_context = {
            "dataset": {
                "rows": total_rows,
                "columns": len(df.columns),
                "column_names": df.columns.tolist(),
            },
            "data_quality": {
                "total_missing_values": total_missing,
                "duplicate_rows": duplicate_count,
                "constant_columns": constant_columns,
                "missing_details": missing_details,
            },
            "numeric_columns": numeric_summary,
            "categorical_columns": categorical_summary,
        }

        ai_context_json = json.dumps(ai_context, default=str)

        ai_prompt = f"""
You are an expert Data Quality Analyst.

Analyze the following dataset profile and create a concise,
professional data quality report.

DATASET PROFILE:
{ai_context_json}

Your report must contain exactly these sections:

1. Executive Summary
2. Critical Data Quality Issues
3. Business Impact
4. Recommended Actions
5. Priority

For each important issue explain:

- What is wrong
- Why it matters
- What should be done

Priority should classify issues as:

HIGH
MEDIUM
LOW

Do not invent information that is not present in the dataset profile.

Focus on practical and actionable recommendations.

Keep the report concise and easy for a business user to understand.
"""

        llm = get_groq_llm(temperature=0.2)
        if llm is not None:
            try:
                with st.spinner("Generating AI data quality report..."):
                    response = llm.invoke(ai_prompt)

                report_text = extract_content(response)
                st.session_state["ai_quality_report"] = report_text

                st.markdown("### AI Data Quality Report")
                st.markdown(report_text)
                st.success("AI data quality report generated successfully.")

            except Exception as e:
                st.error(f"Unable to generate AI report: {e}")

    if st.session_state.get("ai_quality_report") and not generate_ai_report:
        st.markdown("### Previous AI Data Quality Report")
        st.markdown(st.session_state.ai_quality_report)
        st.caption(
            "Click 'Generate AI Data Quality Report' to create a new report for the "
            "current dataset."
        )
