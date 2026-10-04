import streamlit as st
import pandas as pd

from core.file_extractor import extract_file
from core.schema_extractor import get_schema, compare_schemas


def get_dataframe(uploaded_file):
    if uploaded_file is None:
        return None

    result = extract_file(uploaded_file)

    if result.get("dataframe") is not None:
        return result["dataframe"]

    tables = result.get("tables", [])

    if tables:
        return tables[0]

    return None


def render():
    st.header("🔄 Schema Drift Detector")
    st.caption("Compare two dataset versions and detect schema changes.")

    previous_file = st.file_uploader(
        "Upload Previous Dataset",
        type=["csv", "xlsx", "pdf", "docx"],
        key="previous_schema_file"
    )

    current_file = st.file_uploader(
        "Upload Current Dataset",
        type=["csv", "xlsx", "pdf", "docx"],
        key="current_schema_file"
    )

    if previous_file is None or current_file is None:
        st.info("Upload both previous and current datasets to detect schema drift.")
        return

    try:
        previous_df = get_dataframe(previous_file)
        current_df = get_dataframe(current_file)
    except Exception as e:
        st.error(f"File extraction failed: {e}")
        return

    if previous_df is None:
        st.error("No structured data found in the previous dataset.")
        return

    if current_df is None:
        st.error("No structured data found in the current dataset.")
        return

    st.divider()

    previous_schema = get_schema(previous_df)
    current_schema = get_schema(current_df)

    drift = compare_schemas(
        previous_schema,
        current_schema
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Previous Dataset")
        st.metric("Rows", len(previous_df))
        st.metric("Columns", len(previous_df.columns))

    with col2:
        st.subheader("Current Dataset")
        st.metric("Rows", len(current_df))
        st.metric("Columns", len(current_df.columns))

    st.divider()

    if drift["has_drift"]:
        st.error("⚠️ Schema Drift Detected")
    else:
        st.success("✅ No Schema Drift Detected")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Added Columns",
            len(drift["added_columns"])
        )

    with col2:
        st.metric(
            "Removed Columns",
            len(drift["removed_columns"])
        )

    with col3:
        st.metric(
            "Changed Data Types",
            len(drift["changed_types"])
        )

    st.divider()

    st.subheader("➕ Added Columns")

    if drift["added_columns"]:
        st.dataframe(
            pd.DataFrame(
                {"column_name": drift["added_columns"]}
            ),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.write("No columns added.")

    st.subheader("➖ Removed Columns")

    if drift["removed_columns"]:
        st.dataframe(
            pd.DataFrame(
                {"column_name": drift["removed_columns"]}
            ),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.write("No columns removed.")

    st.subheader("🔄 Changed Data Types")

    if drift["changed_types"]:
        st.dataframe(
            pd.DataFrame(drift["changed_types"]),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.write("No data type changes detected.")

    with st.expander("Previous Schema"):
        st.dataframe(
            previous_schema,
            use_container_width=True,
            hide_index=True
        )

    with st.expander("Current Schema"):
        st.dataframe(
            current_schema,
            use_container_width=True,
            hide_index=True
        )


if __name__ == "__main__":
    render()