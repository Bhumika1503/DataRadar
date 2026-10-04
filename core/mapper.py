
import json
import re
from datetime import date, datetime
from decimal import Decimal
from difflib import SequenceMatcher

import pandas as pd

from sqlalchemy import (
    MetaData, Table, Column, Text,
    inspect, select, insert, text
)
from sqlalchemy.sql.sqltypes import (
    Integer, Numeric, Float, Boolean,
    Date, DateTime, JSON
)

from core.database import get_engine


# ---------- SOURCE DATA ----------

def get_jobs():
    engine = get_engine()

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT job_id, filename, row_count, created_at
            FROM ingestion_jobs
            ORDER BY created_at DESC
        """)).mappings().all()

    return [dict(row) for row in rows]


def get_source_data(job_id):
    engine = get_engine()

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT record
            FROM staging_records
            WHERE job_id = :job_id
            ORDER BY row_number
        """), {"job_id": str(job_id)}).scalars().all()

    if not rows:
        raise ValueError("No staging records found.")

    records = [
        json.loads(row) if isinstance(row, str) else row
        for row in rows
    ]

    return pd.DataFrame(records)


# ---------- TARGET DISCOVERY ----------

def get_target_tables():
    engine = get_engine()
    inspector = inspect(engine)

    internal = {
        "ingestion_jobs",
        "staging_records"
    }

    return [
        name
        for name in inspector.get_table_names(schema="public")
        if name not in internal
    ]


def get_target_columns(table_name):
    engine = get_engine()
    inspector = inspect(engine)

    if table_name not in inspector.get_table_names(
        schema="public"
    ):
        raise ValueError("Target table does not exist.")

    return inspector.get_columns(
        table_name,
        schema="public"
    )


# ---------- MAPPING SUGGESTIONS ----------

def normalize_name(name):
    return re.sub(
        r"[^a-z0-9]",
        "",
        str(name).lower()
    )


def suggest_mappings(source_columns, target_columns):
    suggestions = {}
    used_targets = set()

    for source in source_columns:
        source_normalized = normalize_name(source)
        best_target = None
        best_score = 0

        for target in target_columns:
            if target in used_targets:
                continue

            target_normalized = normalize_name(target)

            score = SequenceMatcher(
                None,
                source_normalized,
                target_normalized
            ).ratio()

            if score > best_score:
                best_score = score
                best_target = target

        if best_score >= 0.75:
            suggestions[source] = best_target
            used_targets.add(best_target)
        else:
            suggestions[source] = None

    return suggestions


# ---------- NEW TABLE ----------

def validate_table_name(name):
    if not re.fullmatch(
        r"[a-z][a-z0-9_]{0,62}",
        name
    ):
        raise ValueError(
            "Use lowercase letters, numbers and "
            "underscores. Start with a letter."
        )


def create_target_table(table_name, columns):
    validate_table_name(table_name)

    if not columns:
        raise ValueError("At least one column is required.")

    if len(set(columns)) != len(columns):
        raise ValueError("Duplicate target columns.")

    for column in columns:
        validate_table_name(column)

    engine = get_engine()

    if table_name in inspect(engine).get_table_names(
        schema="public"
    ):
        raise ValueError("Table already exists.")

    metadata = MetaData()

    table = Table(
        table_name,
        metadata,
        *[
            Column(column, Text)
            for column in columns
        ],
        schema="public"
    )

    metadata.create_all(engine, tables=[table])

    return table_name


# ---------- TYPE CONVERSION ----------

def convert_value(value, column_type):
    if value is None:
        return None

    if isinstance(value, (dict, list)):
        if isinstance(column_type, JSON):
            return value
        if isinstance(column_type, Text):
            return json.dumps(value)
        raise ValueError("Nested value incompatible with target.")

    if isinstance(value, str) and not value.strip():
        if not isinstance(column_type, Text):
            return None

    if isinstance(column_type, Boolean):
        if isinstance(value, bool):
            return value

        normalized = str(value).strip().lower()

        if normalized in ("true", "1", "yes"):
            return True
        if normalized in ("false", "0", "no"):
            return False

        raise ValueError("Invalid boolean value.")

    if isinstance(column_type, Integer):
        number = Decimal(str(value))
        if number != number.to_integral_value():
            raise ValueError("Invalid integer value.")
        return int(number)

    if isinstance(column_type, Numeric):
        return Decimal(str(value))

    if isinstance(column_type, Float):
        return float(value)

    if isinstance(column_type, DateTime):
        return pd.to_datetime(value).to_pydatetime()

    if isinstance(column_type, Date):
        return pd.to_datetime(value).date()

    if isinstance(column_type, JSON):
        return value

    return str(value)


# ---------- VALIDATION ----------

def validate_mapping(mapping, target_columns):
    selected = [
        target for target in mapping.values()
        if target
    ]

    if not selected:
        raise ValueError("Select at least one mapping.")

    if len(selected) != len(set(selected)):
        raise ValueError(
            "Multiple source columns cannot map "
            "to the same target column."
        )

    available = {
        column["name"]
        for column in target_columns
    }

    if not set(selected).issubset(available):
        raise ValueError("Invalid target column selected.")

    mapped = set(selected)

    for column in target_columns:
        if (
            column["name"] not in mapped
            and not column["nullable"]
            and column.get("default") is None
            and not column.get("autoincrement")
            and column.get("identity") is None
            and column.get("computed") is None
        ):
            raise ValueError(
                f"Required target column missing: "
                f"{column['name']}"
            )


# ---------- PREPARE RECORDS ----------

def prepare_records(df, mapping, table):
    records = []
    errors = []

    for index, row in df.iterrows():
        output = {}

        for source, target in mapping.items():
            if not target:
                continue

            column = table.c[target]
            value = row[source]

            if pd.isna(value) if not isinstance(
                value, (list, dict)
            ) else False:
                value = None

            try:
                converted = convert_value(
                    value,
                    column.type
                )

                if converted is None and not column.nullable:
                    raise ValueError("NULL not allowed.")

                output[target] = converted

            except Exception as exc:
                errors.append({
                    "row": int(index) + 1,
                    "source": source,
                    "target": target,
                    "error": str(exc)
                })

        records.append(output)

    return records, errors


# ---------- LOAD ----------

def load_to_target(df, table_name, mapping):
    engine = get_engine()
    metadata = MetaData()

    table = Table(
        table_name,
        metadata,
        autoload_with=engine,
        schema="public"
    )

    target_columns = get_target_columns(table_name)

    validate_mapping(mapping, target_columns)

    records, errors = prepare_records(
        df,
        mapping,
        table
    )

    if errors:
        return {
            "loaded": 0,
            "errors": errors
        }

    with engine.begin() as conn:
        if records:
            conn.execute(insert(table), records)

    return {
        "loaded": len(records),
        "errors": []
    }