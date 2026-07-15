from src.database.db import Database
from src.etl.loader import ExcelLoader
import traceback

db = Database()

loader = ExcelLoader()
data = loader.load_all()

print("Companies already in DB:",
      db.connection.execute("SELECT COUNT(*) FROM companies").fetchone()[0])

try:
    db.insert_dataframe("profit_loss", data["profit_loss"])
    print("Profit Loss inserted successfully.")
except Exception:
    print("\n===== FULL ERROR =====")
    traceback.print_exc()

db.close()