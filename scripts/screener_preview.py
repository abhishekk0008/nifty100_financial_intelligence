import sqlite3
import pandas as pd

conn = sqlite3.connect("data/database/nifty100.db")

query = """
SELECT
    company_id,
    year,
    return_on_equity_pct,
    debt_to_equity,
    interest_coverage,
    asset_turnover,
    earnings_per_share
FROM financial_ratios
WHERE
    return_on_equity_pct >= 15
    AND debt_to_equity <= 0.50
ORDER BY return_on_equity_pct DESC
LIMIT 20;
"""

df = pd.read_sql(query, conn)

print(df)

conn.close()