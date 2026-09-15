# Stacks — component structure

Your original `streamlit_app.py` (~6,000 lines, everything in one file) has
been split into modules. Drop your existing `src/` folder (with
`data_loader.py` and `search.py`), your `.env`, and your `data/` folder into
this directory and run it exactly as before:

```
python -m streamlit run streamlit_app.py --server.port 8080
```

## Layout

```
streamlit_app.py           # slim entry point — page config, styling, tabs
state.py                   # session_state key initialization

ui/
  styles.py                 # CSS + hero banner markup

services/
  rag_service.py             # cached RAGSearch resource + rebuild-from-disk
  groq_service.py             # shared ChatGroq client + response-content helper

tabular/
  tab.py                      # orchestrates the "Tabular Data" tab
  sidebar.py                   # nav radio + "loaded dataset" widgets
  loader.py                     # upload widget + CSV/Excel validation
  context.py                     # shared derived values (column roles, quality_df, etc.)
  router.py                       # nav label -> step module mapping
  steps/
    step01_overview.py … step20_executive_dashboard.py   # one file per sidebar page

documents/
  tab.py                      # the "Documents" (RAG search) tab
```

Every step module exposes a single `render(df, ctx, tabular_file)` function.
`ctx` is a `DatasetContext` (see `tabular/context.py`) holding things like
`numeric_columns`, `categorical_columns`, `missing_values`, `quality_df`,
etc. — computed once per run instead of being recomputed (or, in one case,
not computed at all) inside individual steps.

## What I fixed along the way (per your go-ahead)

**The sidebar navigation was wired to the wrong content.** In the original
file, each step's content was gated by `if navigation == "...":`, but the
string on that gate didn't match the label your comment said it was for.
From item 6 onward, almost every label opened a different, unrelated
feature — for example clicking **"🚨 Anomaly Detection"** opened the
Natural-Language-to-SQL tool, and **"🧹 Data Cleaning"** matched no block
at all (a dead label, blank page). Separately, **"🤖 AI Data Analyst"**
matched *two* different blocks, so both used to render stacked on one page.

I re-matched each label to the step whose title/content it actually
describes — see the mapping and full explanation at the top of
`tabular/router.py`. Every one of the 20 labels now maps to exactly one
step, and every step is reachable from exactly one label — this fell out
cleanly once corrected, with no leftovers, which is why I'm fairly
confident this was the intended wiring before something went sideways.

**A latent crash was fixed for free.** The old "Dataset Profiling" content
referenced a `quality_df` variable that was only ever created inside the
Data Quality block — if you clicked that page without visiting Data
Quality first in the same session, it would raise `NameError`. `quality_df`
is now computed once in `tabular/context.py` and available to every step.

## Second pass: fixes applied

- **New-file upload no longer leaks stale state.** Uploading dataset B
  after cleaning dataset A used to leave A's cleaned data (and AI
  reports/plans) sitting in session state. `tabular/dataset_state.py` now
  detects a genuinely new upload (by filename + size) and resets
  everything scoped to "the current dataset" — while *keeping* your
  cleaned/transformed data intact across reruns of the *same* file.
- **Cleaning/transformation now propagates everywhere.** This was the
  other half of the same fix: every step now reads
  `st.session_state.tabular_df` as its single source of truth, instead of
  most steps silently re-reading the raw uploaded file while only steps
  10/13/14 saw edits. Clean or transform once, see it on every page.
- **DuckDB keyword filter no longer false-positives on column names.** A
  column called `date_created` used to get incorrectly blocked because
  the filter did a plain substring check for `"CREATE"`. It's now a
  word-boundary regex (`tabular/steps/step06_nl_sql.py`), so
  `date_created` passes and an actual `CREATE TABLE` is still blocked.
  (This is still a keyword blocklist, not a real SQL parser — swapping in
  `sqlglot` to validate the statement's actual type would be a stronger
  long-term fix if you want it.)
