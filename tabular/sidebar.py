"""
Sidebar for the Tabular Data tab: the section-navigation controls plus the
"currently loaded dataset" summary widgets.

NOTE ON THE NAV LABELS: the original app's sidebar labels didn't match
the content each one opened (a systematic wiring bug — see the routing
table in tabular/router.py). The labels below are unchanged, but they now
open the correspondingly-named content instead of a mismatched block.

NAVIGATION UX: the original was one flat 20-item radio list, which is a
lot to scan. It's now grouped into five categories (a category picker,
then a page picker within that category) — same 20 destinations and
labels, just easier to find things in. tabular/router.py only cares about
the returned label string, not which session-state key produced it, so
this is free to restructure without touching routing at all.
"""

from typing import Dict, List

import streamlit as st


NAV_GROUPS: Dict[str, List[str]] = {
    "🔍 Explore": [
        "📊 Dataset Overview",
        "🔎 Data Quality",
        "📈 Statistical Analysis",
        "🔬 Exploratory Analytics",
        "📊 Automatic Visualization",
        "🚨 Anomaly Detection",
    ],
    "🧹 Clean & Transform": [
        "🧹 Data Cleaning",
        "📋 Dataset Profiling",
        "🔧 Data Transformation",
    ],
    "🤖 AI Assistants": [
        "🤖 AI Data Quality Report",
        "✨ AI Cleaning Assistant",
        "🧠 Natural Language SQL",
        "🤖 AI Data Analyst",
        "💡 GPT Insights",
        "📊 AI Chart Recommendation",
        "🔄 AI Transformation",
        "💼 Business Insights",
        "💬 AI Analyst Chat",
    ],
    "📤 Export": [
        "📤 Export & Reports",
    ],
    "🏠 Overview": [
        "🏠 Executive Dashboard",
    ],
}

# Flat list, still exported for anything (e.g. the router) that wants
# every valid label regardless of grouping.
NAV_OPTIONS: List[str] = [label for group in NAV_GROUPS.values() for label in group]


def render_sidebar() -> str:
    """Renders the sidebar and returns the currently selected nav label."""

    st.sidebar.title("🤖 Stacks V2")
    st.sidebar.caption("Analyze • Clean • Transform • Understand")

    selected_group = st.sidebar.selectbox(
        "Section",
        list(NAV_GROUPS.keys()),
        key="main_navigation_group",
    )

    options_in_group = NAV_GROUPS[selected_group]

    # Each group gets its OWN widget key (rather than one shared
    # "main_navigation" key reused across groups). If a single key were
    # reused, switching groups could leave a stale selected value in
    # session_state that isn't a member of the new group's options list,
    # which Streamlit raises an error on. Per-group keys sidestep that
    # entirely, and as a bonus remember your last page within each
    # section independently.
    navigation = st.sidebar.radio(
        "Page",
        options_in_group,
        key=f"main_navigation__{selected_group}",
    )

    st.sidebar.divider()
    st.sidebar.markdown("### 📁 Dataset")

    df = st.session_state.get("tabular_df")

    if df is not None:
        st.sidebar.success(
            st.session_state.get("tabular_file_name", "Dataset loaded")
        )
        st.sidebar.metric("Rows", f"{len(df):,}")
        st.sidebar.metric("Columns", f"{len(df.columns):,}")
    else:
        st.sidebar.info("No dataset uploaded")

    return navigation
