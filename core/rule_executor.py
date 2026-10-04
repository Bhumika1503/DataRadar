
import re
import pandas as pd


EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
)


def execute_rule(df, rule):
    rule_type = rule["type"]
    column = rule["column"]
    params = rule.get("params", {})

    if rule_type == "duplicate_rows":
        # Mark all occurrences of duplicated rows.
        failed = df.duplicated(keep=False)

    else:
        if column not in df.columns:
            raise ValueError(f"Column not found: {column}")

        series = df[column]

        if rule_type == "not_null":
            failed = (
                series.isna()
                | series.astype("string").str.strip().eq("")
            )

        elif rule_type == "unique":
            failed = series.duplicated(keep=False)
            failed = failed & series.notna()

        elif rule_type == "email":
            values = series.astype("string").str.strip()
            failed = (
                values.notna()
                & ~values.str.fullmatch(
                    EMAIL_PATTERN.pattern,
                    na=False
                )
            )

        elif rule_type == "range":
            numeric = pd.to_numeric(
                series, errors="coerce"
            )

            failed = series.notna() & numeric.isna()

            minimum = params.get("minimum")
            maximum = params.get("maximum")

            if minimum is not None:
                failed = failed | (
                    numeric.notna()
                    & numeric.lt(minimum)
                )

            if maximum is not None:
                failed = failed | (
                    numeric.notna()
                    & numeric.gt(maximum)
                )

        elif rule_type == "valid_date":
            # Strict ISO dates prevent ambiguous parsing.
            values = series.astype("string").str.strip()

            parsed = pd.to_datetime(
                values,
                format="%Y-%m-%d",
                errors="coerce"
            )

            failed = (
                values.notna()
                & parsed.isna()
            )

        else:
            raise ValueError(
                f"Unsupported rule type: {rule_type}"
            )

    failed = failed.fillna(False).astype(bool)

    return {
        "rule_id": rule["id"],
        "column": column,
        "rule_type": rule_type,
        "severity": rule["severity"],
        "total_records": len(df),
        "failed_count": int(failed.sum()),
        "passed_count": int((~failed).sum()),
        "status": (
            "PASS" if not failed.any() else "FAIL"
        ),
        "failed_rows": df.loc[failed].copy()
    }


def execute_rules(df, rules):
    results = []

    for rule in rules:
        if rule.get("approved", False):
            results.append(
                execute_rule(df, rule)
            )

    return results