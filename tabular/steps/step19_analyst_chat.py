"""Dataset-Aware AI Analyst Chat — conversational Q&A grounded in dataset context."""

import json

import pandas as pd
import streamlit as st

from tabular.context import DatasetContext
from services.groq_service import get_groq_llm, extract_content
from config import AI_PRIVACY_NOTICE


def render(df: pd.DataFrame, ctx: DatasetContext, tabular_file=None) -> None:
    st.markdown("## Dataset-Aware AI Analyst Chat")
    st.caption("Ask questions about your dataset using a conversational AI data analyst.")
    st.caption(AI_PRIVACY_NOTICE)

    if df is None or df.empty:
        st.info("Upload a dataset to start chatting with the AI Data Analyst.")
        return

    if "step19_chat_history" not in st.session_state:
        st.session_state["step19_chat_history"] = []

    chat_dataset_summary = {
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": df.columns.tolist(),
        "data_types": {column: str(df[column].dtype) for column in df.columns},
        "numeric_columns": df.select_dtypes(include="number").columns.tolist(),
        "categorical_columns": df.select_dtypes(include=["object", "category"]).columns.tolist(),
        "missing_values": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
    }
    chat_sample = df.head(10).to_dict(orient="records")

    c1, c2 = st.columns([5, 1])
    with c1:
        st.markdown("### Ask Your Data")
    with c2:
        if st.button("Clear Chat", key="step19_clear_chat"):
            st.session_state["step19_chat_history"] = []
            st.rerun()

    for message in st.session_state["step19_chat_history"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_question = st.chat_input("Ask something about your dataset...", key="step19_chat_input")

    if user_question:
        st.session_state["step19_chat_history"].append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)

        _answer_question(user_question, chat_dataset_summary, chat_sample)

    st.markdown("### Suggested Questions")
    q1, q2, q3 = st.columns(3)
    with q1:
        st.info("What are the main data-quality issues?")
    with q2:
        st.info("Which numeric columns have the highest values?")
    with q3:
        st.info("Give me the most important business insight.")


def _answer_question(user_question, chat_dataset_summary, chat_sample):
    conversation_history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state["step19_chat_history"][-10:]
    ]

    dataset_context_json = json.dumps(
        {"dataset_summary": chat_dataset_summary, "sample_data": chat_sample}, default=str
    )
    conversation_json = json.dumps(conversation_history, default=str)

    analyst_prompt = f"""
You are an expert AI Data Analyst.

You are answering questions about the user's current dataset.

DATASET CONTEXT:
{dataset_context_json}

RECENT CONVERSATION:
{conversation_json}

USER'S CURRENT QUESTION:
{user_question}

Instructions:

1. Answer using the dataset context whenever possible.
2. Maintain context from previous messages.
3. Do not invent values or columns.
4. Do not claim calculations that were not performed.
5. Clearly state when the available dataset information
is insufficient.
6. Distinguish between observations and recommendations.
7. Use numbers from the dataset when available.
8. Keep the answer concise but useful.
9. If the user asks for a business recommendation,
explain the reasoning.
10. Never execute Python code.
11. Never modify the dataset.

The user expects you to behave like a professional
data analyst who understands the uploaded dataset.
"""

    llm = get_groq_llm(temperature=0.1)
    if llm is None:
        return

    try:
        with st.chat_message("assistant"):
            with st.spinner("Analyzing your dataset..."):
                response = llm.invoke(analyst_prompt)
            answer = extract_content(response)
            st.markdown(answer)

        st.session_state["step19_chat_history"].append({"role": "assistant", "content": answer})

    except Exception as e:
        st.error(f"Unable to answer the question: {e}")
