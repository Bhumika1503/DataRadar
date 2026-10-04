
import pandas as pd


def generate_rules(df: pd.DataFrame) -> list[dict]:
    """Suggest data quality rules from a dataset."""

    rules = []

    for column in df.columns:
        series = df[column]
        name = str(column).lower()
        rule_id = len(rules) + 1

        def add(rule_type, dimension, severity, **params):
            nonlocal rule_id
            rules.append({
                "id": f"DQ_{len(rules) + 1:03d}",
                "column": str(column),
                "type": rule_type,
                "dimension": dimension,
                "severity": severity,
                "params": params,
                "approved": False
            })

        # Required-field suggestion
        if (
            name.endswith("_id")
            or name in {"id", "email", "name"}
        ):
            add(
                "not_null",
                "Completeness",
                "High"
            )

        # Unique identifier suggestion
        if name == "id" or name.endswith("_id"):
            add(
                "unique",
                "Uniqueness",
                "High"
            )

        # Email format
        if "email" in name:
            add(
                "email",
                "Validity",
                "Medium"
            )

        # Numeric ranges
        if pd.api.types.is_numeric_dtype(series):
            if "age" in name:
                add(
                    "range",
                    "Validity",
                    "High",
                    minimum=0,
                    maximum=120
                )

            elif any(
                word in name
                for word in ["amount", "price", "quantity"]
            ):
                add(
                    "range",
                    "Validity",
                    "Medium",
                    minimum=0,
                    maximum=None
                )

        # Date validity
        if "date" in name:
            add(
                "valid_date",
                "Validity",
                "Medium"
            )

    # Dataset-level duplicate check
    rules.append({
        "id": f"DQ_{len(rules) + 1:03d}",
        "column": "__all__",
        "type": "duplicate_rows",
        "dimension": "Uniqueness",
        "severity": "Medium",
        "params": {},
        "approved": False
    })

    return rules