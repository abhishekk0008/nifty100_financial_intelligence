import sqlite3
import pandas as pd

conn = sqlite3.connect("data/database/nifty100.db")

query = """
SELECT *
FROM financial_ratios
LIMIT 10;
"""

df = pd.read_sql(query, conn)

print(df)

conn.close()