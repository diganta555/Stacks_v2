"""
Central defaults. Previously "faiss_store", "data", "openai/gpt-oss-20b",
etc. were repeated as string literals across several files — changing any
of them meant hunting through the codebase. Now there's one place.
"""

# RAG / vectorstore
FAISS_PERSIST_DIR = "faiss_store"
DOCUMENTS_DATA_DIR = "data"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Groq
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"

# Tabular upload guardrails
MAX_UPLOAD_ROWS = 2_000_000
MAX_UPLOAD_ROWS_WARNING = (
    "This dataset has {rows:,} rows, which is large enough that some "
    "operations (correlation, profiling, AI summaries) may be slow. "
    "Consider sampling it down if you hit performance issues."
)

# Shown before any feature that sends dataset content to Groq's API
AI_PRIVACY_NOTICE = (
    "🔒 This sends a sample of your dataset (column names, summary "
    "statistics, and a few example rows) to Groq's API to generate this "
    "response. Avoid using this feature on data you can't share externally."
)
