"""
Page-level CSS and the hero banner markup.

Kept as a single string (rather than an external .css file) because
Streamlit only supports injecting CSS via st.markdown(unsafe_allow_html=True).
"""

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --ink: #0f1a2b;
    --paper: #eee7d8;
    --paper-panel: #f6f1e4;
    --navy: #152238;
    --navy-2: #1d3050;
    --amber: #c7862b;
    --line: rgba(15,26,43,0.14);
    --line-strong: rgba(15,26,43,0.28);
}

.stApp { background-color: var(--paper); }
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 1.5rem !important; padding-bottom: 3rem !important; padding-left: 2.5rem !important; padding-right: 2.5rem !important; max-width: 1600px; }

/* Full-bleed navy hero banner. Breaks out of the block-container's own
   padding only (not the full viewport) — the old 100vw + -50vw trick
   didn't account for the sidebar's width, so it overflowed past the
   sidebar and caused horizontal scrolling + visual overlap. Since this
   now only cancels out .block-container's own padding-left/right
   (2.5rem, set immediately above), it stays confined to the main
   content column no matter the sidebar's width or state. */
.stacks-hero {
    position: relative;
    margin-left: -2.5rem; margin-right: -2.5rem;
    width: calc(100% + 5rem);
    background: var(--navy);
    color: var(--paper);
    padding: 2.2rem 2.5rem 1.6rem;
    border-bottom: 4px solid var(--amber);
    margin-bottom: 2.8rem;
    overflow: hidden;
}
.stacks-hero .eyebrow {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #e0a53f;
    margin-bottom: 0.5rem;
}
.stacks-hero h1 {
    font-family: 'Source Serif 4', serif !important;
    font-weight: 700 !important;
    font-size: 2.1rem !important;
    color: var(--paper) !important;
    margin: 0 0 0.3rem !important;
}
.stacks-hero p {
    font-family: 'Inter', sans-serif;
    color: #d8cfba;
    font-size: 0.95rem;
    max-width: 60ch;
    margin: 0;
}

/* Section labels styled like archive drawer tabs */
.stacks-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--navy-2);
    border-bottom: 1px solid var(--line-strong);
    padding-bottom: 0.4rem;
    margin-bottom: 0.8rem;
}

h3 {
    font-family: 'Source Serif 4', serif !important;
    color: var(--navy) !important;
}

/* Bordered card panels (st.container(border=True)) */
[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: var(--paper-panel) !important;
    border: 1px solid var(--line-strong) !important;
    border-radius: 2px !important;
    padding: 0.5rem 0.4rem !important;
}

/* Buttons */
.stButton > button {
    background-color: var(--navy) !important;
    color: var(--paper) !important;
    border: none !important;
    border-radius: 2px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    white-space: nowrap !important;
}
.stButton > button:hover { background-color: var(--navy-2) !important; }
.stButton > button[kind="secondary"] {
    background: none !important;
    color: var(--amber) !important;
    border: 1px solid var(--line-strong) !important;
}

