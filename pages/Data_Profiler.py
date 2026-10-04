import streamlit as st
import pandas as pd

from agents.profiler_agent import profile_dataset


def render():
    st.header("📊 Data Profiler")
    st.caption("Understand dataset structure, missing values, duplicates, and statistics.")

    extraction = st.session_state.get("extraction")

    if extraction is None:
        st.info("Upload and extract a dataset from the File Upload module first.")
        return

    datasets = {}

    if extraction.get("dataframe") is not None:
        datasets["Main Dataset"] = extraction["dataframe"]

    for index, table in enumerate(extraction.get("tables", [])):
        datasets[f"Document Table {index + 1}"] = table

    if not datasets:
        st.warning("No structured dataset is available for profiling.")
        return

    dataset_name = st.selectbox(
        "Select Dataset",
        list(datasets.keys())
    )

    df = datasets[dataset_name]

    st.subheader("Dataset Preview")

    st.dataframe(
        df.head(20),
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    if st.button("Generate Profiling Report", type="primary"):

        try:
            report = profile_dataset(df)
            st.session_state["profile_report"] = report
            st.success("Profiling report generated.")

        except Exception as e:
            st.error(f"Profiling failed: {e}")

    report = st.session_state.get("profile_report")

    if report is None:
        return

    st.divider()

    st.subheader("Dataset Summary")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Rows",
            report["total_rows"]
        )

    with col2:
        st.metric(
            "Total Columns",
            report["total_columns"]
        )

    with col3:
        st.metric(
            "Missing Cells",
            report["missing_cells"]
        )

    with col4:
        st.metric(
            "Duplicate Rows",
            report["duplicate_rows"]
        )

    st.divider()

    tab1, tab2, tab3 = st.tabs(
        [
            "Column Profile",
            "Missing Values",
            "Numeric Statistics"
        ]
    )

    with tab1:

        st.subheader("Column Profile")

        column_profile = report["column_profile"]

        st.dataframe(
            column_profile,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download Column Profile",
            column_profile.to_csv(index=False),
            file_name="column_profile.csv",
            mime="text/csv"
        )

    with tab2:

        st.subheader("Missing Values")

        missing = report["missing_by_column"]

        missing_df = pd.DataFrame({
            "column": missing.index.astype(str),
            "missing_values": missing.values
        })

        missing_df["missing_percentage"] = (
            missing_df["missing_values"]
            / report["total_rows"]
            * 100
        ).round(2)

        missing_df = missing_df.sort_values(
            "missing_values",
            ascending=False
        )

        st.dataframe(
            missing_df,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download Missing Value Report",
            missing_df.to_csv(index=False),
            file_name="missing_values.csv",
            mime="text/csv"
        )

    with tab3:

        st.subheader("Numeric Statistics")

        numeric_stats = report["numeric_stats"]

        if numeric_stats.empty:
            st.info("No numeric columns found.")
        else:
            st.dataframe(
                numeric_stats,
                use_container_width=True
            )

            st.download_button(
                "Download Numeric Statistics",
                numeric_stats.to_csv(),
                file_name="numeric_statistics.csv",
                mime="text/csv"
            )


if __name__ == "__main__":
    render()