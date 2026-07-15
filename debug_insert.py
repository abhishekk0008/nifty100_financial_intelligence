from src.database.db import Database
from src.etl.loader import ExcelLoader

db = Database()
db.initialize()

loader = ExcelLoader()
companies = loader.load_all()["companies"]

print("Rows in dataframe:", len(companies))

try:
    db.insert_dataframe("companies", companies)
    print("INSERT SUCCESS")
except Exception as e:
    print("INSERT FAILED")
    print(type(e))
    print(e)

print("Rows in DB:", db.connection.execute("SELECT COUNT(*) FROM companies").fetchone()[0])

db.close()