- **AI features now disclose what they send.** Every step that sends
  dataset content to Groq's API now shows a one-line notice above the
  input (`config.py`'s `AI_PRIVACY_NOTICE`).
- **Sidebar is now grouped** (`Explore` / `Clean & Transform` /
  `AI Assistants` / `Export` / `Overview`) instead of one flat 20-item
  list — `tabular/sidebar.py`.
- **Hardcoded defaults centralized** into `config.py` (`faiss_store`,
  `data`, the default Groq model, upload guardrails).
- **Large-dataset warning** — datasets over ~2M rows now get a heads-up
  that some operations may be slow, instead of just silently grinding.

### Two files in `src_patches/` — optional, for your review

These are **not** applied automatically — they'd overwrite files you
wrote yourself, so I've put patched copies in `src_patches/` for you to
review and drop in if you want them:

- **`src_patches/embedding.py`** — caches the loaded `SentenceTransformer`
  model instead of reloading it from disk on every single
  `add_documents()` call.
- **`src_patches/vectorstore.py`** — persists the raw embeddings array
  alongside your existing `metadata.pkl`, and adds a `remove_by_source()`
  method. Right now, removing one filed document calls
  `rebuild_from_disk()`, which re-embeds your *entire* library from
  scratch just to drop one file. `remove_by_source()` filters the
  already-computed embeddings in memory instead — no re-embedding.
  `documents/tab.py`'s delete button already calls this when it's
  available (`hasattr` check) and falls back to the old full-rebuild
  behavior if you don't apply the patch, so nothing breaks either way.

I tested both patches in isolation (with lightweight stand-ins for
`faiss`/`sentence-transformers` since I can't install those here) —
`remove_by_source()` correctly removes only the targeted file's chunks
and leaves everything else untouched. I could not run them against your
actual embedding model or a real FAISS index on real data, so please
verify on a copy of `faiss_store/` before relying on this in production.

## One thing I found but deliberately did *not* change

**`step10_last_cleaning` is referenced but never set.** The Export &
Analysis Report step reads `st.session_state["step10_last_cleaning"]` for
its "Step 10" cleaning-history line, but nothing in Step 10 ever writes
that key (Step 10 uses `last_cleaning_summary` / `last_cleaning_operation`
instead). It's harmless — the report just always says "no cleaning
operations recorded" for that half — but worth knowing about. Say the
word if you'd like this wired up too.

## Round 2: bug fixes + performance + a few src/ upgrades

You asked for the improvements I'd suggested. Here's exactly what changed and why, plus what I deliberately left as opt-in.

### Fixed directly in this project (no src/ changes needed)

**`tabular/dataset_state.py` is new — it replaces the old per-step, ad-hoc
session-state handling and fixes two real bugs at once:**

1. *Stale data after uploading a new file.* Previously, `tabular_df` was
   only seeded "if it was still `None`" — so after cleaning file A and
   then uploading file B, steps 10/13/14 could still be holding leftover
   state from A. Now every upload is identified by `(name, size)`; a
   genuinely new file wipes all dataset-scoped session state
   (`tabular_df`, AI reports, cleaning history, chat history, etc.)
   before loading the new one.
2. *Cleaning/transformation didn't reach the other steps.* Every step now
   reads `st.session_state.tabular_df` as *the* dataset, not a fresh
   re-parse of the uploaded file. Clean or transform once in Steps
   10/13/14, and Statistical Analysis, EDA, the AI Analyst, etc. all see
   the updated data.
3. *Free performance win*: since the file is only actually parsed
   (`pd.read_csv`/`read_excel`) once per distinct upload instead of on
   every rerun/button click, larger files feel snappier throughout.

I verified this directly (not just "it boots") — see Testing below.

**`tabular/steps/step06_nl_sql.py`** — the dangerous-keyword check used
plain substring matching, so a column named `date_created` (→
`DATE_CREATED` uppercased) would trip the `"CREATE"` block and get your
query rejected even though nothing dangerous was happening. Switched to
word-boundary regex (`\bCREATE\b`) so it only matches the actual SQL
keyword, not text inside identifiers.

**`config.py`** is new — centralizes what used to be repeated string
literals (`"faiss_store"`, `"data"`, the default Groq model) plus two new
guardrails:
- `MAX_UPLOAD_ROWS` — warns (doesn't block) when an uploaded dataset is
  large enough that some operations may be slow.
- `AI_PRIVACY_NOTICE` — a one-line disclosure shown on every step that
  sends dataset content to Groq's API, so it's not implicit.

### Delivered as opt-in patches, not silently applied — see `src_patches/`

I did **not** overwrite your real `src/vectorstore.py` or
`src/embedding.py` — those are yours, and these are real behavior
changes worth reviewing before you adopt them, not something that should
land silently in a component-split PR. `src_patches/` contains upgraded
versions of both:

- **Model caching**: every call to `add_documents()` previously created a
  fresh `EmbeddingPipeline()`, which reloaded `SentenceTransformer` from
  disk every time — even though it's the same model each time. The patch
  caches loaded models in a module-level dict keyed by model name.
- **Cheap document removal**: deleting one filed document used to trigger
  `rebuild_from_disk()` — re-embedding your *entire* library from scratch
  just to remove one file. The patch adds `remove_by_source()`, which
  filters the already-computed embeddings/metadata in memory and rebuilds
  only the FAISS index structure — no re-embedding. It also persists the
  raw embeddings array (`embeddings.npy`) so this is possible across
  restarts.

`documents/tab.py` already checks `hasattr(rag.vectorstore,
"remove_by_source")` and falls back to the old `rebuild_from_disk()`
behavior if you haven't applied the patch — so **you can drop this zip in
and run it exactly as before without touching `src/` at all**, and apply
`src_patches/` whenever you're ready to review them. To apply: back up
your current `src/vectorstore.py` and `src/embedding.py`, then replace
them with the files in `src_patches/`.

### Still open (bigger asks — say the word if you want these too)

- Swapping the DuckDB keyword blocklist for a real SQL parser (e.g.
  `sqlglot`) instead of keyword scanning — more robust against
  cleverly-nested queries, but adds a new dependency.
- Grouping the 20 sidebar items into collapsible sections (Explore /
  Clean / Transform / AI / Export).
- An actual test suite (pytest) exercising each step's `render()` with a
  synthetic dataframe.

## Testing performed

- All files pass `py_compile`.
- Every module imports cleanly against the real `streamlit`/`pandas`/
  `duckdb` packages, both with a stub `src/` and against your **actual**
  `data_loader.py`/`search.py`/`vectorstore.py`/`embedding.py` (with
  lightweight stand-ins only for the heavy `faiss`/`sentence-transformers`
  packages, since I can't download those here).
- `RAGSearch()` instantiates correctly against your real `FaissVectorStore`
  and every method my code calls on it is present and callable.
- The app boots under `streamlit run` in headless mode and serves HTTP 200
  with no errors, both before and after this round of fixes.
- The DuckDB keyword-filter fix: verified a `date_created`-style query no
  longer false-triggers, and an actual `CREATE TABLE` is still blocked.
- The dataset-reset fix: simulated uploading file A, mutating
  `tabular_df` (as cleaning would), confirming it survives a rerun of the
  *same* file, then uploading file B and confirming both the dataframe
  and all AI-scoped session state reset correctly.
- `remove_by_source()` (in `src_patches/vectorstore.py`): verified against
  a synthetic 5-chunk/2-source index that it removes exactly the targeted
  file's chunks, leaves the other file's chunks and embeddings intact,
  and cleans up gracefully when the store empties out entirely.

I still couldn't exercise the real Streamlit UI in a browser, or run
against your actual GROQ_API_KEY / real documents / real embedding model.
Please click through after dropping this in before relying on it.

I couldn't exercise the actual Streamlit UI end-to-end (no browser here,
and no access to your real `src/data_loader.py` / `src/search.py` /
`GROQ_API_KEY`), so please click through the 20 pages once after dropping
this into your project to confirm everything looks right before you rely
on it.
