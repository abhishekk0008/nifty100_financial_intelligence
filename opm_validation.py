import pandas as pd

from src.etl.loader import ExcelLoader
from src.analytics.ratios import operating_profit_margin


loader = ExcelLoader()
data = loader.load_all()

pl = data["profit_loss"].copy()
sectors = data["sectors"].copy()

# Financial companies (Banks, NBFCs, Insurance etc.)
financial_companies = set(
    sectors.loc[
        sectors["broad_sector"] == "Financials",
        "company_id"
    ].astype(str).str.strip()
)

failures = []

checked = 0
skipped = 0

for _, row in pl.iterrows():

    company_id = str(row["company_id"]).strip()

    # Skip Financial companies
    if company_id in financial_companies:
        skipped += 1
        continue

    sales = row["sales"]
    operating_profit = row["operating_profit"]
    reported = row["opm_percentage"]

    # Skip missing values
    if pd.isna(sales) or pd.isna(operating_profit) or pd.isna(reported):
        skipped += 1
        continue

    calc = operating_profit_margin(
        operating_profit,
        sales
    )

    if calc is None:
        skipped += 1
        continue

    checked += 1

    if abs(calc - reported) > 2:

        failures.append({
            "company_id": company_id,
            "year": row["year"],
            "calculated_opm": calc,
            "reported_opm": reported,
            "difference": round(abs(calc - reported), 2)
        })

df = pd.DataFrame(failures)

df.to_csv(
    "reports/opm_validation_failures.csv",
    index=False
)

print(f"Checked rows : {checked}")
print(f"Skipped rows : {skipped}")
print(f"Failures     : {len(failures)}")

print("\nReport saved:")
print("reports/opm_validation_failures.csv")

if not df.empty:
    print("\nTop failing companies:")
    print(
        df.groupby("company_id")
          .size()
          .sort_values(ascending=False)
          .head(10)
    )
else:
    print("\nNo validation failures found.")