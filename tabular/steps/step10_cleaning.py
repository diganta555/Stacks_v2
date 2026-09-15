"""Data Cleaning & Recommendations — detect issues, preview + apply cleaning ops,
undo/reset controls, download current dataset.

This step owns st.session_state.tabular_df (the "current" working dataset),
tabular_original_df (as first uploaded) and tabular_previous_df (one-step undo).
"""

import pandas as pd
import streamlit as st

from tabular.context import DatasetContext
from tabular.dataset_state import reset_all_dataset_state

DESTRUCTIVE_OPERATIONS = [
    "Remove Duplicate Rows",
    "Drop Rows With Missing Values",
    "Drop Constant Columns",
]


def render(df: pd.DataFrame, ctx: DatasetContext, tabular_file=None) -> None:
    st.markdown("## Data Cleaning & Recommendations")
    st.caption(
        "Identify common data-quality problems, preview cleaning operations, "
        "safely apply changes, and download the current dataset."
    )

    if df is None or df.empty:
        st.warning("No dataset is available for cleaning.")
        return

    # df is already st.session_state.tabular_df by the time it reaches
    # here (tabular/dataset_state.py guarantees that for every step), so
    # no seeding is needed — this step just reads and mutates it directly.

    _render_current_summary(df)
    cleaning_recommendations = _build_recommendations(df)
    _render_recommendations(cleaning_recommendations)

    selected_cleaning_operation, preview_state = _render_operation_picker(df, ctx)
    confirm_cleaning = _render_confirmation(selected_cleaning_operation)
    _render_apply_button(df, selected_cleaning_operation, preview_state, confirm_cleaning)
    _render_last_result()
    _render_dataset_controls()
    _render_download(df)


def _render_current_summary(df):
    st.markdown("### Current Dataset")

    current_missing = int(df.isna().sum().sum())
    current_duplicates = int(df.duplicated().sum())

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Rows", f"{len(df):,}")
    with c2:
        st.metric("Columns", f"{len(df.columns):,}")
    with c3:
        st.metric("Missing Values", f"{current_missing:,}")
    with c4:
        st.metric("Duplicate Rows", f"{current_duplicates:,}")


def _build_recommendations(df):
    recommendations = []

    for column in df.columns:
        missing_count = int(df[column].isna().sum())
        if missing_count > 0:
            missing_pct = missing_count / len(df) * 100 if len(df) > 0 else 0
            recommendations.append(
                {
                    "Column": column,
                    "Issue": "Missing Values",
                    "Count": missing_count,
                    "Percentage": round(missing_pct, 2),
                    "Recommendation": "Fill missing values or remove affected records.",
                }
            )

    current_duplicates = int(df.duplicated().sum())
    if current_duplicates > 0:
        duplicate_pct = current_duplicates / len(df) * 100 if len(df) > 0 else 0
        recommendations.append(
            {
                "Column": "All Columns",
                "Issue": "Duplicate Rows",
                "Count": current_duplicates,
                "Percentage": round(duplicate_pct, 2),
                "Recommendation": "Remove duplicate records if they are unintended.",
            }
        )

    constant_columns = [c for c in df.columns if df[c].nunique(dropna=False) <= 1]
    for column in constant_columns:
        recommendations.append(
            {
                "Column": column,
                "Issue": "Constant Column",
                "Count": int(df[column].nunique(dropna=False)),
                "Percentage": 100.0,
                "Recommendation": "Consider removing the column because it contains no variation.",
            }
        )

    return recommendations


def _render_recommendations(cleaning_recommendations):
    if cleaning_recommendations:
        st.markdown("### Detected Data Quality Issues")
        st.dataframe(pd.DataFrame(cleaning_recommendations), use_container_width=True, hide_index=True)
    else:
        st.success("No common data-cleaning issues were detected.")


