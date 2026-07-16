import sqlite3

conn = sqlite3.connect("data/database/nifty100.db")

with open("notebooks/exploratory_queries.sql", "r", encoding="utf-8") as f:
    sql = f.read()

queries = [q.strip() for q in sql.split(";") if q.strip()]

for i, query in enumerate(queries, 1):
    print(f"\n========== Query {i} ==========")
    try:
        rows = conn.execute(query).fetchmany(5)
        for row in rows:
            print(row)
    except Exception as e:
        print("Error:", e)

conn.close()

print("\nAll queries executed.")