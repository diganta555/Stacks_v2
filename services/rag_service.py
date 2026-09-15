"""
Wraps the cached RAGSearch resource and the "rebuild index from disk"
operation used by the Documents tab.
"""

import streamlit as st

from src.data_loader import load_all_documents
from src.search import RAGSearch
from config import DOCUMENTS_DATA_DIR


@st.cache_resource(show_spinner="Loading models and index...")
def get_rag() -> RAGSearch:
    return RAGSearch()


def rebuild_from_disk(rag: RAGSearch, data_dir: str = DOCUMENTS_DATA_DIR) -> None:
    """Wipes the in-memory index and rebuilds it from whatever documents
    currently exist on disk (used after a delete / clear-library action)."""
    rag.vectorstore.index = None
    rag.vectorstore.metadata = []
    docs = load_all_documents(data_dir)
    if docs:
        rag.vectorstore.build_from_documents(docs)
    else:
        rag.vectorstore.save()
