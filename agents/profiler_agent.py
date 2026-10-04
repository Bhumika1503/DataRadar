import pandas as pd


def profile_dataset(df: pd.DataFrame) -> dict:

    if df is None or df.empty:
        raise ValueError("Dataset is empty.")

    total_rows = len(df)
    total_columns = len(df.columns)

    working = df.copy()

    working = working.replace(
        r"^\s*$",
        pd.NA,
        regex=True
    )

    missing = working.isna().sum()

    duplicates = int(
        working.duplicated().sum()
    )

    column_profiles = []

    for column in working.columns:

        series = working[column]

        non_null = series.dropna()

        column_profiles.append({
            "column": str(column),
            "data_type": str(series.dtype),
            "total_rows": total_rows,
            "non_null": int(series.notna().sum()),
            "missing": int(series.isna().sum()),
            "missing_pct": round(
                series.isna().mean() * 100,
                2
            ),
            "unique_values": int(
                series.nunique(dropna=True)
            ),
            "sample_values": ", ".join(
                str(value)
                for value in non_null.unique()[:3]
            )
        })

    numeric_data = pd.DataFrame()

    for column in working.columns:

        converted = pd.to_numeric(
            working[column],
            errors="coerce"
        )

        if converted.notna().sum() > 0:

            numeric_data[column] = converted

    if numeric_data.shape[1] > 0:

        numeric_stats = numeric_data.describe().transpose()

        numeric_stats = numeric_stats.reset_index()

        numeric_stats = numeric_stats.rename(
            columns={
                "index": "column"
            }
        )

    else:

        numeric_stats = pd.DataFrame(
            columns=[
                "column",
                "count",
                "mean",
                "std",
                "min",
                "25%",
                "50%",
                "75%",
                "max"
            ]
        )

    return {
        "total_rows": total_rows,
        "total_columns": total_columns,
        "missing_cells": int(
            missing.sum()
        ),
        "duplicate_rows": duplicates,
        "column_profile": pd.DataFrame(
            column_profiles
        ),
        "numeric_stats": numeric_stats,
        "missing_by_column": missing
    }