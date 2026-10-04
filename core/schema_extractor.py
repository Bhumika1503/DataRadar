import pandas as pd


def get_schema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create a simple schema representation
    from a DataFrame.
    """

    if df is None or df.empty:
        raise ValueError("Dataset is empty.")

    schema = pd.DataFrame({
        "column_name": df.columns.astype(str),
        "data_type": [
            str(dtype)
            for dtype in df.dtypes
        ]
    })

    return schema


def compare_schemas(
    previous_schema: pd.DataFrame,
    current_schema: pd.DataFrame
) -> dict:
    """
    Compare two schemas and identify:

    - Added columns
    - Removed columns
    - Changed data types
    """

    previous = {
        row["column_name"]: row["data_type"]
        for _, row in previous_schema.iterrows()
    }

    current = {
        row["column_name"]: row["data_type"]
        for _, row in current_schema.iterrows()
    }

    previous_columns = set(previous.keys())
    current_columns = set(current.keys())

    added_columns = sorted(
        current_columns - previous_columns
    )

    removed_columns = sorted(
        previous_columns - current_columns
    )

    changed_types = []

    common_columns = (
        previous_columns & current_columns
    )

    for column in sorted(common_columns):

        old_type = previous[column]
        new_type = current[column]

        if old_type != new_type:

            changed_types.append({
                "column_name": column,
                "previous_type": old_type,
                "current_type": new_type
            })

    return {
        "added_columns": added_columns,
        "removed_columns": removed_columns,
        "changed_types": changed_types,
        "has_drift": bool(
            added_columns
            or removed_columns
            or changed_types
        )
    }