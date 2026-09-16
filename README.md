# How Stacks Works

This describes what actually happens inside the app when you use it —
not the code layout (see `README.md` for that), but the behavior: what
happens to your data, step by step, from upload to answer.

The app has two independent halves that don't share data with each
other: **Tabular Data** (CSV/Excel) and **Documents** (PDF/Word/text/etc.,
searched via RAG). Pick the section below for what you're using.

---

# Part 1: Tabular Data (CSV / Excel)

## 1. Upload

You upload a `.csv`, `.xlsx`, or `.xls` file. The app:

1. Parses it into a table (pandas DataFrame).
2. Validates it — rejects it (with a message, not a crash) if the file
   is empty, unreadable, or an unsupported format.
3. Warns you (but doesn't block you) if it's over ~2 million rows, since
   some operations below get slow at that scale.
4. Remembers this table as "the current dataset" for the rest of your
   session.

**Important behavior:** if you upload a *different* file later, the app
detects that (by filename + size) and wipes anything tied to the
previous dataset — cleaned data, AI reports, chat history — so you don't
accidentally see leftovers from the old file mixed with the new one. If
you re-upload the *same* file (e.g. the page just reran), nothing resets;
your work is preserved.

## 2. What gets computed once, up front

Before any page renders, the app scans your table once and works out:
which columns are numeric, which are categorical/text, which are
dates, how many missing values and duplicate rows exist, and which
columns are "constant" (only one unique value — usually a sign the
column isn't useful). Every page below uses this same information rather
than recalculating it, so the numbers are always consistent across pages.

## 3. The 20 pages, grouped

### 🔍 Explore (read-only — nothing here changes your data)

- **Dataset Overview** — row/column counts, a preview of the first 100
  rows, and a per-column data-type breakdown.
- **Data Quality** — missing values, duplicate rows, and constant
  columns, with a plain-language verdict ("Excellent" / "Attention
  required").
- **Statistical Analysis** — mean/median/std/percentiles for every
  numeric column, plus a deep-dive on one column at a time.
- **Exploratory Analytics** — distributions, top categorical values,
  a correlation matrix across numeric columns, grouped aggregations
  (e.g. "average X by Y"), and top/bottom-N record rankings.
- **Automatic Visualization** — the app looks at what column types you
  have and offers only the charts that make sense (histograms, trend
  lines, scatter plots, bar charts, correlation heatmaps).
- **Anomaly Detection** — flags statistical outliers per column using
  either the IQR method or Z-scores, plus a one-click scan across every
  numeric column at once.

### 🧹 Clean & Transform (these DO change your working data)

- **Data Cleaning** — detects issues (missing values, duplicates,
  constant columns) and lets you preview a fix before applying it:
  remove duplicates, fill missing values (mean/median/mode/"Unknown"),
  drop incomplete rows, drop constant columns, or force a column to
  numeric. Has undo (one step back) and a full reset to the originally
  uploaded file.
- **Dataset Profiling** — a deeper automatic report: a 0–100 "health
  score," per-column roles and cardinality, skewness, and outlier counts.
- **Data Transformation** — rename columns, convert types (int/float/
  string/boolean/datetime), build a calculated column from two numeric
  columns (+/−/×/÷), extract date parts (year/month/day/etc.), normalize
  or standardize a numeric column, and text case/whitespace cleanup.

**Once you clean or transform something here, every other page — Explore,
AI, Export — sees the updated data, not the original upload.** This is
one shared working copy, not 20 independent views.

### 🤖 AI Assistants (send a summary of your data to Groq — see note below)

- **AI Data Quality Report** — turns the Data Quality findings into a
  business-readable report with severity ratings (HIGH/MEDIUM/LOW).
- **AI Cleaning Assistant** — proposes a cleaning plan in plain language;
  nothing is applied until you explicitly select an operation and check
  an approval box.
- **Natural Language SQL** — type a question in English, the AI writes
  a DuckDB SQL query against your data, and it's checked against a
  keyword blocklist (only `SELECT`/`WITH`, no `DROP`/`DELETE`/etc.)
  before it's allowed to run.
- **AI Data Analyst** — free-form Q&A ("what are the biggest risks in
  this data?") answered against a profile of your dataset's shape and
  statistics.
- **GPT Insights** — generates a fixed number of structured
  Finding → Evidence → Recommendation cards.
- **AI Chart Recommendation** — describe what you want to see; the AI
  picks a chart type and columns, which are then validated against your
  actual schema before anything renders (it can't invent columns that
  don't exist).
- **AI Transformation (natural language)** — describe a transformation
  in English; the AI explains what it *would* do, but doesn't execute
  arbitrary code — actual transformations still happen through the
  Data Transformation page's fixed set of operations.
- **Business Insights** — answers a specific business question with an
  executive-style Findings/Risks/Recommendations/Confidence writeup.
- **AI Analyst Chat** — a running conversation about your dataset,
  remembering the last 10 exchanges as context.

> **What's actually sent to the AI:** column names, data types, summary
> statistics, and a small sample of rows (typically 10–20) — not
> necessarily your whole file. Every AI page shows a one-line notice
> before you use it. Don't use these features on data you can't share
> with a third-party API (Groq).

### 📤 Export

- **Export & Reports** — download the current (possibly cleaned)
  dataset as CSV, and generate/download a compiled plain-text report
  covering quality, statistics, and any AI outputs you've already
  generated elsewhere in the session.

### 🏠 Overview

- **Executive Dashboard** — a final summary: health score, which AI
  features you've run this session, and one-click download/reset
  controls (including a "clear AI session" button that wipes generated
  reports without touching your actual data).

## 4. What doesn't persist

Everything above lives in the browser session only. Close the tab or
restart the app, and you're back to nothing uploaded — nothing is
written to a database. The only thing that touches disk is a CSV/report
you explicitly click "Download" for.

---

# Part 2: Documents (non-tabular — PDF, Word, text, etc.)

This is a separate system: retrieval-augmented generation (RAG). Instead
of running code against your data like the Tabular tab, it converts your
documents into searchable "meaning," then asks an AI to answer questions
using only the relevant pieces it finds.

## 1. Upload & loading

You upload one or more files. Supported types: PDF, TXT, CSV, Excel,
Word (`.docx`), JSON, Markdown. Each format is read differently:

- **PDF / Word / plain text** — extracted as continuous text.
- **CSV / Excel** — turned into one record per row (each row becomes its
  own searchable unit, not one giant blob of text).
- **JSON** — one record per list item if it's a list, or the whole
  structure as one unit otherwise.

Multiple files load in parallel (up to 8 at once) for speed. A file that
fails to load doesn't block the others — you get a per-file success/error
status.

## 2. Chunking & embedding

Long documents (PDF, Word, text, Markdown) are split into overlapping
~1000-character chunks so a single question doesn't require the AI to
digest an entire 50-page PDF at once. Row/record-based formats (CSV,
JSON, Excel) are **not** split further — a single row is already a
sensible atomic unit and splitting it further would fragment it for no
benefit.

Every chunk is converted into a vector embedding (a numeric fingerprint
of its meaning) using a local embedding model (`all-MiniLM-L6-v2`) —
this runs on your machine, not sent to any external API.

## 3. Storage

Embeddings go into a FAISS vector index; the chunk text and source
filename go into an accompanying metadata store. Both are saved to disk
(`faiss_store/`), so your indexed library survives an app restart — you
don't need to re-upload and re-index everything every session.

## 4. Removing a document

Deleting a filed document removes its chunks from the index. Depending
on which version of the vectorstore code you're running, this either:
rebuilds the entire index from every remaining file on disk (safe, but
slower as your library grows), or surgically removes just that file's
chunks from memory without touching anything else (faster — see
`src_patches/` in the code architecture doc if this hasn't been applied
yet).

## 5. Asking a question

This is the actual "RAG" part, and it happens in three stages:

1. **Retrieval** — your question is compared against every stored chunk
   two ways at once: vector similarity (meaning-based) and BM25 keyword
   search (exact-term-based), then the two rankings are merged
   (reciprocal rank fusion) so both "semantically similar" and
   "contains the exact words" results surface. The merged candidates are
   then re-ordered by a cross-encoder re-ranking model for a final,
   more accurate top-K.
2. **Prompting** — the top-K chunks are assembled into a prompt that
   tells the AI: *answer using only this context; say so if the answer
   isn't covered; cite sources by filename.*
3. **Generation** — the prompt goes to Groq's API, and the answer streams
   back into the chat in real time rather than appearing all at once.

The filenames the answer drew from are shown as source chips underneath
the answer, so you can verify where a claim came from.

## 6. What happens if there's no good match

If nothing in your indexed documents is relevant to the question, you
get "No relevant documents found" instead of an AI-invented answer — the
system doesn't fall back to the model's general knowledge.

## 7. Rate limits

If Groq's daily free-tier limit is hit mid-conversation, you get a clear
"Daily usage limit reached" message (with a retry-time estimate when
Groq provides one) instead of a raw stack trace.

---

## The one thing that's shared between the two tabs

Nothing, by design. A Tabular Data upload has no effect on your indexed
Documents library, and vice versa — they use completely separate storage
(`session_state.tabular_df` vs. `faiss_store/` on disk) and separate AI
call paths (dataset-summary prompts vs. retrieved-chunk prompts).


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
