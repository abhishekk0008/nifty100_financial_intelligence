import sqlite3
import pandas as pd

conn = sqlite3.connect("data/database/nifty100.db")

screeners = {
    "High ROE": """
    SELECT company_id, year, return_on_equity_pct
    FROM financial_ratios
    WHERE return_on_equity_pct >= 20
    ORDER BY return_on_equity_pct DESC
    LIMIT 10;
    """,

    "Low Debt": """
    SELECT company_id, year, debt_to_equity
    FROM financial_ratios
    WHERE debt_to_equity <= 0.30
    ORDER BY debt_to_equity ASC
    LIMIT 10;
    """,

    "High Asset Turnover": """
    SELECT company_id, year, asset_turnover
    FROM financial_ratios
    WHERE asset_turnover >= 1
    ORDER BY asset_turnover DESC
    LIMIT 10;
    """
}

for name, query in screeners.items():
    print(f"\n===== {name} =====")
    df = pd.read_sql(query, conn)
    print(df)

conn.close()