def _render_operation_picker(df, ctx):
    st.markdown("### Apply Cleaning Operation")

    cleaning_operations = [
        "Remove Duplicate Rows",
        "Fill Missing Numeric Values",
        "Fill Missing Categorical Values",
        "Drop Rows With Missing Values",
        "Drop Constant Columns",
        "Convert Column to Numeric",
    ]

    selected_cleaning_operation = st.selectbox(
        "Select cleaning operation", cleaning_operations, key="cleaning_operation"
    )

    state = {
        "numeric_column": None,
        "fill_strategy": None,
        "category_column": None,
        "category_fill_strategy": None,
        "conversion_column": None,
        "constant_columns": [c for c in df.columns if df[c].nunique(dropna=False) <= 1],
    }

    preview_df = df.copy()

    if selected_cleaning_operation == "Remove Duplicate Rows":
        current_duplicates = int(df.duplicated().sum())
        st.info(f"{current_duplicates:,} duplicate row(s) currently detected.")
        if current_duplicates > 0:
            preview_df = df.drop_duplicates().reset_index(drop=True)
            st.markdown("#### Preview")
            st.dataframe(preview_df.head(20), use_container_width=True, hide_index=True)
            st.caption(
                f"Rows before: {len(df):,} | Rows after: {len(preview_df):,} | "
                f"Rows removed: {len(df) - len(preview_df):,}"
            )
        else:
            st.success("No duplicate rows need to be removed.")

    elif selected_cleaning_operation == "Fill Missing Numeric Values":
        available = [c for c in ctx.numeric_columns if c in df.columns]
        if available:
            state["numeric_column"] = st.selectbox(
                "Select numeric column", available, key="clean_numeric_column"
            )
            state["fill_strategy"] = st.selectbox(
                "Fill strategy", ["Mean", "Median", "Zero"], key="numeric_fill_strategy"
            )
            missing_count = int(df[state["numeric_column"]].isna().sum())
            st.info(f"{missing_count:,} missing value(s) found in `{state['numeric_column']}`.")

            numeric_series = pd.to_numeric(df[state["numeric_column"]], errors="coerce")
            fill_value = {
                "Mean": numeric_series.mean,
                "Median": numeric_series.median,
                "Zero": lambda: 0,
            }[state["fill_strategy"]]()

            preview_df = df.copy()
            if pd.notna(fill_value):
                preview_df[state["numeric_column"]] = numeric_series.fillna(fill_value)
                st.markdown("#### Preview")
                st.dataframe(preview_df.head(20), use_container_width=True, hide_index=True)
                st.caption(f"Missing values will be replaced with {fill_value:,.2f}.")
            else:
                st.warning("Unable to calculate a valid fill value.")
        else:
            st.info("No numeric columns are available.")

    elif selected_cleaning_operation == "Fill Missing Categorical Values":
        available = [c for c in ctx.categorical_columns if c in df.columns]
        if available:
            state["category_column"] = st.selectbox(
                "Select categorical column", available, key="clean_category_column"
            )
            state["category_fill_strategy"] = st.selectbox(
                "Fill strategy", ["Most Frequent Value", "Unknown"], key="category_fill_strategy"
            )
            missing_count = int(df[state["category_column"]].isna().sum())
            st.info(f"{missing_count:,} missing value(s) found in `{state['category_column']}`.")

            preview_df = df.copy()
            if state["category_fill_strategy"] == "Most Frequent Value":
                mode_values = df[state["category_column"]].mode()
                fill_value = mode_values.iloc[0] if not mode_values.empty else "Unknown"
            else:
                fill_value = "Unknown"

            preview_df[state["category_column"]] = preview_df[state["category_column"]].fillna(fill_value)
            st.markdown("#### Preview")
            st.dataframe(preview_df.head(20), use_container_width=True, hide_index=True)
            st.caption(f"Missing values will be replaced with `{fill_value}`.")
        else:
            st.info("No categorical columns are available.")

    elif selected_cleaning_operation == "Drop Rows With Missing Values":
        rows_with_missing = int(df.isna().any(axis=1).sum())
        preview_df = df.dropna().reset_index(drop=True)
        st.warning(f"{rows_with_missing:,} row(s) contain at least one missing value.")
        st.caption(
            f"Rows before: {len(df):,} | Rows after: {len(preview_df):,} | "
            f"Rows removed: {len(df) - len(preview_df):,}"
        )
        st.markdown("#### Preview")
        st.dataframe(preview_df.head(20), use_container_width=True, hide_index=True)

    elif selected_cleaning_operation == "Drop Constant Columns":
        if state["constant_columns"]:
            preview_df = df.drop(columns=state["constant_columns"])
            st.warning("The following constant columns will be removed:")
            st.write(", ".join(state["constant_columns"]))
            st.markdown("#### Preview")
            st.dataframe(preview_df.head(20), use_container_width=True, hide_index=True)
            st.caption(
                f"Columns before: {len(df.columns):,} | Columns after: {len(preview_df.columns):,} | "
                f"Columns removed: {len(df.columns) - len(preview_df.columns):,}"
            )
        else:
            st.success("No constant columns need to be removed.")

    elif selected_cleaning_operation == "Convert Column to Numeric":
        state["conversion_column"] = st.selectbox(
            "Select column", df.columns.tolist(), key="conversion_column"
        )
        original_series = df[state["conversion_column"]].copy()
        converted_series = pd.to_numeric(original_series, errors="coerce")
        new_invalid_values = int((original_series.notna() & converted_series.isna()).sum())

        preview_df = df.copy()
        preview_df[state["conversion_column"]] = converted_series

        if new_invalid_values > 0:
            st.warning(f"{new_invalid_values:,} non-numeric value(s) will become missing values.")
        else:
            st.success("All non-null values can be converted to numeric successfully.")

        st.markdown("#### Preview")
        st.dataframe(preview_df.head(20), use_container_width=True, hide_index=True)

    return selected_cleaning_operation, state


