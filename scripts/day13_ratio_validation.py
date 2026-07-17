from src.etl.loader import ExcelLoader
from src.analytics.ratios import (
    return_on_equity,
    return_on_capital_employed,
)

loader = ExcelLoader()
data = loader.load_all()

companies = data["companies"]
balance = data["balance_sheet"]
profit = data["profit_loss"]
sectors = data["sectors"]

merged = (
    profit.merge(
        balance,
        on=["company_id", "year"],
        suffixes=("_pl", "_bs")
    )
    .merge(
        companies[["id", "roe_percentage", "roce_percentage"]],
        left_on="company_id",
        right_on="id",
        how="left"
    )
    .merge(
        sectors[["company_id", "broad_sector"]],
        on="company_id",
        how="left"
    )
)

print("Rows:", len(merged))
print(merged.head())

# merged dataframe ko df naam de do
df = merged.copy()

df["calculated_roe"] = df.apply(
    lambda x: return_on_equity(
        x["net_profit"],
        x["equity_capital"],
        x["reserves"],
    ),
    axis=1,
)

df["calculated_roce"] = df.apply(
    lambda x: return_on_capital_employed(
        x["operating_profit"] + x["other_income"],
        x["equity_capital"],
        x["reserves"],
        x["borrowings"],
    ),
    axis=1,
)

print(
    df[
        [
            "company_id",
            "year",
            "calculated_roe",
            "roe_percentage",
            "calculated_roce",
            "roce_percentage",
        ]
    ].head(20)
)

df["roe_diff"] = (df["calculated_roe"] - df["roe_percentage"]).abs()
df["roce_diff"] = (df["calculated_roce"] - df["roce_percentage"]).abs()

print("\n===== ROE Validation =====")
print(df["roe_diff"].describe())

print("\n===== ROCE Validation =====")
print(df["roce_diff"].describe())

validated = (
    (df["roe_diff"] <= 5) &
    (df["roce_diff"] <= 5)
).sum()

print(f"\nRows within ±5% tolerance: {validated}/{len(df)}")

from pathlib import Path

Path("reports").mkdir(exist_ok=True)

df.to_csv(
    "reports/day13_ratio_validation.csv",
    index=False
)

print("\nReport saved: reports/day13_ratio_validation.csv")