"""Final Dashboard — health overview, AI-feature completion status, export center."""

import pandas as pd
import streamlit as st

from tabular.context import DatasetContext


def render(df: pd.DataFrame, ctx: DatasetContext, tabular_file=None) -> None:
    st.markdown("## Final Dashboard & Production Polish")
    st.caption(
        "Final overview of the current dataset, analysis status, AI capabilities, "
        "and export options."
    )

    if df is None or df.empty:
        st.info("Upload a dataset to view the final dashboard.")
        return

    total_rows = len(df)
    total_columns = len(df.columns)
    total_missing = int(df.isna().sum().sum())
    total_duplicates = int(df.duplicated().sum())
    total_cells = total_rows * total_columns
    missing_percentage = (total_missing / total_cells) * 100 if total_cells > 0 else 0
    duplicate_percentage = (total_duplicates / total_rows) * 100 if total_rows > 0 else 0
    constant_columns = [c for c in df.columns if df[c].nunique(dropna=False) <= 1]

    health_score = 100.0
    health_score -= min(missing_percentage, 40)
    health_score -= min(duplicate_percentage, 20)
    if total_columns > 0:
        constant_percentage = (len(constant_columns) / total_columns) * 100
        health_score -= min(constant_percentage, 20)
    health_score = max(0, min(100, health_score))

    st.markdown("### Dataset Status")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Rows", f"{total_rows:,}")
    with c2:
        st.metric("Columns", f"{total_columns:,}")
    with c3:
        st.metric("Missing Values", f"{total_missing:,}")
    with c4:
        st.metric("Health Score", f"{health_score:.1f}/100")

    if health_score >= 80:
        st.success("Dataset Status: Healthy")
    elif health_score >= 60:
        st.warning("Dataset Status: Needs Improvement")
    else:
        st.error("Dataset Status: Poor Data Quality")

    st.markdown("### Data Quality Summary")
    q1, q2, q3 = st.columns(3)
    with q1:
        st.metric("Missing %", f"{missing_percentage:.2f}%")
    with q2:
        st.metric("Duplicate %", f"{duplicate_percentage:.2f}%")
    with q3:
        st.metric("Constant Columns", len(constant_columns))

    st.markdown("### Current Dataset")
    st.dataframe(df.head(10), use_container_width=True, hide_index=True)

    _render_ai_status()
    _render_export_center(df)
    _render_session_management()

    st.markdown("---")
    st.success("AI Data Analyst workflow completed successfully.")
    st.caption(
        "Dataset → Quality → Analysis → AI → Cleaning → Transformation → "
        "Insights → Export"
    )


def _feature_status(key):
    return "Generated" if st.session_state.get(key) else "Not Generated"


def _render_ai_status():
    st.markdown("### AI Analysis Status")

    ai_status = [
        {"Feature": "AI Data Quality Report", "Status": _feature_status("ai_quality_report")},
        {"Feature": "AI Cleaning Plan", "Status": _feature_status("ai_cleaning_plan")},
        {"Feature": "AI Business Insights", "Status": _feature_status("step18_business_insights")},
        {"Feature": "AI Chart Recommendation", "Status": _feature_status("step17_chart_plan")},
        {"Feature": "AI Transformation Plan", "Status": _feature_status("step16_transformation_plan")},
    ]

    st.dataframe(pd.DataFrame(ai_status), use_container_width=True, hide_index=True)


def _render_export_center(df):
    st.markdown("### Export Center")

    final_csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Current Dataset",
        data=final_csv,
        file_name="final_dataset.csv",
        mime="text/csv",
        key="step20_download_dataset",
    )

    if st.session_state.get("complete_analysis_report"):
        final_report = st.session_state["complete_analysis_report"].encode("utf-8")
        st.download_button(
            label="Download Complete Analysis Report",
            data=final_report,
            file_name="complete_analysis_report.txt",
            mime="text/plain",
            key="step20_download_report",
        )
    else:
        st.info(
            "Generate the Complete Analysis Report in the Export & Reports step "
            "to enable the final report download."
        )


def _render_session_management():
    st.markdown("### Session Management")

    if st.button("Clear AI Analysis Session", key="step20_clear_ai_session"):
        keys_to_clear = [
            "ai_quality_report",
            "ai_cleaning_plan",
            "step16_transformation_plan",
            "step17_chart_plan",
            "step18_business_insights",
            "complete_analysis_report",
            "step19_chat_history",
        ]
        for key in keys_to_clear:
            st.session_state.pop(key, None)

        st.success("AI analysis session cleared successfully.")
        st.rerun()
