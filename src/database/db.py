import sqlite3
from pathlib import Path


class Database:

    def __init__(
        self,
        db_path="data/database/nifty100.db",
        schema_path="src/database/schema.sql",
    ):
        self.db_path = Path(db_path)
        self.schema_path = Path(schema_path)

        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.connection = sqlite3.connect(self.db_path)
        self.connection.execute("PRAGMA foreign_keys = ON;")

    def initialize(self):

        with open(self.schema_path, "r", encoding="utf-8") as f:
            schema = f.read()

        self.connection.executescript(schema)
        self.connection.commit()

    def insert_dataframe(self, table_name, dataframe):

        print(f"\n>>> INSERTING {table_name}")

        dataframe.to_sql(
            table_name,
            self.connection,
            if_exists="append",
            index=False,
        )

        self.connection.commit()

        count = self.connection.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        ).fetchone()[0]

        print(f">>> {table_name} rows after insert = {count}")

    def close(self):
        self.connection.close()