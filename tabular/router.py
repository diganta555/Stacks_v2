"""
Maps each sidebar navigation label to the step module whose content it
should actually show.

WHY THIS FILE MATTERS: in the original single-file app, each step's
content was gated behind `if navigation == "...":`, but the string on
each gate didn't match the label the step's own comment described —
labels 6 through 17 were wired to a semantically-unrelated block. Two
consequences: "🤖 AI Data Analyst" matched *two* separate blocks (so both
rendered, stacked, on one page) and "🧹 Data Cleaning" matched *no* block
at all (a dead label).

The mapping below was reconstructed by matching each label's own wording
to the step whose comment title/content it actually describes — every
label now maps to exactly one step, and every step is reachable from
exactly one label.
"""

from typing import Callable, Dict

from tabular.steps import (
    step01_overview,
    step02_quality,
    step03_statistics,
    step04_eda,
    step05_visualization,
    step06_nl_sql,
    step07_ai_analyst,
    step08_ai_insights,
    step09_anomaly_detection,
    step10_cleaning,
    step11_profiling,
    step12_ai_quality_report,
    step13_ai_cleaning_assistant,
    step14_transformation,
    step15_export_report,
    step16_ai_transform_nl,
    step17_ai_chart_recommendation,
    step18_business_insights,
    step19_analyst_chat,
    step20_executive_dashboard,
)

ROUTES: Dict[str, Callable] = {
    "📊 Dataset Overview": step01_overview.render,
    "🔎 Data Quality": step02_quality.render,
    "📈 Statistical Analysis": step03_statistics.render,
    "🔬 Exploratory Analytics": step04_eda.render,
    "📊 Automatic Visualization": step05_visualization.render,
    "🧠 Natural Language SQL": step06_nl_sql.render,
    "🤖 AI Data Analyst": step07_ai_analyst.render,
    "💡 GPT Insights": step08_ai_insights.render,
    "🚨 Anomaly Detection": step09_anomaly_detection.render,
    "🧹 Data Cleaning": step10_cleaning.render,
    "📋 Dataset Profiling": step11_profiling.render,
    "🤖 AI Data Quality Report": step12_ai_quality_report.render,
    "✨ AI Cleaning Assistant": step13_ai_cleaning_assistant.render,
    "🔧 Data Transformation": step14_transformation.render,
    "📤 Export & Reports": step15_export_report.render,
    "🔄 AI Transformation": step16_ai_transform_nl.render,
    "📊 AI Chart Recommendation": step17_ai_chart_recommendation.render,
    "💼 Business Insights": step18_business_insights.render,
    "💬 AI Analyst Chat": step19_analyst_chat.render,
    "🏠 Executive Dashboard": step20_executive_dashboard.render,
}


def dispatch(navigation: str, df, ctx, tabular_file) -> None:
    handler = ROUTES.get(navigation)
    if handler is None:
        import streamlit as st
        st.error(f"No content is registered for '{navigation}'.")
        return
    handler(df, ctx, tabular_file)