/* Inputs */
.stTextInput input, .stNumberInput input {
    background-color: var(--paper) !important;
    color: var(--ink) !important;
    border: 1px solid var(--line-strong) !important;
    border-radius: 2px !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextInput input::placeholder, .stNumberInput input::placeholder {
    color: #8a8270 !important;
    opacity: 1 !important;
}

/* Alerts (success/info) recolored to fit the palette */
.stAlert {
    border-radius: 2px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.82rem !important;
}

/* File uploader dropzone */
[data-testid="stFileUploaderDropzone"] {
    background-color: var(--paper) !important;
    border: 2px dashed var(--line-strong) !important;
    border-radius: 2px !important;
}

/* Monospace index numbers + filenames */
.stMarkdown code {
    background: none !important;
    color: var(--amber) !important;
    font-family: 'JetBrains Mono', monospace !important;
    padding: 0 !important;
}

/* Source chips at the end of an answer */
.stacks-chip {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    padding: 0.25rem 0.55rem;
    border: 1px solid var(--amber);
    color: var(--navy-2);
    border-radius: 2px;
    background: rgba(199,134,43,0.1);
    margin-right: 0.35rem;
}
.stacks-chip-ext {
    border-color: var(--line-strong) !important;
    color: var(--navy-2) !important;
    background: none !important;
    margin-bottom: 0.35rem;
}

/* Divider under each indexed-source row instead of a boxed look
   (scoped to rows inside bordered panels only, not the outer page columns) */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] {
    border-bottom: 1px solid var(--line);
    padding-bottom: 0.3rem;
    margin-bottom: 0.3rem;
}
/* Widget labels, captions, and uploader text — force dark, readable color */
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label,
.stCaption, [data-testid="stCaptionContainer"],
[data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploaderDropzone"] div,
[data-testid="stFileUploaderFile"] span,
[data-testid="stFileUploaderFile"] small,
.stMarkdown p,
.stMarkdown li,
.stMarkdown ol,
.stMarkdown ul {
    color: var(--ink) !important;
    opacity: 1 !important;
}
.stMarkdown li::marker {
    color: var(--ink) !important;
}

/* Hero text must stay light against the dark navy background — higher
   specificity so it wins over the broader .stMarkdown rule above. */
.stacks-hero p, .stacks-hero .eyebrow, .stacks-hero h1 {
    color: #d8cfba !important;
}
.stacks-hero h1 { color: var(--paper) !important; }
.stacks-hero .eyebrow { color: #e0a53f !important; }

/* Streamlit dims the whole app to ~70% opacity while a script run is in
   progress; that's what made everything look washed out mid-action.
   Force full opacity on the main view wrapper so text stays readable. */
[data-testid="stAppViewContainer"], [data-testid="stMain"] {
    opacity: 1 !important;
}

/* ============================================================
   SIDEBAR — match the navy hero band instead of Streamlit's
   default light theme. Previously the sidebar had NO custom
   styling at all (true even in the original single-file app),
   so it looked like a completely different, unstyled app next
   to the navy header / warm paper content area.
   ============================================================ */

[data-testid="stSidebar"] {
    background-color: var(--navy) !important;
    border-right: 3px solid var(--amber);
    position: sticky;
    top: 0;
    height: 100vh;
    overflow-y: auto;
}

/* Streamlit's own top toolbar (Deploy button, etc.) is already fixed in
   place natively — this just gives it a matching background instead of
   a plain transparent strip, and makes sure it layers above the hero. */
[data-testid="stHeader"] {
    background-color: var(--paper) !important;
    z-index: 1000;
}

[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding-top: 1.2rem;
}

/* Default all sidebar text to the same light "paper" tone the hero
   uses, then carve out specific exceptions below (metric deltas,
   alerts, and the select/radio controls) that need their own colors
   to stay legible or keep their semantic meaning (red/green deltas). */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stCaption,
[data-testid="stCaptionContainer"],
[data-testid="stSidebar"] [data-testid="stMetricLabel"],
[data-testid="stSidebar"] [data-testid="stMetricValue"] {
    color: #d8cfba !important;
}

[data-testid="stSidebar"] h1 {
    font-family: 'Source Serif 4', serif !important;
    font-weight: 700 !important;
    color: var(--paper) !important;
}

[data-testid="stSidebar"] hr {
    border-color: rgba(216, 207, 186, 0.25) !important;
}

/* "Section" selectbox: keep it on a light control (matches the
   text-input styling used elsewhere) so its text stays dark-on-light
   rather than light-on-light against the navy sidebar. */
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background-color: var(--paper) !important;
    border: 1px solid var(--line-strong) !important;
    border-radius: 2px !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] * {
    color: var(--ink) !important;
}

/* "Page" radio group: labels sit directly on the navy background,
   so they use the light paper tone; the selected option's circle
   keeps Streamlit's accent color so the active page is still obvious. */
[data-testid="stSidebar"] [role="radiogroup"] label p {
    color: #d8cfba !important;
}
[data-testid="stSidebar"] [role="radiogroup"] label:hover p {
    color: var(--amber) !important;
}

/* Metric deltas (rows-removed / +N indicators) keep their default
   green/red semantic color rather than being flattened to paper. */
[data-testid="stSidebar"] [data-testid="stMetricDelta"] {
    color: unset !important;
}

/* Success / info boxes ("Dataset loaded", "No dataset uploaded") keep
   Streamlit's own light-tinted backgrounds with dark text — they read
   as intentional highlighted panels against the dark sidebar rather
   than needing a custom color. */
[data-testid="stSidebar"] .stAlert,
[data-testid="stSidebar"] .stAlert * {
    color: var(--ink) !important;
}
</style>
"""

HERO_HTML = """
<div class="stacks-hero">
    <div class="eyebrow">Drawer 01 — Reference &amp; Retrieval</div>
    <h1>\U0001F4DA Stacks</h1>
    <p>Upload documents into the stacks, then ask the reading room a question.
    Answers are drawn only from what you've filed.</p>
</div>
"""


def inject_global_styles() -> None:
    """Injects page CSS + the hero banner. Call once, near the top of the app."""
    st.markdown(CSS + HERO_HTML, unsafe_allow_html=True)