import sqlite3
import pandas as pd

conn = sqlite3.connect("data/database/nifty100.db")

query = """
SELECT
    f.company_id,
    s.broad_sector,
    f.year,
    f.return_on_equity_pct,
    f.debt_to_equity
FROM financial_ratios f
JOIN sectors s
ON f.company_id = s.company_id
WHERE
    s.broad_sector = 'Financials'
    AND f.debt_to_equity <= 1
ORDER BY f.return_on_equity_pct DESC
LIMIT 20;
"""

df = pd.read_sql(query, conn)

print(df)

conn.close()