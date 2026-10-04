from __future__ import annotations

import re
from difflib import SequenceMatcher

import pandas as pd


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_name(name: str) -> str:
    """
    Normalize a column name so that similar names
    can be compared reliably.
    """

    name = str(name).strip().lower()

    # Replace separators with spaces
    name = re.sub(r"[_\-\./]+", " ", name)

    # Split camelCase / PascalCase
    name = re.sub(
        r"([a-z])([A-Z])",
        r"\1 \2",
        name
    )

    # Remove remaining special characters
    name = re.sub(
        r"[^a-z0-9 ]+",
        " ",
        name
    )

    # Remove extra spaces
    name = re.sub(
        r"\s+",
        " ",
        name
    ).strip()

    return name


# ============================================================
# SYNONYMS
# ============================================================

SYNONYMS = {
    "customer": {
        "client",
        "buyer",
        "consumer"
    },
    "name": {
        "fullname",
        "full name",
        "customer name",
        "customername"
    },
    "email": {
        "emailid",
        "email id",
        "mail",
        "mailid",
        "e mail"
    },
    "phone": {
        "mobile",
        "mobile number",
        "phone number",
        "contact",
        "contact number",
        "telephone"
    },
    "address": {
        "location",
        "residential address",
        "customer address"
    },
    "id": {
        "identifier",
        "number",
        "code"
    },
    "date": {
        "day",
        "timestamp"
    },
    "amount": {
        "price",
        "cost",
        "value",
        "total"
    },
    "quantity": {
        "qty",
        "count",
        "units"
    },
}


# ============================================================
# TOKENIZATION
# ============================================================

def tokenize(name: str) -> set[str]:
    """
    Convert a normalized column name into tokens.
    """

    normalized = normalize_name(name)

    if not normalized:
        return set()

    return set(normalized.split())


# ============================================================
# SYNONYM EXPANSION
# ============================================================

def expand_tokens(tokens: set[str]) -> set[str]:
    """
    Add known synonyms to the token set.
    """

    expanded = set(tokens)

    for token in list(tokens):

        for key, synonyms in SYNONYMS.items():

            if token == key:
                expanded.update(synonyms)

            elif token in synonyms:
                expanded.add(key)

    return expanded


# ============================================================
# TOKEN SIMILARITY
# ============================================================

def token_similarity(
    source: str,
    target: str
) -> float:
    """
    Calculate similarity between source and target
    column names using token overlap and string similarity.
    """

    source_normalized = normalize_name(source)
    target_normalized = normalize_name(target)

    if not source_normalized or not target_normalized:
        return 0.0

    source_tokens = expand_tokens(
        tokenize(source)
    )

    target_tokens = expand_tokens(
        tokenize(target)
    )

    if not source_tokens or not target_tokens:
        return 0.0

    intersection = source_tokens.intersection(
        target_tokens
    )

    union = source_tokens.union(
        target_tokens
    )

    token_score = (
        len(intersection) / len(union)
        if union
        else 0.0
    )

    sequence_score = SequenceMatcher(
        None,
        source_normalized,
        target_normalized
    ).ratio()

    # Give more importance to semantic token overlap.
    final_score = (
        token_score * 0.65
        + sequence_score * 0.35
    )

    return round(
        final_score,
        4
    )


# ============================================================
# DATA TYPE NORMALIZATION
# ============================================================

def normalize_dtype(dtype) -> str:
    """
    Convert Pandas dtype into a simpler category.
    """

    dtype_string = str(dtype).lower()

    if "int" in dtype_string:
        return "integer"

    if "float" in dtype_string:
        return "float"

    if "bool" in dtype_string:
        return "boolean"

    if "datetime" in dtype_string:
        return "datetime"

    return "string"


# ============================================================
# TARGET SCHEMA PREPARATION
# ============================================================

