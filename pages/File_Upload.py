
import streamlit as st

from core.file_extractor import (
    extract_file,
    get_excel_sheets,
    SUPPORTED_TYPES
)

from core.database import (
    initialize_database,
    ingest_dataframe,
    get_ingestion_jobs
)


st.set_page_config(
    page_title="DataRadar | Ingestion",
    page_icon="📡",
    layout="wide"
)

st.title("📂 File Ingestion")
st.caption(
    "Upload, extract, preview and stage your data."
)

uploaded_file = st.file_uploader(
    "Choose a file",
    type=SUPPORTED_TYPES
)

if uploaded_file is not None:

    filename = uploaded_file.name
    file_bytes = uploaded_file.getvalue()
    extension = filename.rsplit(
        ".", 1
    )[-1].lower()

    st.subheader("Extraction Settings")

    sheet_name = None
    delimiter = ","
    encoding = "utf-8"
    header = True

    if extension == "xlsx":
        sheets = get_excel_sheets(file_bytes)

        sheet_name = st.selectbox(
            "Select Excel sheet",
            sheets
        )

    if extension == "csv":
        delimiter = st.selectbox(
            "CSV delimiter",
            [",", ";", "\t", "|"]
        )

    if extension in ["csv", "txt"]:
        encoding = st.selectbox(
            "File encoding",
            ["utf-8", "utf-8-sig", "latin-1"]
        )

    if extension in ["csv", "xlsx"]:
        header = st.checkbox(
            "First row contains column names",
            value=True
        )

    try:
        df = extract_file(
            file_bytes=file_bytes,
            filename=filename,
            sheet_name=sheet_name,
            delimiter=delimiter,
            encoding=encoding,
            header=header
        )

        st.success("File extracted successfully!")

        col1, col2, col3 = st.columns(3)

        col1.metric("Rows", len(df))
        col2.metric("Columns", len(df.columns))
        col3.metric(
            "Missing Values",
            int(df.isna().sum().sum())
        )

        st.subheader("Data Preview")

        st.dataframe(
            df.head(100),
            use_container_width=True
        )

        st.subheader("Detected Columns")

        st.dataframe(
            {
                "Column": df.columns,
                "Data Type": [
                    str(dtype)
                    for dtype in df.dtypes
                ]
            },
            use_container_width=True
        )

        if st.button(
            "Ingest into PostgreSQL",
            type="primary"
        ):
            with st.spinner("Ingesting data..."):
                initialize_database()

                job_id = ingest_dataframe(
                    df=df,
                    filename=filename
                )

            st.success(
                "Data successfully ingested!"
            )

            st.code(
                job_id,
                language=None
            )

    except Exception as error:
        st.error(
            f"Processing failed: {error}"
        )


st.divider()

st.subheader("Recent Ingestion Jobs")

if st.button("Load ingestion history"):
    try:
        history = get_ingestion_jobs()

        if history.empty:
            st.info("No ingestion jobs found.")
        else:
            st.dataframe(
                history,
                use_container_width=True
            )

    except Exception as error:
        st.error(
            f"Could not load history: {error}"
        )
        
def get_excel_sheets(uploaded_file):
    """Return all worksheet names from an Excel file."""

    import io
    import pandas as pd

    file_bytes = uploaded_file.getvalue()

    excel = pd.ExcelFile(
        io.BytesIO(file_bytes)
    )

    try:
        return excel.sheet_names
    finally:
        excel.close()