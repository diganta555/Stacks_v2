"""AI Natural Language Data Transformation — describe a change, AI proposes a
plan. Execution is intentionally disabled; points the user to Step 14 instead."""

import json

import pandas as pd
import streamlit as st

from tabular.context import DatasetContext
from services.groq_service import get_groq_llm, extract_content
from config import AI_PRIVACY_NOTICE


def render(df: pd.DataFrame, ctx: DatasetContext, tabular_file=None) -> None:
    st.markdown("## AI Natural Language Data Transformation")
    st.caption(
        "Describe a data transformation in natural language and let AI create "
        "a safe transformation plan."
    )
    st.caption(AI_PRIVACY_NOTICE)

    if df is None or df.empty:
        st.info("Upload a dataset to use AI-powered transformations.")
        return

    transformation_request = st.text_area(
        "Describe what you want to change",
        placeholder="Example: Create a total_sales column using price multiplied by quantity.",
        key="step16_transformation_request",
    )

    if st.button("Generate Transformation Plan", key="step16_generate_plan"):
        if not transformation_request.strip():
            st.warning("Please describe the transformation you want to perform.")
        else:
            dataset_context = {
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist(),
                "data_types": {column: str(df[column].dtype) for column in df.columns},
                "sample_data": df.head(5).to_dict(orient="records"),
            }
            dataset_context_json = json.dumps(dataset_context, default=str)

            transformation_prompt = f"""
You are an expert data transformation assistant.

The user wants to transform a dataset.

USER REQUEST:
{transformation_request}

DATASET INFORMATION:
{dataset_context_json}

Analyze the request and create a safe transformation plan.

Your response must contain:

1. Understanding of the request
2. Columns involved
3. Transformation logic
4. Expected output
5. Potential risks

Rules:

- Do not invent columns.
- Only use columns that exist in the dataset.
- Do not delete existing columns.
- Do not modify the dataset.
- Do not execute code.
- If the request is ambiguous, clearly state the ambiguity.
- Prefer creating a new column instead of overwriting an existing column.
- Do not expose Python code.
"""

            llm = get_groq_llm(temperature=0.1)
            if llm is not None:
                try:
                    with st.spinner("AI is analyzing your transformation request..."):
                        response = llm.invoke(transformation_prompt)
                    st.session_state["step16_transformation_plan"] = extract_content(response)
                    st.success("Transformation plan generated.")
                except Exception as e:
                    st.error(f"Unable to generate transformation plan: {e}")

    plan = st.session_state.get("step16_transformation_plan")
    if not plan:
        return

    st.markdown("### AI Transformation Plan")
    st.markdown(plan)
    st.warning("The AI plan is only a recommendation. Review it before applying any transformation.")

    approve_transformation = st.checkbox(
        "I have reviewed and approve this transformation.", key="step16_approve_transformation"
    )
    apply_transformation = st.button("Apply Approved Transformation", key="step16_apply_transformation")

    if not apply_transformation:
        return

    if not approve_transformation:
        st.error("Please approve the transformation before applying it.")
        return

    st.info("Automatic execution of arbitrary AI-generated code is disabled for safety.")
    st.markdown("### Supported Transformations")
    st.write("Use Step 14 for the actual supported transformations.")
    st.info(
        "In the next implementation phase, the AI plan can be mapped to a strict "
        "whitelist of transformation operations."
    )
