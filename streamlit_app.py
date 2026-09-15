"""
Streamlit version of Stacks — no separate FastAPI backend needed.

Run locally with:
    python -m streamlit run streamlit_app.py --server.port 8080

Local environment:
    Create a .env file in the project root:

        GROQ_API_KEY=gsk_...
        GROQ_MODEL=openai/gpt-oss-20b

For Streamlit Cloud deployment, the same variables can be configured
through Streamlit Secrets.

--------------------------------------------------------------------
This file is intentionally thin. It only wires together:
  1. Page config + global styling
  2. Session-state initialization
  3. The cached RAG resource
  4. The two top-level tabs (Tabular Data / Documents)

All actual feature logic lives in tabular/ and documents/.
--------------------------------------------------------------------
"""

from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Stacks V2 — Document Search",
    page_icon="📚",
    layout="wide",
)

from dotenv import load_dotenv  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

from state import init_session_state  # noqa: E402
from ui.styles import inject_global_styles  # noqa: E402
from services.rag_service import get_rag  # noqa: E402
from tabular.tab import render_tabular_tab  # noqa: E402
from documents.tab import render_documents_tab  # noqa: E402

UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

init_session_state()
inject_global_styles()

try:
    rag = get_rag()
except RuntimeError as e:
    st.error(str(e))
    st.stop()

tabular_tab, documents_tab = st.tabs(["📊 Tabular Data", "📚 Documents"])

with tabular_tab:
    render_tabular_tab()

with documents_tab:
    render_documents_tab(rag, UPLOAD_DIR)
