# Stacks — Architecture

Stacks is a Streamlit app with two tabs:

- **Tabular Data** — upload a CSV/Excel file and run it through 20 analysis,
  cleaning, transformation, and AI-powered steps.
- **Documents** — upload PDFs/text/etc., index them into a FAISS vector
  store, and ask questions over them (RAG) via Groq.

This file describes how the codebase is organized and why. It was
originally a single ~6,000-line `streamlit_app.py`; this document reflects
the componentized version.

---

## Directory layout

```
streamlit_app.py           Entry point: page config, global styles, session
                            init, cached RAG resource, top-level tabs.
state.py                   One-time st.session_state defaults at app startup.
config.py                  Centralized constants (paths, model names,
                            upload guardrails, the AI privacy notice).

ui/
  styles.py                 All CSS + the hero banner markup, injected once.

services/
  rag_service.py             @st.cache_resource-wrapped RAGSearch instance,
                             + rebuild_from_disk() for the Documents tab.
  groq_service.py             Shared ChatGroq client factory + response
                             content extraction. Used by every AI step.

tabular/
  tab.py                      Orchestrates the Tabular Data tab: sidebar →
                             upload → dataset_state → context → router.
  sidebar.py                   Sidebar UI: grouped section/page navigation
                             + "currently loaded dataset" widgets.
  loader.py                     Raw CSV/Excel upload widget + parsing/
                             validation (no session-state logic here).
  dataset_state.py                Owns the *lifecycle* of "the current
                             dataset" in session_state — see below.
  context.py                       Computes derived values (column roles,
                             quality_df, constant columns, etc.) ONCE per
                             run, shared by every step via `ctx`.
  router.py                         Maps each sidebar label to its step
                             module's render() function.
  steps/
    step01_overview.py … step20_executive_dashboard.py
                             One file per sidebar page. Each exposes:
                                 render(df, ctx, tabular_file) -> None

documents/
  tab.py                      The Documents (RAG) tab: upload/index panel
                             + search panel, calls into services/rag_service.

src/                        NOT part of this delivery — this is your
                            existing RAG backend (data_loader.py,
                            search.py, vectorstore.py, embedding.py).
                            tabular/ and documents/ only ever import from
                            it; nothing here modifies it.

src_patches/                Optional, hand-reviewed upgrades to two of
                            your src/ files (embedding.py, vectorstore.py).
                            NOT applied automatically — see "src/ patches"
                            below.
```

---

## Request flow (Tabular Data tab)

```
streamlit_app.py
  └─ render_tabular_tab()                     [tabular/tab.py]
       ├─ render_sidebar()                    [tabular/sidebar.py]
       │    → returns the selected page label, e.g. "📈 Statistical Analysis"
       │
       ├─ render_uploader()                   [tabular/loader.py]
       │    → returns the raw Streamlit UploadedFile (or None)
       │
       ├─ sync_with_uploaded_file(file)       [tabular/dataset_state.py]
       │    → parses the file ONLY if it's a genuinely new upload
       │      (by name+size); otherwise returns the existing
       │      st.session_state.tabular_df, which may already be
       │      cleaned/transformed by a previous step
       │
       ├─ build_context(df)                   [tabular/context.py]
       │    → DatasetContext: numeric_columns, categorical_columns,
       │      date_columns, missing_values, duplicate_rows,
       │      constant_columns, quality_df
       │
       └─ dispatch(label, df, ctx, file)      [tabular/router.py]
            → looks up label in ROUTES, calls that step's render()
```

Every step module is a pure function of `(df, ctx, tabular_file)` plus
whatever it reads/writes in `st.session_state` for its own widgets. Steps
never re-parse the uploaded file themselves — `df` is always already the
current working copy.

## Request flow (Documents tab)

```
streamlit_app.py
  └─ get_rag()                                [services/rag_service.py]
       → @st.cache_resource: one RAGSearch instance for the whole
         session (loads the embedding model + FAISS index once)
  └─ render_documents_tab(rag, upload_dir)    [documents/tab.py]
       ├─ upload panel → writes files to disk, calls
       │    rag.ingest_new_documents(docs)
       ├─ source list → delete button calls rag.vectorstore
       │    .remove_by_source() if available (src_patches applied),
       │    else falls back to rebuild_from_disk()
       └─ search panel → rag.stream_search_and_summarize(query)
            → yields {"type": "answer_chunk"|"sources"|"error", ...}
```

---

## Key design decisions