def _render_confirmation(selected_cleaning_operation):
    if selected_cleaning_operation in DESTRUCTIVE_OPERATIONS:
        st.markdown("### Confirmation")
        return st.checkbox(
            "I understand that this operation may remove data.",
            key="confirm_cleaning_operation",
        )
    return True


def _render_apply_button(df, selected_cleaning_operation, state, confirm_cleaning):
    st.markdown("### Apply Changes")

    if not st.button("Apply Cleaning Operation", key="apply_cleaning_operation", type="primary"):
        return

    if not confirm_cleaning:
        st.warning("Please confirm that you understand the operation may remove data.")
        return

    try:
        st.session_state.tabular_previous_df = df.copy()

        before_rows = len(df)
        before_columns = len(df.columns)
        before_missing = int(df.isna().sum().sum())
        operation_applied = True

        if selected_cleaning_operation == "Remove Duplicate Rows":
            df = df.drop_duplicates().reset_index(drop=True)
            st.success(f"Removed {before_rows - len(df):,} duplicate row(s).")

        elif selected_cleaning_operation == "Fill Missing Numeric Values":
            column = state["numeric_column"]
            numeric_series_clean = pd.to_numeric(df[column], errors="coerce")
            fill_value = {
                "Mean": numeric_series_clean.mean,
                "Median": numeric_series_clean.median,
                "Zero": lambda: 0,
            }[state["fill_strategy"]]()

            if pd.isna(fill_value):
                st.error("Unable to calculate a valid fill value.")
                operation_applied = False
            else:
                df[column] = numeric_series_clean.fillna(fill_value)
                st.success(f"Filled missing values in `{column}` using {state['fill_strategy'].lower()}.")

        elif selected_cleaning_operation == "Fill Missing Categorical Values":
            column = state["category_column"]
            if state["category_fill_strategy"] == "Most Frequent Value":
                mode_values = df[column].mode()
                fill_value = mode_values.iloc[0] if not mode_values.empty else "Unknown"
            else:
                fill_value = "Unknown"
            df[column] = df[column].fillna(fill_value)
            st.success(f"Filled missing values in `{column}` with `{fill_value}`.")

        elif selected_cleaning_operation == "Drop Rows With Missing Values":
            df = df.dropna().reset_index(drop=True)
            st.success(f"Removed {before_rows - len(df):,} row(s) containing missing values.")

        elif selected_cleaning_operation == "Drop Constant Columns":
            if state["constant_columns"]:
                df = df.drop(columns=state["constant_columns"])
                st.success(f"Removed {len(state['constant_columns'])} constant column(s).")
            else:
                st.info("No constant columns to remove.")

        elif selected_cleaning_operation == "Convert Column to Numeric":
            column = state["conversion_column"]
            original_series = df[column].copy()
            converted_series = pd.to_numeric(original_series, errors="coerce")
            new_invalid_values = int((original_series.notna() & converted_series.isna()).sum())
            df[column] = converted_series
            if new_invalid_values > 0:
                st.warning(
                    f"{new_invalid_values:,} value(s) could not be converted to numeric "
                    f"and became missing."
                )
            st.success(f"Converted `{column}` to numeric.")

        if operation_applied:
            st.session_state.tabular_df = df.copy()

            st.session_state.last_cleaning_operation = selected_cleaning_operation
            st.session_state.last_cleaning_summary = {
                "before_rows": before_rows,
                "after_rows": len(df),
                "before_columns": before_columns,
                "after_columns": len(df.columns),
                "before_missing": before_missing,
                "after_missing": int(df.isna().sum().sum()),
            }

            st.rerun()
        else:
            st.session_state.tabular_previous_df = None

    except Exception as cleaning_error:
        st.error(f"Cleaning operation failed: {cleaning_error}")
        st.session_state.tabular_previous_df = None


