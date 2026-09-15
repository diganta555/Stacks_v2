"""Data Transformation & Feature Engineering — rename, retype, calculate, extract
date parts, normalize/standardize, text case ops. Mutates st.session_state.tabular_df."""

import pandas as pd
import streamlit as st

from tabular.context import DatasetContext


def render(df: pd.DataFrame, ctx: DatasetContext, tabular_file=None) -> None:
    st.markdown("## Data Transformation & Feature Engineering")
    st.caption("Transform columns and create derived features without changing the original uploaded dataset.")

    if df is None or df.empty:
        st.info("Upload a dataset to use data transformation and feature engineering.")
        return

    transformation_type = st.selectbox(
        "Select Transformation",
        [
            "Select an operation",
            "Rename Column",
            "Convert Data Type",
            "Create Calculated Column",
            "Extract Date Components",
            "Normalize Numeric Column",
            "Standardize Numeric Column",
            "Lowercase Text Column",
            "Uppercase Text Column",
            "Strip Text Whitespace",
        ],
        key="step14_transformation_type",
    )

    handlers = {
        "Rename Column": _rename_column,
        "Convert Data Type": _convert_data_type,
        "Create Calculated Column": _create_calculated_column,
        "Extract Date Components": _extract_date_components,
        "Normalize Numeric Column": _normalize_column,
        "Standardize Numeric Column": _standardize_column,
        "Lowercase Text Column": lambda df: _text_case(df, "lower"),
        "Uppercase Text Column": lambda df: _text_case(df, "upper"),
        "Strip Text Whitespace": _strip_whitespace,
    }

    if transformation_type in handlers:
        handlers[transformation_type](df)

    st.markdown("### Current Dataset Preview")
    df = st.session_state.tabular_df if st.session_state.get("tabular_df") is not None else df
    st.dataframe(df.head(20), use_container_width=True, hide_index=True)
    st.caption(f"Current dataset: {len(df):,} rows × {len(df.columns):,} columns")


def _rename_column(df):
    st.markdown("### Rename Column")

    rename_column = st.selectbox("Column", df.columns.tolist(), key="step14_rename_column")
    new_column_name = st.text_input("New Column Name", key="step14_new_column_name")

    if not st.button("Rename Column", key="step14_apply_rename"):
        return

    new_column_name = new_column_name.strip()

    if not new_column_name:
        st.error("Please enter a new column name.")
        return

    if new_column_name != rename_column and new_column_name in df.columns:
        st.error("A column with this name already exists.")
        return

    st.session_state.tabular_previous_df = df.copy()
    df = df.rename(columns={rename_column: new_column_name})
    st.session_state.tabular_df = df.copy()
    st.success(f"Column '{rename_column}' renamed to '{new_column_name}'.")
    st.rerun()


def _convert_data_type(df):
    st.markdown("### Convert Data Type")

    dtype_column = st.selectbox("Column", df.columns.tolist(), key="step14_dtype_column")
    target_dtype = st.selectbox(
        "Target Data Type", ["Integer", "Float", "String", "Boolean", "Date / Time"],
        key="step14_target_dtype",
    )

    if not st.button("Convert Data Type", key="step14_apply_dtype"):
        return

    try:
        st.session_state.tabular_previous_df = df.copy()
        invalid_values = 0

        if target_dtype == "Integer":
            converted = pd.to_numeric(df[dtype_column], errors="coerce")
            invalid_values = int((converted.isna() & df[dtype_column].notna()).sum())
            df[dtype_column] = converted.round().astype("Int64")

        elif target_dtype == "Float":
            converted = pd.to_numeric(df[dtype_column], errors="coerce")
            invalid_values = int((converted.isna() & df[dtype_column].notna()).sum())
            df[dtype_column] = converted

        elif target_dtype == "String":
            df[dtype_column] = df[dtype_column].astype("string")

        elif target_dtype == "Boolean":
            true_values = ["true", "1", "yes", "y", "t"]
            false_values = ["false", "0", "no", "n", "f"]

            def convert_boolean(value):
                if pd.isna(value):
                    return pd.NA
                value_string = str(value).strip().lower()
                if value_string in true_values:
                    return True
                if value_string in false_values:
                    return False
                return pd.NA

            original_non_null = df[dtype_column].notna()
            df[dtype_column] = df[dtype_column].apply(convert_boolean).astype("boolean")
            invalid_values = int((df[dtype_column].isna() & original_non_null).sum())

        else:
            df[dtype_column] = pd.to_datetime(df[dtype_column], errors="coerce")

        st.session_state.tabular_df = df.copy()

        if invalid_values > 0:
            st.warning(f"{invalid_values} value(s) could not be converted and became missing.")

        st.success(f"'{dtype_column}' converted to {target_dtype} successfully.")
        st.rerun()

    except Exception as e:
        st.error(f"Unable to convert data type: {e}")


def _create_calculated_column(df):
    st.markdown("### Create Calculated Column")

    numeric_columns = df.select_dtypes(include="number").columns.tolist()

    if len(numeric_columns) < 2:
        st.info("At least two numeric columns are required to create a calculated column.")
        return

    calculated_name = st.text_input("New Column Name", key="step14_calculated_name")
    calculated_left = st.selectbox("First Numeric Column", numeric_columns, key="step14_calculated_left")
    calculated_operator = st.selectbox(
        "Operation", ["Add (+)", "Subtract (-)", "Multiply (*)", "Divide (/)"],
        key="step14_calculated_operator",
    )
    calculated_right = st.selectbox("Second Numeric Column", numeric_columns, key="step14_calculated_right")

    if not st.button("Create Calculated Column", key="step14_apply_calculated"):
        return

    calculated_name = calculated_name.strip()

    if not calculated_name:
        st.error("Please enter a name for the new column.")
        return
    if calculated_name in df.columns:
        st.error("A column with this name already exists.")
        return

    try:
        st.session_state.tabular_previous_df = df.copy()

        ops = {
            "Add (+)": lambda a, b: df[a] + df[b],
            "Subtract (-)": lambda a, b: df[a] - df[b],
            "Multiply (*)": lambda a, b: df[a] * df[b],
            "Divide (/)": lambda a, b: df[a] / df[b],
        }
        df[calculated_name] = ops[calculated_operator](calculated_left, calculated_right)

        st.session_state.tabular_df = df.copy()
        st.success(f"Calculated column '{calculated_name}' created.")
        st.rerun()

    except Exception as e:
        st.error(f"Unable to create calculated column: {e}")