def prepare_target_schema(
    target_schema: pd.DataFrame
) -> pd.DataFrame:
    """
    Validate and normalize target schema.

    Required columns:
        target_column
        target_dtype

    Optional:
        nullable
        description
    """

    required_columns = {
        "target_column",
        "target_dtype"
    }

    missing_columns = (
        required_columns
        - set(target_schema.columns)
    )

    if missing_columns:
        raise ValueError(
            "Target schema is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    schema = target_schema.copy()

    schema["target_column"] = (
        schema["target_column"]
        .astype(str)
        .str.strip()
    )

    schema["target_dtype"] = (
        schema["target_dtype"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    return schema


# ============================================================
# GENERATE MAPPINGS
# ============================================================

def generate_mappings(
    source_df: pd.DataFrame,
    target_schema: pd.DataFrame,
    minimum_confidence: float = 0.35
) -> list[dict]:
    """
    Generate source-to-target mapping suggestions.

    Each source column gets its best target-column match.
    """

    if source_df is None or source_df.empty:
        raise ValueError(
            "Source dataset is empty."
        )

    target_schema = prepare_target_schema(
        target_schema
    )

    if target_schema.empty:
        raise ValueError(
            "Target schema is empty."
        )

    mappings = []

    source_columns = list(
        source_df.columns
    )

    target_columns = list(
        target_schema["target_column"]
    )

    for source_column in source_columns:

        best_target = None
        best_score = 0.0

        for target_column in target_columns:

            score = token_similarity(
                source_column,
                target_column
            )

            if score > best_score:
                best_score = score
                best_target = target_column

        source_dtype = normalize_dtype(
            source_df[source_column].dtype
        )

        target_row = target_schema[
            target_schema["target_column"]
            == best_target
        ]

        if not target_row.empty:
            target_dtype = normalize_dtype(
                target_row.iloc[0]["target_dtype"]
            )
        else:
            target_dtype = "unknown"

        if best_score >= 0.80:
            confidence = "High"

        elif best_score >= 0.55:
            confidence = "Medium"

        elif best_score >= minimum_confidence:
            confidence = "Low"

        else:
            best_target = None
            confidence = "Unmapped"

        mappings.append({
            "source_column": str(
                source_column
            ),
            "source_dtype": source_dtype,
            "target_column": best_target,
            "target_dtype": target_dtype,
            "similarity_score": best_score,
            "confidence": confidence,
            "approved": False
        })

    return mappings


# ============================================================
# VALIDATE MAPPINGS
# ============================================================

def validate_mappings(
    mappings: list[dict]
) -> dict:
    """
    Validate generated mappings.

    Checks:
        - unmapped columns
        - duplicate target assignments
        - approved mappings
    """

    unmapped = [
        mapping
        for mapping in mappings
        if mapping["target_column"] is None
    ]

    mapped_targets = [
        mapping["target_column"]
        for mapping in mappings
        if mapping["target_column"] is not None
    ]

    duplicates = sorted({
        target
        for target in mapped_targets
        if mapped_targets.count(target) > 1
    })

    approved = [
        mapping
        for mapping in mappings
        if mapping.get("approved", False)
    ]

    return {
        "total_source_columns": len(mappings),
        "mapped_columns": len(mapped_targets),
        "unmapped_columns": len(unmapped),
        "duplicate_target_assignments": len(
            duplicates
        ),
        "approved_mappings": len(approved),
        "unmapped": unmapped,
        "duplicate_targets": duplicates
    }


# ============================================================
# APPLY MAPPINGS
# ============================================================

def apply_mappings(
    source_df: pd.DataFrame,
    mappings: list[dict]
) -> pd.DataFrame:
    """
    Create a target-shaped DataFrame using approved mappings.
    """

    approved_mappings = [
        mapping
        for mapping in mappings
        if mapping.get("approved", False)
        and mapping.get("target_column")
    ]

    if not approved_mappings:
        raise ValueError(
            "No approved mappings available."
        )

    result = pd.DataFrame()

    used_targets = set()

    for mapping in approved_mappings:

        source_column = mapping[
            "source_column"
        ]

        target_column = mapping[
            "target_column"
        ]

        if source_column not in source_df.columns:
            continue

        if target_column in used_targets:
            raise ValueError(
                f"Target column '{target_column}' "
                "has been assigned more than once."
            )

        result[target_column] = (
            source_df[source_column]
        )

        used_targets.add(
            target_column
        )

    return result