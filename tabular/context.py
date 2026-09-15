"""
DatasetContext: everything derived from the uploaded dataframe that more
than one step needs (column roles, missing-value counts, the quality
summary table, constant columns, etc).

In the original monolithic script these were computed ad hoc, sometimes
multiple times in different steps, and in one case (`quality_df`) only
inside a single step's `if` block — meaning any other step referencing it
would raise NameError unless the user happened to visit Data Quality first
in the same session. Computing everything once here removes that landmine
and the duplicate work.
"""

from dataclasses import dataclass, field
from typing import List

import pandas as pd


@dataclass
class DatasetContext:
    total_rows: int
    total_columns: int
    numeric_columns: List[str]
    categorical_columns: List[str]
    date_columns: List[str]
    missing_values: int
    duplicate_rows: int
    constant_columns: List[str]
    quality_df: pd.DataFrame = field(repr=False)


def build_context(df: pd.DataFrame) -> DatasetContext:
    total_rows = len(df)
    total_columns = len(df.columns)

    numeric_columns = df.select_dtypes(include="number").columns.tolist()

    categorical_columns = (
        df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    )

    date_columns = (
        df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()
    )

    missing_values = int(df.isnull().sum().sum())
    duplicate_rows = int(df.duplicated().sum())

    constant_columns = [
        column for column in df.columns if df[column].nunique(dropna=False) <= 1
    ]

    quality_df = pd.DataFrame(
        {
            "Column": df.columns,
            "Data Type": [str(df[col].dtype) for col in df.columns],
            "Missing": [int(df[col].isna().sum()) for col in df.columns],
            "Missing %": [
                round((df[col].isna().sum() / len(df)) * 100, 2) if len(df) > 0 else 0
                for col in df.columns
            ],
            "Unique": [int(df[col].nunique(dropna=True)) for col in df.columns],
        }
    )

    return DatasetContext(
        total_rows=total_rows,
        total_columns=total_columns,
        numeric_columns=numeric_columns,
        categorical_columns=categorical_columns,
        date_columns=date_columns,
        missing_values=missing_values,
        duplicate_rows=duplicate_rows,
        constant_columns=constant_columns,
        quality_df=quality_df,
    )