def _render_last_result():
    if "last_cleaning_summary" not in st.session_state:
        return

    summary = st.session_state.last_cleaning_summary

    st.markdown("### Last Cleaning Result")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            "Rows", f"{summary['after_rows']:,}",
            delta=summary["after_rows"] - summary["before_rows"],
        )
    with c2:
        st.metric(
            "Columns", f"{summary['after_columns']:,}",
            delta=summary["after_columns"] - summary["before_columns"],
        )
    with c3:
        st.metric(
            "Missing Values", f"{summary['after_missing']:,}",
            delta=summary["after_missing"] - summary["before_missing"],
        )
    with c4:
        st.metric(
            "Rows Removed",
            f"{max(summary['before_rows'] - summary['after_rows'], 0):,}",
        )


def _render_dataset_controls():
    st.markdown("### Dataset Controls")

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("↩️ Undo Last Cleaning", key="undo_last_cleaning"):
            if st.session_state.tabular_previous_df is not None:
                st.session_state.tabular_df = st.session_state.tabular_previous_df.copy()
                st.session_state.tabular_previous_df = None
                st.session_state.pop("last_cleaning_summary", None)
                st.session_state.pop("last_cleaning_operation", None)
                st.rerun()
            else:
                st.info("There is no cleaning operation to undo.")

    with c2:
        if st.button("🔄 Reset to Original Dataset", key="reset_tabular_dataset"):
            if st.session_state.tabular_original_df is not None:
                st.session_state.tabular_df = st.session_state.tabular_original_df.copy()
                st.session_state.tabular_previous_df = None
                st.session_state.pop("last_cleaning_summary", None)
                st.session_state.pop("last_cleaning_operation", None)
                st.rerun()
            else:
                st.info("Original dataset is not available.")

    with c3:
        if st.button("🗑️ Clear Dataset", key="clear_tabular_dataset"):
            reset_all_dataset_state()
            st.rerun()


def _render_download(df):
    st.markdown("### Download Current Dataset")

    current_df = st.session_state.tabular_df
    cleaned_csv = current_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "⬇️ Download Cleaned CSV",
        data=cleaned_csv,
        file_name="cleaned_dataset.csv",
        mime="text/csv",
        key="download_cleaned_dataset",
    )
