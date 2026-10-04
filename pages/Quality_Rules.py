import streamlit as st
import pandas as pd

from agents.quality_agent import generate_rules
from core.rule_executor import execute_rules


def render():
    st.header("🛡️ Data Quality Rule Generator")
    st.caption("Generate, approve, and execute data quality rules.")

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
        st.warning("No structured dataset is available.")
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

    if st.button("Generate Quality Rules", type="primary"):

        try:
            rules = generate_rules(df)

            st.session_state["quality_rules"] = rules

            st.success(
                f"{len(rules)} quality rules generated."
            )

        except Exception as e:
            st.error(f"Rule generation failed: {e}")

    rules = st.session_state.get("quality_rules")

    if not rules:
        return

    st.subheader("Generated Quality Rules")

    rules_df = pd.DataFrame(rules)

    columns = [
        "id",
        "column",
        "type",
        "dimension",
        "severity",
        "params",
        "approved"
    ]

    columns = [
        column
        for column in columns
        if column in rules_df.columns
    ]

    edited_rules = st.data_editor(
        rules_df[columns],
        use_container_width=True,
        hide_index=True,
        column_config={
            "approved": st.column_config.CheckboxColumn(
                "Approved"
            ),
            "severity": st.column_config.SelectboxColumn(
                "Severity",
                options=[
                    "Low",
                    "Medium",
                    "High"
                ]
            )
        },
        disabled=[
            column
            for column in columns
            if column not in ["approved", "severity"]
        ],
        key="quality_rules_editor"
    )

    st.divider()

    approved_rules = edited_rules[
        edited_rules["approved"] == True
    ]

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Total Rules",
            len(edited_rules)
        )

    with col2:
        st.metric(
            "Approved Rules",
            len(approved_rules)
        )

    if approved_rules.empty:
        st.info("Approve at least one rule to run validation.")
        return

    if st.button("Run Data Quality Checks", type="primary"):

        try:

            approved_rule_list = approved_rules.to_dict(
                orient="records"
            )

            result = execute_rules(
                df,
                approved_rule_list
            )

            st.session_state["quality_result"] = result

            st.success("Data quality validation completed.")

        except Exception as e:
            st.error(f"Quality validation failed: {e}")

    result = st.session_state.get("quality_result")

    if result is None:
        return

    st.divider()

    st.subheader("Validation Report")

    total_failed = 0
    total_checked = 0

    if isinstance(result, dict):

        if "summary" in result:

            summary = result["summary"]

            total_checked = summary.get(
                "total_records",
                len(df)
            )

            total_failed = summary.get(
                "failed_records",
                0
            )

        results_df = result.get("results")

        if results_df is not None and isinstance(
            results_df,
            pd.DataFrame
        ):

            st.dataframe(
                results_df,
                use_container_width=True,
                hide_index=True
            )

        failed_df = result.get("failed_records")

        if failed_df is not None and isinstance(
            failed_df,
            pd.DataFrame
        ):

            st.subheader("Failed Records")

            if failed_df.empty:

                st.success("No records failed the approved rules.")

            else:

                st.dataframe(
                    failed_df,
                    use_container_width=True,
                    hide_index=True
                )

                st.download_button(
                    "Download Failed Records",
                    failed_df.to_csv(index=False),
                    file_name="failed_records.csv",
                    mime="text/csv"
                )

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "Records Checked",
                total_checked
            )

        with col2:
            st.metric(
                "Failed Records",
                total_failed
            )

    else:
        st.dataframe(
            result,
            use_container_width=True,
            hide_index=True
        )


if __name__ == "__main__":
    render()