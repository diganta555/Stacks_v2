"""AI Data Analyst — free-form question answered against a dataset profile."""

import pandas as pd
import streamlit as st

from tabular.context import DatasetContext
from services.groq_service import get_groq_llm, extract_content
from config import AI_PRIVACY_NOTICE


def render(df: pd.DataFrame, ctx: DatasetContext, tabular_file=None) -> None:
    st.markdown("## AI Data Analyst")
    st.caption(
        "Let AI analyze your dataset and provide key findings, trends, "
        "anomalies, and actionable recommendations."
    )
    st.caption(AI_PRIVACY_NOTICE)

    c1, c2 = st.columns(2)
    with c1:
        analysis_type = st.selectbox(
            "Analysis Type",
            [
                "Overall Dataset Analysis",
                "Business Insights",
                "Anomaly Detection",
                "Trend Analysis",
                "Data Quality Recommendations",
            ],
            key="ai_analysis_type",
        )
    with c2:
        analysis_detail = st.selectbox(
            "Analysis Detail",
            ["Concise", "Detailed", "Very Detailed"],
            index=1,
            key="ai_analysis_detail",
        )

    analyst_question = st.text_area(
        "What would you like the AI analyst to investigate?",
        placeholder=(
            "Example: Analyze this dataset and identify the most important "
            "business insights."
        ),
        height=100,
        key="ai_analyst_question",
    )

    with st.expander("Example AI Analyst Questions"):
        st.markdown(
            """
            - Analyze the overall dataset and give me the most important findings.
            - What are the main trends in this dataset?
            - Are there any unusual or suspicious values?
            - What business insights can be extracted from this data?
            - Which categories are performing the best?
            - What data quality problems should I fix?
            - What recommendations would you give based on this dataset?
            """
        )

    if not st.button("Analyze Dataset", key="run_ai_analyst", type="primary"):
        return

    if not analyst_question.strip():
        st.warning("Please enter a question for the AI analyst.")
        return

    try:
        llm = get_groq_llm(temperature=0)
        if llm is None:
            return

        numeric_columns = ctx.numeric_columns
        categorical_columns = ctx.categorical_columns

        dataset_profile_text = "\n".join(
            [
                f"Dataset rows: {len(df)}",
                f"Dataset columns: {len(df.columns)}",
                f"Numeric columns: {numeric_columns}",
                f"Categorical columns: {categorical_columns}",
                f"Date columns: {ctx.date_columns}",
                f"Missing values: {ctx.missing_values}",
                f"Duplicate rows: {ctx.duplicate_rows}",
            ]
        )

        numeric_summary_text = "No numeric columns available."
        if numeric_columns:
            numeric_summary = pd.DataFrame(
                {
                    "Column": numeric_columns,
                    "Mean": [round(df[col].mean(), 2) for col in numeric_columns],
                    "Median": [round(df[col].median(), 2) for col in numeric_columns],
                    "Min": [round(df[col].min(), 2) for col in numeric_columns],
                    "Max": [round(df[col].max(), 2) for col in numeric_columns],
                    "Std Dev": [round(df[col].std(), 2) for col in numeric_columns],
                }
            )
            numeric_summary_text = numeric_summary.to_string(index=False)

        categorical_summary_text = "No categorical columns available."
        if categorical_columns:
            parts = []
            for col in categorical_columns:
                top_values = df[col].fillna("Missing").astype(str).value_counts().head(5)
                parts.append(f"\nColumn: {col}\n{top_values.to_string()}")
            categorical_summary_text = "\n".join(parts)

        missing_columns_ai = []
        for col in df.columns:
            missing_count = int(df[col].isna().sum())
            if missing_count > 0:
                missing_columns_ai.append(
                    {
                        "Column": col,
                        "Data Type": str(df[col].dtype),
                        "Missing": missing_count,
                        "Missing %": round(missing_count / len(df) * 100, 2) if len(df) > 0 else 0,
                        "Unique": int(df[col].nunique(dropna=True)),
                    }
                )
        missing_summary = (
            pd.DataFrame(missing_columns_ai).to_string(index=False)
            if missing_columns_ai
            else "No missing values."
        )

        correlation_summary = "Not enough numeric columns for correlation analysis."
        if len(numeric_columns) >= 2:
            correlation_matrix_ai = df[numeric_columns].corr()
            pairs = []
            for i in range(len(numeric_columns)):
                for j in range(i + 1, len(numeric_columns)):
                    col_a, col_b = numeric_columns[i], numeric_columns[j]
                    corr_value = correlation_matrix_ai.loc[col_a, col_b]
                    if pd.notna(corr_value):
                        pairs.append({"Column 1": col_a, "Column 2": col_b, "Correlation": round(corr_value, 3)})
            if pairs:
                correlation_summary = (
                    pd.DataFrame(pairs)
                    .sort_values("Correlation", key=lambda x: x.abs(), ascending=False)
                    .head(10)
                    .to_string(index=False)
                )

        sample_data = df.head(20).to_string(index=False)

        detail_instructions = {
            "Concise": "Keep the analysis concise. Focus only on the most important findings.",
            "Detailed": "Provide a detailed analysis with clear explanations and supporting numbers.",
            "Very Detailed": (
                "Provide a very detailed analysis covering important patterns, "
                "relationships, anomalies, data quality issues, and recommendations."
            ),
        }
        detail_instruction = detail_instructions[analysis_detail]

        analyst_prompt = f"""
You are an expert AI Data Analyst.

Analyze the provided dataset information and answer
the user's question.

ANALYSIS TYPE:
{analysis_type}

USER QUESTION:
{analyst_question}

ANALYSIS DETAIL:
{analysis_detail}

DATASET PROFILE:
{dataset_profile_text}

NUMERIC SUMMARY:
{numeric_summary_text}

CATEGORICAL SUMMARY:
{categorical_summary_text}

MISSING VALUE SUMMARY:
{missing_summary}

CORRELATION SUMMARY:
{correlation_summary}

SAMPLE DATA:
{sample_data}

INSTRUCTIONS:

{detail_instruction}

Your response must be based only on the information
provided about the dataset.

Do not invent values, columns, trends, or business facts.

Clearly distinguish observations from recommendations.

Structure your answer using these sections:

## Key Findings

List the most important findings from the dataset.

## Trends & Patterns

Explain important trends, distributions,
relationships, or category patterns.

## Anomalies / Risks

Identify unusual values, potential anomalies,
data quality problems, or risks if supported
by the available data.

## Recommendations

Provide practical recommendations based
on the findings.

## Summary

Give a short final conclusion.

Use actual numbers from the dataset whenever available.
"""

        with st.spinner("AI analyst is analyzing your dataset..."):
            analyst_response = llm.invoke(analyst_prompt)

        analyst_result = extract_content(analyst_response)

        st.markdown("### AI Analysis")
        st.markdown(analyst_result)

        st.download_button(
            "Download AI Analysis",
            data=analyst_result,
            file_name="ai_data_analysis.txt",
            mime="text/plain",
            key="download_ai_analysis",
        )

    except Exception as e:
        st.error(f"AI analysis failed: {e}")
