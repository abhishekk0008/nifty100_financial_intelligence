from pathlib import Path
import pandas as pd

from src.database.db import Database
from src.etl.loader import ExcelLoader


def main():

    db_file = Path("data/database/nifty100.db")

    if db_file.exists():
        print("\nCleaning existing database...")
        db_file.unlink()
        print("Old data removed successfully.\n")

    db = Database()
    db.initialize()

    loader = ExcelLoader()
    data = loader.load_all()

    valid_ids = set(data["companies"]["id"].astype(str).str.strip())

    tables = {
        "companies": data["companies"],

        "profit_loss":
            data["profit_loss"][
                data["profit_loss"]["company_id"].astype(str).str.strip().isin(valid_ids)
            ],

        "balance_sheet":
            data["balance_sheet"][
                data["balance_sheet"]["company_id"].astype(str).str.strip().isin(valid_ids)
            ],

        "cash_flow":
            data["cash_flow"][
                data["cash_flow"]["company_id"].astype(str).str.strip().isin(valid_ids)
            ],

        "analysis":
            data["analysis"][
                data["analysis"]["company_id"].astype(str).str.strip().isin(valid_ids)
            ],

        "documents":
            data["documents"][
                data["documents"]["company_id"].astype(str).str.strip().isin(valid_ids)
            ],

        "pros_cons":
            data["pros_cons"][
                data["pros_cons"]["company_id"].astype(str).str.strip().isin(valid_ids)
            ],

        "financial_ratios":
            data["financial_ratios"][
                data["financial_ratios"]["company_id"].astype(str).str.strip().isin(valid_ids)
            ],

        "market_cap":
            data["market_cap"][
                data["market_cap"]["company_id"].astype(str).str.strip().isin(valid_ids)
            ],

        "peer_groups":
            data["peer_groups"][
                data["peer_groups"]["company_id"].astype(str).str.strip().isin(valid_ids)
            ],

        "sectors":
            data["sectors"][
                data["sectors"]["company_id"].astype(str).str.strip().isin(valid_ids)
            ],

        "stock_prices":
            data["stock_prices"][
                data["stock_prices"]["company_id"].astype(str).str.strip().isin(valid_ids)
            ],
    }

    audit = []

    print("\n==============================")
    print("Loading into SQLite")
    print("==============================")

    for table_name, df in tables.items():

        print(f"\nLoading {table_name}...")
        print("Rows:", len(df))

        db.insert_dataframe(table_name, df)

        audit.append({
            "table_name": table_name,
            "rows_loaded": len(df),
            "status": "SUCCESS"
        })

        print(f"{table_name} rows after insert = {len(df)}")

    Path("reports").mkdir(exist_ok=True)

    audit_df = pd.DataFrame(audit)
    audit_df.to_csv("reports/load_audit.csv", index=False)

    print("\n===================================")
    print("DATABASE LOADED SUCCESSFULLY")
    print("===================================")
    print("load_audit.csv created successfully.")

    db.close()


if __name__ == "__main__":
    main()