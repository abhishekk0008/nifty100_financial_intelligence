from src.database.db import Database
from src.etl.loader import ExcelLoader


def main():

    # Create database
    db = Database()
    db.initialize()

    # Load Excel files
    loader = ExcelLoader()
    datasets = loader.load_all()

    # Insert into tables
    table_mapping = {
        "companies": "companies",
        "profit_loss": "profit_loss",
        "balance_sheet": "balance_sheet",
        "cash_flow": "cash_flow",
        "analysis": "analysis",
        "documents": "documents",
        "pros_cons": "pros_cons",
    }

    for dataset_name, table_name in table_mapping.items():

        if dataset_name not in datasets:
            continue

        df = datasets[dataset_name]

        print(f"Inserting {len(df)} rows into {table_name}")

        db.insert_dataframe(table_name, df)

    db.close()

    print("\nDatabase loading completed successfully!")


if __name__ == "__main__":
    main()