def _extract_date_components(df):
    st.markdown("### Extract Date Components")

    datetime_columns = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()

    if not datetime_columns:
        st.info("No Date / Time columns were found. Convert a column to Date / Time first.")
        return

    date_column = st.selectbox("Date / Time Column", datetime_columns, key="step14_date_column")
    date_component = st.selectbox(
        "Component", ["Year", "Month", "Day", "Day of Week", "Quarter", "Hour"],
        key="step14_date_component",
    )

    if not st.button("Extract Component", key="step14_extract_date"):
        return

    component_names = {
        "Year": "year", "Month": "month", "Day": "day",
        "Day of Week": "day_of_week", "Quarter": "quarter", "Hour": "hour",
    }
    component_name = component_names[date_component]
    new_column_name = f"{date_column}_{component_name}"

    if new_column_name in df.columns:
        st.error(f"Column '{new_column_name}' already exists.")
        return

    st.session_state.tabular_previous_df = df.copy()

    accessors = {
        "Year": df[date_column].dt.year,
        "Month": df[date_column].dt.month,
        "Day": df[date_column].dt.day,
        "Day of Week": df[date_column].dt.dayofweek,
        "Quarter": df[date_column].dt.quarter,
        "Hour": df[date_column].dt.hour,
    }
    df[new_column_name] = accessors[date_component]

    st.session_state.tabular_df = df.copy()
    st.success(f"Created '{new_column_name}'.")
    st.rerun()


def _normalize_column(df):
    st.markdown("### Min-Max Normalization")

    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    if not numeric_columns:
        st.info("No numeric columns are available.")
        return

    normalize_column = st.selectbox("Numeric Column", numeric_columns, key="step14_normalize_column")
    normalized_name = st.text_input(
        "New Column Name", value=f"{normalize_column}_normalized", key="step14_normalized_name"
    )

    if not st.button("Normalize Column", key="step14_apply_normalize"):
        return

    normalized_name = normalized_name.strip()
    if not normalized_name or normalized_name in df.columns:
        st.error("Please provide a unique new column name.")
        return

    series = df[normalize_column]
    min_value, max_value = series.min(), series.max()

    st.session_state.tabular_previous_df = df.copy()

    if pd.isna(min_value) or pd.isna(max_value) or min_value == max_value:
        df[normalized_name] = 0.0
    else:
        df[normalized_name] = (series - min_value) / (max_value - min_value)

    st.session_state.tabular_df = df.copy()
    st.success(f"Normalized column '{normalize_column}'.")
    st.rerun()


def _standardize_column(df):
    st.markdown("### Z-Score Standardization")

    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    if not numeric_columns:
        st.info("No numeric columns are available.")
        return

    standardize_column = st.selectbox("Numeric Column", numeric_columns, key="step14_standardize_column")
    standardized_name = st.text_input(
        "New Column Name", value=f"{standardize_column}_standardized", key="step14_standardized_name"
    )

    if not st.button("Standardize Column", key="step14_apply_standardize"):
        return

    standardized_name = standardized_name.strip()
    if not standardized_name or standardized_name in df.columns:
        st.error("Please provide a unique new column name.")
        return

    series = df[standardize_column]
    mean_value, std_value = series.mean(), series.std()

    st.session_state.tabular_previous_df = df.copy()

    if pd.isna(std_value) or std_value == 0:
        df[standardized_name] = 0.0
    else:
        df[standardized_name] = (series - mean_value) / std_value

    st.session_state.tabular_df = df.copy()
    st.success(f"Standardized column '{standardize_column}'.")
    st.rerun()


def _text_case(df, mode):
    label = "Lowercase" if mode == "lower" else "Uppercase"
    st.markdown(f"### {label} Text")

    text_columns = df.select_dtypes(include=["object", "string", "category"]).columns.tolist()
    if not text_columns:
        st.info("No text columns are available.")
        return

    column = st.selectbox("Text Column", text_columns, key=f"step14_{mode}case_column")

    if not st.button(f"Convert to {label}", key=f"step14_apply_{mode}case"):
        return

    st.session_state.tabular_previous_df = df.copy()

    series = df[column].astype("string")
    df[column] = series.str.lower() if mode == "lower" else series.str.upper()

    st.session_state.tabular_df = df.copy()
    st.success(f"'{column}' converted to {mode}case.")
    st.rerun()


def _strip_whitespace(df):
    st.markdown("### Remove Leading / Trailing Whitespace")

    text_columns = df.select_dtypes(include=["object", "string", "category"]).columns.tolist()
    if not text_columns:
        st.info("No text columns are available.")
        return

    whitespace_column = st.selectbox("Text Column", text_columns, key="step14_whitespace_column")

    if not st.button("Strip Whitespace", key="step14_apply_whitespace"):
        return

    st.session_state.tabular_previous_df = df.copy()
    df[whitespace_column] = df[whitespace_column].astype("string").str.strip()
    st.session_state.tabular_df = df.copy()
    st.success(f"Whitespace removed from '{whitespace_column}'.")
    st.rerun()
