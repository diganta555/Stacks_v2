"""Automated Data Cleaning Assistant — detects issues, AI proposes a plan,
user explicitly approves before any destructive operation runs."""

import json

import pandas as pd
import streamlit as st

from tabular.context import DatasetContext
from services.groq_service import get_groq_llm, extract_content
from config import AI_PRIVACY_NOTICE


def render(df: pd.DataFrame, ctx: DatasetContext, tabular_file=None) -> None:
    st.markdown("## Automated Data Cleaning Assistant")
    st.caption(
        "AI analyzes the current dataset and recommends specific cleaning "
        "actions. No changes are made without your approval."
    )
    st.caption(AI_PRIVACY_NOTICE)

    if df is None or df.empty:
        st.info("Upload a dataset to use the AI Data Cleaning Assistant.")
        return

    total_rows = len(df)
    total_columns = len(df.columns)
    total_missing = int(df.isna().sum().sum())
    duplicate_count = int(df.duplicated().sum())
    constant_columns = [c for c in df.columns if df[c].nunique(dropna=False) <= 1]

    column_information = _build_column_information(df, total_rows)
    detected_issues = _detect_issues(df, total_rows, duplicate_count, total_missing, constant_columns)

    st.markdown("### Detected Data Quality Issues")
    if detected_issues:
        issue_display = pd.DataFrame(detected_issues)
        issue_display.columns = ["Issue", "Count", "Recommended Action"]
        st.dataframe(issue_display, use_container_width=True, hide_index=True)
    else:
        st.success("No obvious cleaning issues were detected.")

    _render_ai_plan(df, total_rows, total_columns, total_missing, duplicate_count, constant_columns, column_information, detected_issues)
    _render_approval_section(df, detected_issues)
    _render_last_operation_summary()


def _build_column_information(df, total_rows):
    column_information = []
    for column in df.columns:
        series = df[column]
        missing_count = int(series.isna().sum())
        unique_count = int(series.nunique(dropna=True))

        if pd.api.types.is_numeric_dtype(series):
            data_role = "Numeric"
        elif pd.api.types.is_datetime64_any_dtype(series):
            data_role = "Date / Time"
        elif pd.api.types.is_bool_dtype(series):
            data_role = "Boolean"
        else:
            data_role = "Categorical / Text"

        column_information.append(
            {
                "column": column,
                "dtype": str(series.dtype),
                "role": data_role,
                "missing": missing_count,
                "missing_percentage": round(missing_count / total_rows * 100, 2) if total_rows else 0,
                "unique_values": unique_count,
            }
        )
    return column_information


def _detect_issues(df, total_rows, duplicate_count, total_missing, constant_columns):
    detected_issues = []

    if duplicate_count > 0:
        detected_issues.append(
            {"issue": "Duplicate rows", "count": duplicate_count, "recommendation": "Remove duplicate rows"}
        )

    if total_missing > 0:
        for column in df.columns:
            missing_count = int(df[column].isna().sum())
            if missing_count == 0:
                continue

            missing_percentage = missing_count / total_rows * 100

            if missing_percentage >= 50:
                recommendation = (
                    "Consider dropping the column or investigating why most values are missing"
                )
            elif pd.api.types.is_numeric_dtype(df[column]):
                recommendation = "Consider filling missing values using the median"
            else:
                recommendation = "Consider filling missing values using the mode"

            detected_issues.append(
                {
                    "issue": f"Missing values in '{column}'",
                    "count": missing_count,
                    "recommendation": recommendation,
                }
            )

    for column in constant_columns:
        detected_issues.append(
            {
                "issue": f"Constant column '{column}'",
                "count": int(df[column].nunique(dropna=False)),
                "recommendation": "Consider dropping the column",
            }
        )

    return detected_issues