**Why a `DatasetContext` instead of passing raw values around?**
Several derived values (column roles, `quality_df`, constant columns) used
to be computed inside individual steps — in one case *only* inside one
step, so any other step referencing it would crash with `NameError` if you
hadn't visited that step first in the same session. `context.py` computes
everything once per render and passes it down, so every step sees
consistent data and nothing is silently missing.

**Why does `dataset_state.py` exist separately from `loader.py`?**
`loader.py` only knows how to turn an `UploadedFile` into a validated
DataFrame — it has no opinion on session state. `dataset_state.py` owns
the *lifecycle*: detecting a new upload vs. a rerun of the same file,
resetting stale AI reports/cleaning history when the file actually
changes, and making sure cleaning/transformation steps' edits are visible
to every other step (they all read the same `st.session_state.tabular_df`
rather than each re-parsing the file independently).

**Why a `router.py` dict instead of `if/elif` chains?**
The original app's `if navigation == "...":` chain had labels that didn't
match the content they opened (see "Bugs fixed" below) — an easy mistake
to make invisibly in a long `if/elif` chain, hard to audit. A dict from
label → function makes every mapping explicit and greppable in one place,
and a duplicate/missing key is a Python-level error instead of silent
mis-wiring.

**Why is `src_patches/` separate from `src/`?**
`src/` is your code, not generated by this refactor. `src_patches/`
contains two optional, backward-compatible upgrades (model caching,
cheap document removal) that change real behavior — they're left for you
to review and apply deliberately rather than silently overwriting files
you wrote. `documents/tab.py` checks `hasattr(vectorstore,
"remove_by_source")` and works correctly whether or not you've applied
the patch.

**Why is `config.py` separate from `state.py`?**
`config.py` holds constants that never change at runtime (default model
names, directory paths, guardrail thresholds) — the kind of thing you'd
want to grep for in one place. `state.py` only initializes
`st.session_state` keys; it's about runtime state, not configuration.

---

## Adding a new step

1. Create `tabular/steps/step21_my_feature.py` with:
   ```python
   def render(df, ctx, tabular_file=None) -> None:
       ...
   ```
2. Add its sidebar label to the appropriate group in `NAV_GROUPS`
   (`tabular/sidebar.py`).
3. Add `"🆕 My Feature": step21_my_feature.render` to `ROUTES`
   (`tabular/router.py`).

That's it — `tab.py` and `context.py` don't need to change, since every
step receives the same `(df, ctx, tabular_file)` signature.

---

## Bugs fixed during componentization

- **Sidebar labels didn't match their content.** In the original file,
  `if navigation == "...":` gates were wired to the wrong blocks from
  item 6 onward — e.g. clicking "🚨 Anomaly Detection" opened the
  Natural-Language-SQL tool, "🧹 Data Cleaning" matched no block at all,
  and "🤖 AI Data Analyst" matched *two* blocks (both rendered, stacked).
  Every label now maps to exactly one step — see the full mapping
  rationale at the top of `tabular/router.py`.
- **Latent `NameError` on "Dataset Profiling".** It referenced a
  `quality_df` that only existed if you'd visited "Data Quality" first in
  the same session. Now computed once in `context.py` for everyone.
- **Stale data after uploading a new file.** Cleaning file A and then
  uploading file B used to leave A's cleaned data sitting in session
  state. `dataset_state.py` now resets everything scoped to "the current
  dataset" on a genuinely new upload (detected by name + size).
- **Cleaning/transformation didn't reach other steps.** Steps 10/13/14
  edited `session_state.tabular_df`, but every other step re-read the raw
  uploaded file. All steps now read the same working copy.
- **DuckDB keyword filter false-positived on column names** like
  `date_created` (contains "CREATE" as a substring). Now a word-boundary
  regex, so it only matches the actual SQL keyword.

## Still open (bigger changes, not yet done)

- The DuckDB safety check is still a keyword blocklist, not a real SQL
  parser — `sqlglot` would be a more robust (but new-dependency) fix.
- No automated test suite — a good next step would be pytest cases that
  call each step's `render()` with a synthetic DataFrame and a fake
  `st.session_state`.
- `step10_last_cleaning` is read by the Export & Analysis Report step but
  never written by Step 10 (which uses `last_cleaning_summary` instead) —
  harmless (that section of the report just stays empty), not yet wired up.

## Running it

```
python -m streamlit run streamlit_app.py --server.port 8080
```

Requires your existing `src/`, `.env`, `data/`, and `faiss_store/`
alongside this code (see "Directory layout" above — `src/` is
intentionally not included in this delivery).
