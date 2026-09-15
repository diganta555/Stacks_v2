"""Automatic Anomaly Detection — IQR or Z-score, single column + dataset-wide scan."""

import pandas as pd
import streamlit as st

from tabular.context import DatasetContext


def render(df: pd.DataFrame, ctx: DatasetContext, tabular_file=None) -> None:
    st.markdown("## Automatic Anomaly Detection")
    st.caption(
        "Automatically detect unusual numeric values using the Interquartile "
        "Range (IQR) method."
    )

    numeric_columns = ctx.numeric_columns

    if not numeric_columns:
        st.info("Anomaly detection requires at least one numeric column.")
    else:
        _render_single_column_detection(df, numeric_columns)

    if len(numeric_columns) >= 2:
        _render_dataset_wide_scan(df, numeric_columns)


def _render_single_column_detection(df, numeric_columns):
    anomaly_method = st.selectbox("Detection Method", ["IQR", "Z-Score"], key="anomaly_method")

    z_score_threshold = 3.0
    if anomaly_method == "Z-Score":
        z_score_threshold = st.slider(
            "Z-Score Threshold", min_value=1.0, max_value=5.0, value=3.0, step=0.5,
            key="z_score_threshold",
        )

    anomaly_column = st.selectbox("Select numeric column", numeric_columns, key="anomaly_column")
    anomaly_series = pd.to_numeric(df[anomaly_column], errors="coerce")
    valid_anomaly_data = anomaly_series.dropna()

    if valid_anomaly_data.empty:
        st.warning("No valid numeric values found in this column.")
        return

    if len(valid_anomaly_data) < 4:
        st.info("At least 4 valid numeric values are recommended for anomaly detection.")
        return

    q1 = q3 = iqr = lower_bound = upper_bound = None

    if anomaly_method == "IQR":
        q1 = valid_anomaly_data.quantile(0.25)
        q3 = valid_anomaly_data.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        anomaly_mask = (anomaly_series < lower_bound) | (anomaly_series > upper_bound)
    else:
        mean_value = valid_anomaly_data.mean()
        std_value = valid_anomaly_data.std()
        if pd.isna(std_value) or std_value == 0:
            anomaly_mask = pd.Series(False, index=df.index)
        else:
            z_scores = (anomaly_series - mean_value) / std_value
            anomaly_mask = z_scores.abs() > z_score_threshold

    anomaly_mask = anomaly_mask.fillna(False)
    anomaly_count = int(anomaly_mask.sum())
    valid_count = int(valid_anomaly_data.count())
    anomaly_percentage = (anomaly_count / valid_count) * 100 if valid_count > 0 else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Anomalies", f"{anomaly_count:,}")
    with c2:
        st.metric("Valid Values", f"{valid_count:,}")
    with c3:
        st.metric("Anomaly %", f"{anomaly_percentage:.2f}%")

    if anomaly_method == "IQR":
        b1, b2, b3 = st.columns(3)
        with b1:
            st.metric("Q1", f"{q1:,.2f}")
        with b2:
            st.metric("Q3", f"{q3:,.2f}")
        with b3:
            st.metric("IQR", f"{iqr:,.2f}")
        st.info(f"Normal range: {lower_bound:,.2f} to {upper_bound:,.2f}")
    else:
        st.info(
            f"Values with an absolute Z-score greater than {z_score_threshold:.1f} "
            f"are classified as anomalies."
        )

    st.markdown("### Detected Anomalies")

    anomaly_records = df[anomaly_mask].copy()

    if anomaly_records.empty:
        st.success("No anomalies were detected in this column.")
    else:
        anomaly_records["_Anomaly_Value"] = pd.to_numeric(
            anomaly_records[anomaly_column], errors="coerce"
        )

        if anomaly_method == "IQR":
            anomaly_records["_Distance_From_Range"] = anomaly_records["_Anomaly_Value"].apply(
                lambda value: lower_bound - value if value < lower_bound else value - upper_bound
            )
        else:
            anomaly_records["_Z_Score"] = (
                anomaly_records["_Anomaly_Value"] - valid_anomaly_data.mean()
            ) / valid_anomaly_data.std()

        st.dataframe(anomaly_records, use_container_width=True, hide_index=True)

        anomaly_csv = anomaly_records.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download Anomalies",
            data=anomaly_csv,
            file_name="detected_anomalies.csv",
            mime="text/csv",
            key="download_anomalies",
        )

    st.markdown("### Anomaly Summary")

    if anomaly_count == 0:
        st.success(f"No unusual values were detected in `{anomaly_column}`.")
    elif anomaly_percentage < 1:
        st.info(
            f"{anomaly_count} unusual value(s) were detected in `{anomaly_column}`. "
            f"The anomaly rate is low ({anomaly_percentage:.2f}%)."
        )
    elif anomaly_percentage < 5:
        st.warning(
            f"{anomaly_count} unusual value(s) were detected in `{anomaly_column}`. "
            f"Review these records before using the data for analysis."
        )
    else:
        st.error(
            f"{anomaly_count} unusual value(s) were detected in `{anomaly_column}`. "
            f"The anomaly rate is {anomaly_percentage:.2f}%, which may significantly "
            f"affect analysis."
        )


def _render_dataset_wide_scan(df, numeric_columns):
    st.markdown("### Dataset-Wide Anomaly Scan")

    if not st.button("Scan All Numeric Columns", key="scan_all_anomalies"):
        return

    all_anomaly_results = []

    for column in numeric_columns:
        series = pd.to_numeric(df[column], errors="coerce")
        valid_values = series.dropna()

        if len(valid_values) < 4:
            continue

        q1_value = valid_values.quantile(0.25)
        q3_value = valid_values.quantile(0.75)
        iqr_value = q3_value - q1_value
        lower_value = q1_value - 1.5 * iqr_value
        upper_value = q3_value + 1.5 * iqr_value

        column_anomalies = (series < lower_value) | (series > upper_value)
        anomaly_count_column = int(column_anomalies.sum())
        anomaly_rate_column = (anomaly_count_column / len(valid_values)) * 100

        all_anomaly_results.append(
            {
                "Column": column,
                "Valid Values": len(valid_values),
                "Anomalies": anomaly_count_column,
                "Anomaly %": round(anomaly_rate_column, 2),
                "Lower Bound": round(lower_value, 2),
                "Upper Bound": round(upper_value, 2),
            }
        )

    if not all_anomaly_results:
        st.info("No suitable numeric columns were available for the dataset-wide scan.")
        return

    anomaly_scan_df = pd.DataFrame(all_anomaly_results).sort_values(
        "Anomaly %", ascending=False
    )
    st.dataframe(anomaly_scan_df, use_container_width=True, hide_index=True)

    highest_anomaly_column = anomaly_scan_df.iloc[0]
    st.info(
        f"Highest anomaly rate: `{highest_anomaly_column['Column']}` with "
        f"{highest_anomaly_column['Anomaly %']:.2f}% potential anomalies."
    )
