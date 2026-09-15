"""Natural Language → SQL — ask a question, get DuckDB SQL, run it safely."""

import re

import pandas as pd
import streamlit as st
import duckdb

from tabular.context import DatasetContext
from services.groq_service import get_groq_llm, extract_content
from config import AI_PRIVACY_NOTICE

DANGEROUS_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "COPY", "ATTACH", "DETACH", "GRANT", "REVOKE",
]

# Word-boundary match instead of plain substring: a column named
# `date_created` (-> "DATE_CREATED" uppercased) must NOT trip the
# "CREATE" keyword check the way a bare `in` substring test would.
_KEYWORD_PATTERNS = {kw: re.compile(rf"\b{kw}\b") for kw in DANGEROUS_KEYWORDS}


def render(df: pd.DataFrame, ctx: DatasetContext, tabular_file=None) -> None:
    st.markdown("## Natural Language → SQL")
    st.caption(
        "Ask questions about your dataset using normal language. "
        "The AI converts your question into DuckDB SQL and executes it."
    )
    st.caption(AI_PRIVACY_NOTICE)

    schema_lines = [f'"{column}" : {df[column].dtype}' for column in df.columns]
    dataset_schema = "\n".join(schema_lines)

    with st.expander("Example Questions"):
        st.markdown(
            """
            **Examples:**

            - How many rows are in the dataset?
            - What is the average salary?
            - What is the average salary by department?
            - Show the top 10 employees by salary.
            - Which department has the highest average salary?
            - What are the most common cities?
            - Show the total sales by category.
            - What is the minimum and maximum price?
            """
        )

    user_sql_question = st.text_area(
        "Ask a question about your dataset",
        placeholder="Example: What is the average salary for each department?",
        height=100,
        key="duckdb_nl_question",
    )

    if not st.button("Generate SQL & Run", key="duckdb_generate_sql", type="primary"):
        return

    if not user_sql_question.strip():
        st.warning("Please enter a question first.")
        return

    try:
        llm = get_groq_llm(temperature=0)
        if llm is None:
            return

        sql_prompt = _build_sql_prompt(dataset_schema, user_sql_question)

        with st.spinner("Generating SQL..."):
            response = llm.invoke(sql_prompt)

        generated_sql = extract_content(response).strip()
        generated_sql = (
            generated_sql.replace("```sql", "").replace("```SQL", "").replace("```", "").strip()
        )

        if not _validate_sql(generated_sql):
            return

        st.markdown("### Generated SQL")
        st.code(generated_sql, language="sql")

        st.markdown("### Query Result")

        connection = duckdb.connect(database=":memory:")
        try:
            connection.register("data", df)
            result_df = connection.execute(generated_sql).fetchdf()
        finally:
            connection.close()

        if result_df.empty:
            st.info("The query executed successfully but returned no rows.")
        else:
            st.success(f"Query executed successfully — {len(result_df):,} row(s) returned.")
            st.dataframe(result_df, use_container_width=True, hide_index=True)

            csv_result = result_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download Query Result",
                data=csv_result,
                file_name="duckdb_query_result.csv",
                mime="text/csv",
                key="download_duckdb_result",
            )

    except Exception as e:
        st.error(f"Unable to generate or execute SQL: {e}")


def _validate_sql(generated_sql: str) -> bool:
    sql_upper = generated_sql.upper().strip().rstrip(";").strip()

    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        st.error("Query rejected. Only SELECT queries are allowed.")
        return False

    for keyword, pattern in _KEYWORD_PATTERNS.items():
        if pattern.search(sql_upper):
            st.error(f"Query rejected because `{keyword}` is not allowed.")
            return False

    return True


def _build_sql_prompt(dataset_schema: str, user_sql_question: str) -> str:
    return f"""
You are an expert DuckDB SQL analyst.

Your task is to convert the user's natural-language
question into ONE valid DuckDB SQL query.

DATABASE TABLE:
The uploaded pandas DataFrame is available as:

data

DATASET SCHEMA:

{dataset_schema}

USER QUESTION:

{user_sql_question}

STRICT RULES:

1. Generate exactly ONE SQL query.
2. The query must be SELECT-only.
3. WITH queries are allowed only when the final statement is SELECT.
4. The table name is exactly "data".
5. Use only columns present in the provided schema.
6. Preserve column names correctly.
7. Do not invent columns.
8. Do not use INSERT.
9. Do not use UPDATE.
10. Do not use DELETE.
11. Do not use DROP.
12. Do not use ALTER.
13. Do not use CREATE.
14. Do not use TRUNCATE.
15. Do not use COPY.
16. Do not use ATTACH.
17. Do not use DETACH.
18. Do not use GRANT.
19. Do not use REVOKE.
20. Return ONLY SQL.
21. Do not return markdown.
22. Do not return ```sql.
23. Do not explain the query.

Return only the SQL query.
"""
