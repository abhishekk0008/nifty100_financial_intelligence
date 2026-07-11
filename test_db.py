from src.database.db import Database

db = Database()
db.initialize()

print("Database created successfully!")

db.close()