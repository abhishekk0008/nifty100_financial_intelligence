import sqlite3
import pandas as pd
from pathlib import Path

conn = sqlite3.connect("data/database/nifty100.db")

queries = {
    "profit_loss": """
        SELECT company_id, COUNT(DISTINCT year) AS year_count
        FROM profit_loss
        GROUP BY company_id
        HAVING year_count < 5
    """,
    "balance_sheet": """
        SELECT company_id, COUNT(DISTINCT year) AS year_count
        FROM balance_sheet
        GROUP BY company_id
        HAVING year_count < 5
    """,
    "cash_flow": """
        SELECT company_id, COUNT(DISTINCT year) AS year_count
        FROM cash_flow
        GROUP BY company_id
        HAVING year_count < 5
    """
}

failures = []

for table, query in queries.items():
    df = pd.read_sql(query, conn)
    if not df.empty:
        df["table"] = table
        df["severity"] = "MEDIUM"
        failures.append(df)

Path("reports").mkdir(exist_ok=True)

if failures:
    result = pd.concat(failures, ignore_index=True)
else:
    result = pd.DataFrame(
        columns=["company_id", "year_count", "table", "severity"]
    )

result.to_csv("reports/validation_failures.csv", index=False)

print(result)
print("\nvalidation_failures.csv generated.")

conn.close()