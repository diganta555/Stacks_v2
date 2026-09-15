"""
Shared helper for creating a ChatGroq client.

In the original single-file app this exact block (read GROQ_API_KEY /
GROQ_MODEL from the environment, error + st.stop() if missing, construct
ChatGroq) was copy-pasted into ~10 different steps. Centralizing it here
means a future change (e.g. switching providers, adding retries) only
needs to happen once.
"""

import os
from typing import Optional

import streamlit as st

from config import DEFAULT_GROQ_MODEL


def get_groq_llm(temperature: float = 0.0):
    """Returns a configured ChatGroq client, or None (after showing an
    st.error) if GROQ_API_KEY isn't set. Callers should check for None
    and stop / return early."""

    groq_api_key = os.getenv("GROQ_API_KEY")

    if not groq_api_key:
        st.error(
            "GROQ_API_KEY was not found in your .env file."
        )
        return None

    groq_model = os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)

    from langchain_groq import ChatGroq

    return ChatGroq(
        model=groq_model,
        temperature=temperature,
        api_key=groq_api_key,
    )


def extract_content(response) -> str:
    """LLM responses are sometimes a message object (.content) and
    sometimes a plain string, depending on call path. Normalize here."""
    return response.content if hasattr(response, "content") else str(response)