def _render_ai_plan(df, total_rows, total_columns, total_missing, duplicate_count, constant_columns, column_information, detected_issues):
    generate_cleaning_plan = st.button("Generate AI Cleaning Plan", key="generate_ai_cleaning_plan")

    if generate_cleaning_plan:
        cleaning_context = {
            "dataset": {"rows": total_rows, "columns": total_columns, "column_names": df.columns.tolist()},
            "quality": {
                "missing_values": total_missing,
                "duplicate_rows": duplicate_count,
                "constant_columns": constant_columns,
            },
            "columns": column_information,
            "detected_issues": detected_issues,
        }

        cleaning_context_json = json.dumps(cleaning_context, default=str)

        cleaning_prompt = f"""
You are an expert Data Cleaning Assistant.

Analyze the following dataset information.

DATASET:
{cleaning_context_json}

Create a practical cleaning plan.

For every recommended action provide:

1. Issue
2. Column
3. Recommended Action
4. Reason
5. Risk
6. Priority

Allowed actions are ONLY:

- Remove Duplicate Rows
- Fill Missing Values
- Drop Missing Rows
- Drop Constant Columns
- Convert Numeric Column
- No Action

Important rules:

- Do not invent problems.
- Do not recommend an action if there is no evidence for it.
- Do not modify the dataset.
- Do not assume that missing values should always be deleted.
- For numeric missing values, consider median imputation.
- For categorical missing values, consider mode imputation.
- If a column has a very high missing percentage, consider dropping
the column rather than blindly imputing it.
- Explain the potential risk of every destructive operation.
- Prefer conservative cleaning decisions.

Return a concise professional report.
"""

        llm = get_groq_llm(temperature=0.1)
        if llm is not None:
            try:
                with st.spinner("AI is analyzing the dataset and preparing a cleaning plan..."):
                    response = llm.invoke(cleaning_prompt)
                st.session_state["ai_cleaning_plan"] = extract_content(response)
            except Exception as e:
                st.error(f"Unable to generate AI cleaning plan: {e}")

    if st.session_state.get("ai_cleaning_plan"):
        st.markdown("### AI Recommended Cleaning Plan")
        st.markdown(st.session_state.ai_cleaning_plan)
        st.info("Review the recommendations carefully. The AI plan does not modify your dataset.")


def _render_approval_section(df, detected_issues):
    if not detected_issues:
        return

    st.markdown("### Apply Recommended Cleaning")
    st.caption("Select an operation below and explicitly approve it before modifying the dataset.")

    approved_operation = st.selectbox(
        "Cleaning Operation",
        [
            "Select an operation",
            "Remove Duplicate Rows",
            "Fill Missing Values",
            "Drop Rows With Missing Values",
            "Drop Constant Columns",
        ],
        key="step13_cleaning_operation",
    )

    if approved_operation == "Select an operation":
        return

    st.warning(
        "This operation will modify the current dataset. Your Step 10 undo/reset "
        "options remain available."
    )

    approve_cleaning = st.checkbox(
        "I have reviewed and approve this cleaning operation.", key="step13_approve_cleaning"
    )

    apply_cleaning = st.button("Apply Approved Cleaning", key="step13_apply_cleaning")

    if not apply_cleaning:
        return

    if not approve_cleaning:
        st.error("Please approve the cleaning operation before applying it.")
        return

    st.session_state.tabular_previous_df = df.copy()
    rows_before = len(df)
    columns_before = len(df.columns)

    if approved_operation == "Remove Duplicate Rows":
        df = df.drop_duplicates().reset_index(drop=True)

    elif approved_operation == "Drop Rows With Missing Values":
        df = df.dropna().reset_index(drop=True)

    elif approved_operation == "Drop Constant Columns":
        columns_to_drop = [c for c in df.columns if df[c].nunique(dropna=False) <= 1]
        df = df.drop(columns=columns_to_drop)

    elif approved_operation == "Fill Missing Values":
        for column in df.columns:
            if not df[column].isna().any():
                continue
            if pd.api.types.is_numeric_dtype(df[column]):
                median_value = df[column].median()
                df[column] = df[column].fillna(median_value)
            else:
                mode_values = df[column].mode(dropna=True)
                if not mode_values.empty:
                    df[column] = df[column].fillna(mode_values.iloc[0])

    st.session_state.tabular_df = df.copy()

    st.session_state["step13_last_cleaning"] = {
        "operation": approved_operation,
        "rows_before": rows_before,
        "rows_after": len(df),
        "columns_before": columns_before,
        "columns_after": len(df.columns),
    }

    st.success(f"{approved_operation} applied successfully.")
    st.rerun()


def _render_last_operation_summary():
    if "step13_last_cleaning" not in st.session_state:
        return

    last_cleaning = st.session_state["step13_last_cleaning"]

    st.markdown("### Last Cleaning Operation")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Operation", last_cleaning["operation"])
    with c2:
        st.metric("Rows", f'{last_cleaning["rows_before"]:,} → {last_cleaning["rows_after"]:,}')
    with c3:
        st.metric("Columns", f'{last_cleaning["columns_before"]:,} → {last_cleaning["columns_after"]:,}')
