import json
import math
from datetime import date, datetime
from decimal import Decimal

import pandas as pd
import streamlit as st

from sqlalchemy import create_engine, text


# ============================================================
# DATABASE CONNECTION
# ============================================================

@st.cache_resource
def get_engine():
    """
    Create and cache the PostgreSQL SQLAlchemy engine.
    """

    database_url = st.secrets["DATABASE_URL"]

    return create_engine(
        database_url,
        pool_pre_ping=True
    )


# ============================================================
# TEST CONNECTION
# ============================================================

def test_connection():
    """
    Test PostgreSQL connection and return database name.
    """

    engine = get_engine()

    with engine.connect() as connection:

        return connection.execute(
            text("SELECT current_database()")
        ).scalar_one()


# ============================================================
# CLEAN VALUES FOR JSON
# ============================================================

def clean_value(value):
    """
    Convert Pandas / Python values into JSON-safe values.
    """

    if value is None:
        return None

    if isinstance(value, (list, dict)):
        return value

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, float):

        if not math.isfinite(value):
            return None

    if pd.api.types.is_scalar(value):

        try:

            if pd.isna(value):
                return None

        except (TypeError, ValueError):

            pass

    if hasattr(value, "item"):

        try:
            return value.item()

        except Exception:
            pass

    return value


# ============================================================
# PREPARE DATAFRAME
# ============================================================

def prepare_dataframe(df):
    """
    Prepare a DataFrame before database loading.
    """

    if df is None or df.empty:

        raise ValueError(
            "No records available to load."
        )

    prepared = df.copy()

    columns = [
        str(column)
        for column in prepared.columns
    ]

    if len(columns) != len(set(columns)):

        raise ValueError(
            "Duplicate column names found. "
            "Resolve them before loading."
        )

    prepared.columns = columns

    return prepared


# ============================================================
# SAVE EXTRACTED DATA
# ============================================================

def save_extracted_data(
    filename,
    file_type,
    dataframes
):
    """
    Save extracted structured data into staging tables.
    """

    valid_tables = []

    for index, df in enumerate(dataframes):

        if df is None or df.empty:
            continue

        valid_tables.append(
            (
                index,
                prepare_dataframe(df)
            )
        )

    if not valid_tables:

        raise ValueError(
            "No structured records found."
        )

    total_rows = sum(
        len(df)
        for _, df in valid_tables
    )

    total_columns = sum(
        len(df.columns)
        for _, df in valid_tables
    )

    engine = get_engine()

    with engine.begin() as connection:

        upload_id = connection.execute(
            text(
                """
                INSERT INTO staging.file_uploads
                (
                    filename,
                    file_type,
                    row_count,
                    column_count
                )
                VALUES
                (
                    :filename,
                    :file_type,
                    :row_count,
                    :column_count
                )
                RETURNING upload_id
                """
            ),
            {
                "filename": filename,
                "file_type": file_type,
                "row_count": total_rows,
                "column_count": total_columns
            }
        ).scalar_one()

        insert_query = text(
            """
            INSERT INTO staging.extracted_records
            (
                upload_id,
                source_table,
                row_number,
                record_data
            )
            VALUES
            (
                :upload_id,
                :source_table,
                :row_number,
                CAST(:record_data AS JSONB)
            )
            """
        )

        for table_index, df in valid_tables:

            records = df.to_dict(
                orient="records"
            )

            batch = []

            for row_number, record in enumerate(
                records,
                start=1
            ):

                cleaned_record = {
                    key: clean_value(value)
                    for key, value in record.items()
                }

                batch.append(
                    {
                        "upload_id": upload_id,
                        "source_table": table_index,
                        "row_number": row_number,
                        "record_data": json.dumps(
                            cleaned_record,
                            ensure_ascii=False,
                            allow_nan=False,
                            default=str
                        )
                    }
                )

                if len(batch) >= 500:

                    connection.execute(
                        insert_query,
                        batch
                    )

                    batch = []

            if batch:

                connection.execute(
                    insert_query,
                    batch
                )

    return upload_id


# ============================================================
# UPLOAD HISTORY
# ============================================================

def get_upload_history(limit=20):
    """
    Retrieve recent file uploads.
    """

    query = text(
        """
        SELECT
            upload_id,
            filename,
            file_type,
            row_count,
            column_count,
            uploaded_at
        FROM staging.file_uploads
        ORDER BY
            uploaded_at DESC,
            upload_id DESC
        LIMIT :limit
        """
    )

    with get_engine().connect() as connection:

        return pd.read_sql(
            query,
            connection,
            params={
                "limit": limit
            }
        )


# ============================================================
# GET DATABASE SCHEMAS
# ============================================================

def get_database_schemas():
    """
    Return user-accessible PostgreSQL schemas.
    """

    query = text(
        """
        SELECT
            schema_name
        FROM information_schema.schemata
        WHERE schema_name NOT IN
        (
            'information_schema',
            'pg_catalog'
        )
        ORDER BY schema_name
        """
    )

    with get_engine().connect() as connection:

        return pd.read_sql(
            query,
            connection
        )


# ============================================================
# GET DATABASE TABLES
# ============================================================

def get_database_tables(
    schema_name="public"
):
    """
    Return tables available in a PostgreSQL schema.
    """

    query = text(
        """
        SELECT
            table_name
        FROM information_schema.tables
        WHERE
            table_schema = :schema_name
            AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """
    )

    with get_engine().connect() as connection:

        return pd.read_sql(
            query,
            connection,
            params={
                "schema_name": schema_name
            }
        )


# ============================================================
# GET TARGET TABLE SCHEMA
# ============================================================

def get_target_table_schema(
    schema_name,
    table_name
):
    """
    Fetch column metadata from an actual PostgreSQL table.

    Returns:
        target_column
        target_dtype
        nullable
        default_value
    """

    query = text(
        """
        SELECT
            column_name,
            data_type,
            is_nullable,
            column_default,
            ordinal_position
        FROM information_schema.columns
        WHERE
            table_schema = :schema_name
            AND table_name = :table_name
        ORDER BY ordinal_position
        """
    )

    with get_engine().connect() as connection:

        result = pd.read_sql(
            query,
            connection,
            params={
                "schema_name": schema_name,
                "table_name": table_name
            }
        )

    if result.empty:

        raise ValueError(
            f"Table "
            f"'{schema_name}.{table_name}' "
            f"does not exist or has no columns."
        )

    result = result.rename(
        columns={
            "column_name": "target_column",
            "data_type": "target_dtype",
            "is_nullable": "nullable",
            "column_default": "default_value"
        }
    )

    return result[
        [
            "target_column",
            "target_dtype",
            "nullable",
            "default_value"
        ]
    ]


# ============================================================
# GET TABLE PREVIEW
# ============================================================

def get_table_preview(
    schema_name,
    table_name,
    limit=10
):
    """
    Preview records from a selected target table.
    """

    # Identifiers cannot safely be passed as normal
    # SQL parameters, so validate them before interpolation.

    identifier_pattern = r"^[A-Za-z_][A-Za-z0-9_]*$"

    import re

    if not re.match(
        identifier_pattern,
        schema_name
    ):
        raise ValueError(
            "Invalid schema name."
        )

    if not re.match(
        identifier_pattern,
        table_name
    ):
        raise ValueError(
            "Invalid table name."
        )

    query = text(
        f"""
        SELECT *
        FROM "{schema_name}"."{table_name}"
        LIMIT :limit
        """
    )

    with get_engine().connect() as connection:

        return pd.read_sql(
            query,
            connection,
            params={
                "limit": limit
            }
        )