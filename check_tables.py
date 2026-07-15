import sqlite3

conn = sqlite3.connect(r"data/database/nifty100.db")

cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")

print(cur.fetchall())

conn.close()