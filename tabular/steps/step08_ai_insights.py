"""AI-Generated Insights — structured Finding/Evidence/Recommendation cards."""

import pandas as pd
import streamlit as st

from tabular.context import DatasetContext
from services.groq_service import get_groq_llm, extract_content
from config import AI_PRIVACY_NOTICE


def render(df: pd.DataFrame, ctx: DatasetContext, tabular_file=None) -> None:
    st.markdown("## AI-Generated Insights")
    st.caption(
        "Automatically transform dataset statistics into clear, actionable insights."
    )
    st.caption(AI_PRIVACY_NOTICE)

    c1, c2 = st.columns(2)
    with c1:
        insight_focus = st.selectbox(
            "Insight Focus",
            ["General", "Business", "Performance", "Customers", "Sales", "Data Quality"],
            key="ai_insight_focus",
        )
    with c2:
        insight_count = st.selectbox(
            "Number of Insights", [3, 5, 7, 10], index=1, key="ai_insight_count"
        )

    if not st.button("Generate AI Insights", key="generate_ai_insights", type="primary"):
        return

    try:
        llm = get_groq_llm(temperature=0)
        if llm is None:
            return

        numeric_columns = ctx.numeric_columns
        categorical_columns = ctx.categorical_columns

        dataset_summary = f"""
Dataset name:
{tabular_file.name}

Rows:
{ctx.total_rows}

Columns:
{ctx.total_columns}

Numeric columns:
{numeric_columns}

Categorical columns:
{categorical_columns}

Date columns:
{ctx.date_columns}

Missing values:
{ctx.missing_values}

Duplicate rows:
{ctx.duplicate_rows}
"""

        numeric_information = "No numeric columns available."
        if numeric_columns:
            rows = []
            for column in numeric_columns:
                series = pd.to_numeric(df[column], errors="coerce").dropna()
                if not series.empty:
                    rows.append(
                        {
                            "Column": column,
                            "Count": int(series.count()),
                            "Mean": round(series.mean(), 2),
                            "Median": round(series.median(), 2),
                            "Minimum": round(series.min(), 2),
                            "Maximum": round(series.max(), 2),
                            "Std Dev": round(series.std(), 2),
                        }
                    )
            if rows:
                numeric_information = pd.DataFrame(rows).to_string(index=False)

        categorical_information = "No categorical columns available."
        if categorical_columns:
            parts = []
            for column in categorical_columns:
                value_counts = df[column].fillna("Missing").astype(str).value_counts().head(10)
                parts.append(f"\nColumn: {column}\n\n{value_counts.to_string()}\n")
            categorical_information = "\n".join(parts)

        quality_information = ctx.quality_df.to_string(index=False)

        correlation_information = "Correlation analysis is not available."
        if len(numeric_columns) >= 2:
            correlation_matrix_ai = df[numeric_columns].corr()
            pairs = []
            for i in range(len(numeric_columns)):
                for j in range(i + 1, len(numeric_columns)):
                    col_a, col_b = numeric_columns[i], numeric_columns[j]
                    corr = correlation_matrix_ai.loc[col_a, col_b]
                    if pd.notna(corr):
                        pairs.append({"Column 1": col_a, "Column 2": col_b, "Correlation": round(corr, 3)})
            if pairs:
                correlation_information = (
                    pd.DataFrame(pairs)
                    .sort_values("Correlation", key=lambda x: x.abs(), ascending=False)
                    .head(10)
                    .to_string(index=False)
                )

        sample_data = df.head(20).to_string(index=False)

        insight_prompt = f"""
You are an expert AI Data Analyst.

Analyze the provided dataset information and generate
high-quality insights.

INSIGHT FOCUS:
{insight_focus}

NUMBER OF INSIGHTS:
{insight_count}

DATASET SUMMARY:
{dataset_summary}

NUMERIC INFORMATION:
{numeric_information}

CATEGORICAL INFORMATION:
{categorical_information}

DATA QUALITY:
{quality_information}

CORRELATION INFORMATION:
{correlation_information}

SAMPLE DATA:
{sample_data}

STRICT RULES:

1. Use only information supported by the dataset.
2. Do not invent values.
3. Do not invent business facts.
4. Use actual numbers whenever available.
5. Clearly distinguish observations from assumptions.
6. Do not claim causation from correlation.
7. Prioritize the most meaningful insights.
8. Avoid repeating the same insight.
9. Keep the recommendations practical.

For each insight use this format:

### Insight 1
**Finding:** <specific finding>

**Evidence:** <numbers or dataset evidence>

**Why it matters:** <short explanation>

**Recommendation:** <actionable recommendation>

Repeat for the requested number of insights.

Then provide:

### Overall Conclusion

A concise summary of the most important message
from the dataset.
"""

        with st.spinner("AI is generating insights..."):
            insight_response = llm.invoke(insight_prompt)

        ai_insights = extract_content(insight_response)

        st.markdown("### Generated Insights")
        st.markdown(ai_insights)

        st.download_button(
            "Download AI Insights",
            data=ai_insights,
            file_name="ai_generated_insights.txt",
            mime="text/plain",
            key="download_ai_insights",
        )

    except Exception as e:
        st.error(f"Unable to generate AI insights: {e}")
