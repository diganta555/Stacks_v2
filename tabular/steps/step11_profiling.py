"""Automatic Dataset Profiling — health score, per-column profile, numeric/categorical/date detail."""

import pandas as pd
import streamlit as st

from tabular.context import DatasetContext


def render(df: pd.DataFrame, ctx: DatasetContext, tabular_file=None) -> None:
    st.markdown("## Automatic Dataset Profiling")
    st.caption(
        "Automatically generate a comprehensive profile of the current dataset, "
        "including column roles, data quality, statistics, cardinality, and "
        "potential outliers."
    )

    if df is None or df.empty:
        st.info("Upload a dataset to generate an automatic profile.")
        return

    if not st.button("Generate Dataset Profile", key="generate_dataset_profile"):
        return

    total_rows = len(df)
    total_columns = len(df.columns)
    total_cells = total_rows * total_columns
    total_missing = int(df.isna().sum().sum())
    missing_percentage = (total_missing / total_cells) * 100 if total_cells > 0 else 0
    duplicate_count = int(df.duplicated().sum())
    duplicate_percentage = (duplicate_count / total_rows) * 100 if total_rows > 0 else 0
    constant_columns = [c for c in df.columns if df[c].nunique(dropna=False) <= 1]

    health_score = 100.0
    health_score -= min(missing_percentage, 40)
    health_score -= min(duplicate_percentage, 20)
    if total_columns > 0:
        constant_percentage = (len(constant_columns) / total_columns) * 100
        health_score -= min(constant_percentage, 20)
    health_score = max(0, min(100, health_score))

    st.markdown("### Dataset Summary")
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
        st.success("Dataset health is good. Only minor data-quality issues were detected.")
    elif health_score >= 60:
        st.warning("Dataset health is moderate. Some data-quality improvements are recommended.")
    else:
        st.error("Dataset health is poor. Significant data-quality issues were detected.")

    st.markdown("### Column Profile")

    column_profile = []
    for column in df.columns:
        series = df[column]
        missing_count = int(series.isna().sum())
        missing_percentage_column = (missing_count / total_rows) * 100 if total_rows > 0 else 0
        unique_count = int(series.nunique(dropna=True))

        if pd.api.types.is_numeric_dtype(series):
            column_role = "Numeric"
        elif pd.api.types.is_datetime64_any_dtype(series):
            column_role = "Date / Time"
        elif pd.api.types.is_bool_dtype(series):
            column_role = "Boolean"
        else:
            column_role = "Categorical / Text"

        column_profile.append(
            {
                "Column": column,
                "Data Type": str(series.dtype),
                "Role": column_role,
                "Missing": missing_count,
                "Missing %": round(missing_percentage_column, 2),
                "Unique Values": unique_count,
            }
        )

    st.dataframe(pd.DataFrame(column_profile), use_container_width=True, hide_index=True)

    numeric_profile_columns = df.select_dtypes(include="number").columns.tolist()
    if numeric_profile_columns:
        st.markdown("### Numeric Column Profile")

        numeric_profile = []
        for column in numeric_profile_columns:
            series = df[column].dropna()
            if series.empty:
                continue
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            outlier_count = int(((series < lower_bound) | (series > upper_bound)).sum())

            numeric_profile.append(
                {
                    "Column": column,
                    "Mean": round(series.mean(), 3),
                    "Median": round(series.median(), 3),
                    "Std Dev": round(series.std(), 3),
                    "Minimum": round(series.min(), 3),
                    "Maximum": round(series.max(), 3),
                    "Skewness": round(series.skew(), 3),
                    "Potential Outliers": outlier_count,
                }
            )

        if numeric_profile:
            st.dataframe(pd.DataFrame(numeric_profile), use_container_width=True, hide_index=True)
    else:
        st.info("No numeric columns were found for statistical profiling.")

    categorical_profile_columns = df.select_dtypes(include=["object", "category"]).columns.tolist()
    if categorical_profile_columns:
        st.markdown("### Categorical Column Profile")

        categorical_profile = []
        for column in categorical_profile_columns:
            series = df[column].dropna()
            if series.empty:
                continue
            value_counts = series.value_counts()
            top_value = value_counts.index[0]
            top_frequency = int(value_counts.iloc[0])
            top_percentage = (top_frequency / len(series)) * 100

            categorical_profile.append(
                {
                    "Column": column,
                    "Unique Values": int(series.nunique()),
                    "Top Value": str(top_value),
                    "Top Frequency": top_frequency,
                    "Top %": round(top_percentage, 2),
                }
            )

        if categorical_profile:
            st.dataframe(pd.DataFrame(categorical_profile), use_container_width=True, hide_index=True)

    datetime_columns = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()
    if datetime_columns:
        st.markdown("### Date / Time Profile")

        date_profile = []
        for column in datetime_columns:
            series = df[column].dropna()
            if series.empty:
                continue
            date_profile.append(
                {
                    "Column": column,
                    "Start Date": series.min(),
                    "End Date": series.max(),
                    "Date Range": series.max() - series.min(),
                }
            )

        if date_profile:
            st.dataframe(pd.DataFrame(date_profile), use_container_width=True, hide_index=True)

    st.markdown("### Automatic Profiling Findings")

    findings = []

    if total_missing > 0:
        findings.append(
            f"Dataset contains {total_missing:,} missing values "
            f"({missing_percentage:.2f}% of all cells)."
        )

    if duplicate_count > 0:
        findings.append(f"Dataset contains {duplicate_count:,} duplicate rows.")

    if constant_columns:
        findings.append(
            f"{len(constant_columns)} constant column(s) contain only one unique value."
        )

    if numeric_profile_columns:
        total_potential_outliers = 0
        for column in numeric_profile_columns:
            series = df[column].dropna()
            if series.empty:
                continue
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            total_potential_outliers += int(((series < lower_bound) | (series > upper_bound)).sum())

        if total_potential_outliers > 0:
            findings.append(
                f"{total_potential_outliers:,} potential numeric outlier values were "
                f"detected using the IQR method."
            )

    if not findings:
        st.success("No major data-quality issues were detected during automatic profiling.")
    else:
        for finding in findings:
            st.warning(finding)

    st.success("Automatic dataset profiling completed successfully.")
