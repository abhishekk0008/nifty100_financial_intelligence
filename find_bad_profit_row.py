from src.database.db import Database
from src.etl.loader import ExcelLoader
import traceback

db = Database()

loader = ExcelLoader()
data = loader.load_all()

conn = db.connection

print("Companies in DB:", conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0])

profit = data["profit_loss"]

for i, row in profit.iterrows():

    try:
        row.to_frame().T.to_sql(
            "profit_loss",
            conn,
            if_exists="append",
            index=False,
        )

    except Exception as e:

        print("\n" + "=" * 80)
        print(f"FAILED AT ROW: {i}")
        print("=" * 80)

        print("\nROW DATA:")
        print(row.to_string())

        print("\nEXCEPTION TYPE:")
        print(type(e))

        print("\nEXCEPTION:")
        print(repr(e))

        print("\nCAUSE:")
        print(repr(e.__cause__))

        print("\nFULL TRACEBACK:")
        traceback.print_exc()

        break

db.close()