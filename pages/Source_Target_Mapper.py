import streamlit as st
import pandas as pd

from core.source_target_mapper import (
    prepare_target_schema,
    generate_mappings,
    validate_mappings,
    apply_mappings,
)

from core.database import (
    get_database_schemas,
    get_database_tables,
    get_target_table_schema,
)


def get_schema_names(schemas):

    if schemas is None:
        return []

    if isinstance(schemas, pd.DataFrame):

        if schemas.empty:
            return []

        if "schema_name" in schemas.columns:
            return schemas["schema_name"].astype(str).tolist()

        return schemas.iloc[:, 0].astype(str).tolist()

    if isinstance(schemas, pd.Series):
        return schemas.astype(str).tolist()

    if isinstance(schemas, (list, tuple)):
        return [str(schema) for schema in schemas]

    return []


def get_table_names(tables):

    if tables is None:
        return []

    if isinstance(tables, pd.DataFrame):

        if tables.empty:
            return []

        if "table_name" in tables.columns:
            return tables["table_name"].astype(str).tolist()

        return tables.iloc[:, 0].astype(str).tolist()

    if isinstance(tables, pd.Series):
        return tables.astype(str).tolist()

    if isinstance(tables, (list, tuple)):
        return [str(table) for table in tables]

    return []


def render():

    st.header("🔄 Source-to-Target Mapper")
    st.caption("Map source columns to a target database schema.")

    extraction = st.session_state.get("extraction")

    if extraction is None:
        st.info(
            "Upload and extract a dataset from the File Upload module first."
        )
        return

    datasets = {}

    if extraction.get("dataframe") is not None:
        datasets["Main Dataset"] = extraction["dataframe"]

    for index, table in enumerate(
        extraction.get("tables", [])
    ):
        datasets[f"Document Table {index + 1}"] = table

    if not datasets:
        st.warning(
            "No structured dataset is available for mapping."
        )
        return

    source_name = st.selectbox(
        "Select Source Dataset",
        list(datasets.keys())
    )

    source_df = datasets[source_name]

    st.subheader("Source Dataset")

    st.dataframe(
        source_df.head(20),
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader("Target Database")

    try:

        schemas = get_database_schemas()
        schema_names = get_schema_names(schemas)

    except Exception as e:

        st.error(
            f"Could not load database schemas: {e}"
        )
        return

    if len(schema_names) == 0:

        st.warning(
            "No database schemas found."
        )
        return

    schema_name = st.selectbox(
        "Target Schema",
        schema_names
    )

    try:

        tables = get_database_tables(
            schema_name
        )

        table_names = get_table_names(tables)

    except Exception as e:

        st.error(
            f"Could not load database tables: {e}"
        )
        return

    if len(table_names) == 0:

        st.warning(
            "No tables found in the selected schema."
        )
        return

    table_name = st.selectbox(
        "Target Table",
        table_names
    )

    try:

        target_schema = get_target_table_schema(
            schema_name,
            table_name
        )

    except Exception as e:

        st.error(
            f"Could not load target table schema: {e}"
        )
        return

    if target_schema is None:

        st.warning(
            "Target table schema is empty."
        )
        return

    if not isinstance(
        target_schema,
        pd.DataFrame
    ):

        target_schema = pd.DataFrame(
            target_schema
        )

    if target_schema.empty:

        st.warning(
            "Target table schema is empty."
        )
        return

    st.subheader("Target Schema")

    st.dataframe(
        target_schema,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    if st.button(
        "Generate Mapping",
        type="primary"
    ):

        try:

            target = prepare_target_schema(
                target_schema
            )

            mappings = generate_mappings(
                source_df,
                target,
                minimum_confidence=0.35
            )

            st.session_state[
                "source_target_mappings"
            ] = mappings

            st.session_state[
                "mapping_validation"
            ] = None

            st.session_state[
                "mapped_dataframe"
            ] = None

            st.success(
                "Mapping suggestions generated."
            )

        except Exception as e:

            st.error(
                f"Mapping generation failed: {e}"
            )

    mappings = st.session_state.get(
        "source_target_mappings"
    )

    if mappings is None:
        return

    if isinstance(
        mappings,
        pd.DataFrame
    ):

        mapping_df = mappings.copy()

    else:

        mapping_df = pd.DataFrame(
            mappings
        )

    if mapping_df.empty:

        st.warning(
            "No mapping suggestions were generated."
        )
        return

    st.subheader("Mapping Suggestions")

    display_columns = [
        "source_column",
        "source_dtype",
        "target_column",
        "target_dtype",
        "similarity_score",
        "confidence",
        "approved",
    ]

    display_columns = [
        column
        for column in display_columns
        if column in mapping_df.columns
    ]

    if "approved" not in mapping_df.columns:
        mapping_df["approved"] = False

    edited_mapping = st.data_editor(
        mapping_df[display_columns],
        use_container_width=True,
        hide_index=True,
        column_config={
            "approved": st.column_config.CheckboxColumn(
                "Approved"
            ),
            "confidence": st.column_config.NumberColumn(
                "Confidence",
                format="%.2f"
            ),
            "similarity_score": st.column_config.NumberColumn(
                "Similarity",
                format="%.2f"
            ),
        },
        disabled=[
            column
            for column in display_columns
            if column not in [
                "target_column",
                "approved"
            ]
        ],
        key="mapping_editor"
    )

    st.divider()

    if st.button("Validate Mapping"):

        try:

            validation = validate_mappings(
                edited_mapping.to_dict(
                    orient="records"
                ),
                source_df.columns.tolist(),
                target_schema[
                    "target_column"
                ].tolist()
            )

            st.session_state[
                "mapping_validation"
            ] = validation

        except Exception as e:

            st.error(
                f"Validation failed: {e}"
            )

    validation = st.session_state.get(
        "mapping_validation"
    )

    if validation is not None:

        if validation.get("valid"):

            st.success(
                "✅ Mapping is valid."
            )

        else:

            st.error(
                "❌ Mapping has validation errors."
            )

        errors = validation.get(
            "errors",
            []
        )

        for error in errors:

            st.error(error)

    if "approved" not in edited_mapping.columns:
        edited_mapping["approved"] = False

    approved_mappings = edited_mapping[
        edited_mapping["approved"] == True
    ]

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Total Mappings",
            len(edited_mapping)
        )

    with col2:

        st.metric(
            "Approved Mappings",
            len(approved_mappings)
        )

    if approved_mappings.empty:

        st.info(
            "Approve at least one mapping to create the target dataset."
        )
        return

    if st.button(
        "Apply Approved Mappings",
        type="primary"
    ):

        try:

            result = apply_mappings(
                source_df,
                approved_mappings.to_dict(
                    orient="records"
                )
            )

            st.session_state[
                "mapped_dataframe"
            ] = result

            st.success(
                "Approved mappings applied successfully."
            )

        except Exception as e:

            st.error(
                f"Could not apply mappings: {e}"
            )

    mapped_df = st.session_state.get(
        "mapped_dataframe"
    )

    if mapped_df is not None:

        st.divider()

        st.subheader(
            "Target-Ready Dataset"
        )

        st.dataframe(
            mapped_df,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download Mapped Dataset",
            mapped_df.to_csv(
                index=False
            ),
            file_name=f"{table_name}_mapped.csv",
            mime="text/csv"
        )


if __name__ == "__main__":
    render()