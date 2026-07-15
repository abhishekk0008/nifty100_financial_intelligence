import sqlite3

conn = sqlite3.connect(r"data/database/nifty100.db")
cur = conn.cursor()

tables = [
    "companies",
    "profit_loss",
    "balance_sheet",
    "cash_flow",
    "analysis",
    "documents",
    "pros_cons",
    "financial_ratios",
    "market_cap",
    "peer_groups",
    "sectors",
    "stock_prices",
]

for table in tables:
    count = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"{table:20} {count}")

conn.close()