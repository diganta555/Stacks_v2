"""
The "Documents" tab: unstructured/non-tabular document ingestion (left
panel) and retrieval-augmented search over the filed documents (right
panel).
"""

import os
import shutil
from pathlib import Path

import streamlit as st

from src.data_loader import LOADER_REGISTRY
from services.rag_service import rebuild_from_disk


def render_documents_tab(rag, upload_dir: Path) -> None:
    st.markdown(
        '<div class="stacks-label">Unstructured / Non-Tabular Documents</div>',
        unsafe_allow_html=True,
    )

    col_upload, col_search = st.columns([1, 1.4], gap="large")

    with col_upload:
        sources = _render_upload_panel(rag, upload_dir)

    with col_search:
        _render_search_panel(rag, sources)


def _render_upload_panel(rag, upload_dir: Path):
    panel = st.container(border=True)

    with panel:
        st.markdown('<div class="stacks-label">Accessions</div>', unsafe_allow_html=True)

        uploaded = st.file_uploader(
            "Drop files here",
            accept_multiple_files=True,
            label_visibility="collapsed",
            key="document_uploader",
        )

        chips = "".join(
            f'<span class="stacks-chip stacks-chip-ext">{ext}</span>'
            for ext in sorted(LOADER_REGISTRY.keys())
        )
        st.markdown(f'<div style="margin:0.6rem 0 0.4rem">{chips}</div>', unsafe_allow_html=True)

        if uploaded and st.button("File these documents", type="primary", key="file_documents"):
            _ingest_uploaded_files(rag, upload_dir, uploaded)

        st.divider()
        st.markdown('<div class="stacks-label">Indexed sources</div>', unsafe_allow_html=True)

        sources = rag.vectorstore.list_sources()

        if not sources:
            st.caption("Nothing filed yet.")
        else:
            _render_source_list(rag, upload_dir, sources)

        return sources


def _ingest_uploaded_files(rag, upload_dir: Path, uploaded) -> None:
    new_documents = []
    results = []

    with st.spinner(f"Filing {len(uploaded)} file(s)…"):
        for f in uploaded:
            ext = Path(f.name).suffix.lower()

            if ext not in LOADER_REGISTRY:
                results.append((f.name, "skipped", f"unsupported extension {ext}"))
                continue

            dest = upload_dir / f.name
            dest.write_bytes(f.getbuffer())

            try:
                loader_fn, label = LOADER_REGISTRY[ext]
                docs = loader_fn(dest)

                for d in docs:
                    d.metadata.setdefault("source", str(dest))
                    d.metadata.setdefault("file_type", label)

                new_documents.extend(docs)
                results.append((f.name, "filed", None))

            except Exception as e:
                results.append((f.name, "error", str(e)))

        if new_documents:
            rag.ingest_new_documents(new_documents)

    for name, status, reason in results:
        if status == "filed":
            st.success(f"{name} — filed")
        else:
            st.error(f"{name} — {status}: {reason}")


def _render_source_list(rag, upload_dir: Path, sources) -> None:
    for i, src in enumerate(sources, 1):
        name = os.path.basename(src)

        c1, c2 = st.columns([3.2, 1.3])
        c1.write(f"`{i:02d}` {name}")

        if name != "unknown" and c2.button("remove", key=f"del-{i}-{name}", type="secondary"):
            for p in upload_dir.glob(name):
                if p.is_file():
                    p.unlink()

            # If src/vectorstore.py has the remove_by_source() patch
            # applied (see src_patches/), removing one document only
            # filters the already-computed embeddings and rebuilds the
            # index structure — no re-embedding of the rest of the
            # library. Without the patch, falls back to the original
            # behavior of rescanning data/ and rebuilding from scratch.
            if hasattr(rag.vectorstore, "remove_by_source"):
                rag.vectorstore.remove_by_source(src)
                rag.vectorstore.save()
            else:
                rebuild_from_disk(rag)

            st.rerun()

    if st.button("Clear entire library", type="secondary", key="clear_library"):
        if upload_dir.exists():
            shutil.rmtree(upload_dir)

        upload_dir.mkdir(parents=True, exist_ok=True)

        rebuild_from_disk(rag)
        st.rerun()


def _render_search_panel(rag, sources) -> None:
    panel = st.container(border=True)

    with panel:
        st.markdown('<div class="stacks-label">Reading Room</div>', unsafe_allow_html=True)

        has_docs = rag.vectorstore.index is not None and rag.vectorstore.index.ntotal > 0

        if has_docs:
            st.success(f"{len(sources)} source(s) filed — ready to ask")
        else:
            st.info("Upload a document to get started")

        query = st.text_input(
            "Ask something about your documents…", disabled=not has_docs, key="document_query"
        )

        col_topk, col_model = st.columns([1, 1])

        with col_topk:
            top_k = st.number_input(
                "Passages to consider", min_value=1, max_value=20, value=5, key="document_top_k"
            )

        with col_model:
            model_options = {
                "GPT OSS 20B — Balanced": "openai/gpt-oss-20b",
                "GPT OSS 120B — High Quality": "openai/gpt-oss-120b",
            }
            model_choice = st.selectbox(
                "Model", list(model_options.keys()), index=0, key="document_model"
            )

        selected_model = model_options[model_choice]
        rag.set_model(selected_model)

        if st.button("Search", disabled=not has_docs, key="document_search") and query:
            _run_search(rag, query, top_k)


def _run_search(rag, query: str, top_k: int) -> None:
    st.markdown("**Answer**")

    answer_placeholder = st.empty()
    full_answer = ""
    found_sources = []
    error_event = None

    for event in rag.stream_search_and_summarize(query, top_k=top_k):
        if event["type"] == "answer_chunk":
            full_answer += event["text"]
            answer_placeholder.markdown(full_answer)
        elif event["type"] == "sources":
            found_sources = event["sources"]
        elif event["type"] == "error":
            error_event = event

    if error_event:
        answer_placeholder.empty()
        if error_event["kind"] == "rate_limit":
            st.warning(f"⏳ **{error_event['title']}** — {error_event['message']}")
        else:
            st.error(f"⚠️ **{error_event['title']}** — {error_event['message']}")

    elif found_sources:
        chips = "".join(f'<span class="stacks-chip">{s}</span>' for s in found_sources)
        st.markdown(f"**Sources:** {chips}", unsafe_allow_html=True)
