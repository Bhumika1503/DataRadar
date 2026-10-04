import streamlit as st

from core.file_extractor import extract_file
from core.database import (
    test_connection,
    save_extracted_data,
    get_upload_history,
)


st.set_page_config(
    page_title="Data Radar",
    page_icon="📡",
    layout="wide",
)


if "extraction" not in st.session_state:
    st.session_state["extraction"] = None

if "file_id" not in st.session_state:
    st.session_state["file_id"] = None


st.title("📡 DATA RADAR")
st.caption("AI-Powered Data Engineering Platform")


st.sidebar.title("Data Radar")

page = st.sidebar.radio(
    "Modules",
    [
        "File Upload",
        "Source-to-Target Mapper",
        "Data Profiler",
        "Data Quality Rules",
        "Schema Drift Detector",
    ],
)


st.sidebar.divider()

if test_connection():
    st.sidebar.success("PostgreSQL Connected")
else:
    st.sidebar.error("PostgreSQL Disconnected")


if page == "File Upload":

    st.header("📄 Unstructured File → Database")

    uploaded_file = st.file_uploader(
        "Upload your file",
        type=["csv", "xlsx", "pdf", "docx", "txt"],
    )

    if uploaded_file is not None:

        if st.button("Extract File", type="primary"):

            try:
                with st.spinner("Extracting file..."):

                    extraction = extract_file(uploaded_file)

                    st.session_state["extraction"] = extraction
                    st.session_state["file_id"] = None

                st.success("File extracted successfully.")

            except Exception as e:
                st.error(f"Extraction failed: {e}")

        extraction = st.session_state.get("extraction")

        if extraction is not None:

            st.divider()

            dataframe = extraction.get("dataframe")
            tables = extraction.get("tables", [])
            text = extraction.get("text", "")

            if dataframe is not None:

                st.subheader("Extracted Dataset")

                st.dataframe(
                    dataframe,
                    use_container_width=True,
                    hide_index=True,
                )

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Rows", len(dataframe))

                with col2:
                    st.metric("Columns", len(dataframe.columns))

                with col3:
                    st.metric(
                        "Missing Values",
                        int(dataframe.isna().sum().sum()),
                    )

                st.download_button(
                    "Download Extracted CSV",
                    dataframe.to_csv(index=False),
                    file_name="extracted_data.csv",
                    mime="text/csv",
                )

                if st.button("Save to PostgreSQL"):

                    try:

                        upload_id = save_extracted_data(
                            dataframe=dataframe,
                            filename=uploaded_file.name,
                            file_type=extraction.get("file_type", ""),
                        )

                        st.session_state["file_id"] = upload_id

                        st.success(
                            f"Data saved to PostgreSQL. Upload ID: {upload_id}"
                        )

                    except Exception as e:
                        st.error(f"Database save failed: {e}")

            if tables:

                st.subheader("Extracted Tables")

                for index, table in enumerate(tables):

                    st.write(f"Table {index + 1}")

                    st.dataframe(
                        table,
                        use_container_width=True,
                        hide_index=True,
                    )

                    st.download_button(
                        f"Download Table {index + 1}",
                        table.to_csv(index=False),
                        file_name=f"table_{index + 1}.csv",
                        mime="text/csv",
                        key=f"download_table_{index}",
                    )

            if text:

                st.subheader("Extracted Text")

                st.text_area(
                    "Text",
                    text,
                    height=300,
                )

            if not dataframe is not None and not tables and not text:

                st.warning("No structured data or text was extracted.")

    st.divider()

    st.subheader("Recent Uploads")

    try:

        history = get_upload_history()

        if history is not None and not history.empty:

            st.dataframe(
                history,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info("No uploads found.")

    except Exception as e:

        st.warning(f"Could not load upload history: {e}")


elif page == "Source-to-Target Mapper":

    from pages.Source_Target_Mapper import render

    render()


elif page == "Data Profiler":

    from pages.Data_Profiler import render

    render()


elif page == "Data Quality Rules":

    from pages.Quality_Rules import render

    render()


elif page == "Schema Drift Detector":

    from pages.Schema_Drift import render

    render()


st.sidebar.divider()

st.sidebar.caption(
    "DATA RADAR | Data Engineering Platform"
)