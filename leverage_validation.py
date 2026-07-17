import pandas as pd

from src.etl.loader import ExcelLoader
from src.analytics.ratios import (
    debt_to_equity,
    high_leverage_flag,
    interest_coverage_ratio,
    icr_label,
    net_debt,
    asset_turnover,
)

loader = ExcelLoader()
data = loader.load_all()

pl = data["profit_loss"].copy()
bs = data["balance_sheet"].copy()
sectors = data["sectors"].copy()

# Merge Profit & Loss with Balance Sheet
df = pl.merge(
    bs,
    on=["company_id", "year"],
    how="inner"
)

# Merge Sector information
df = df.merge(
    sectors[["company_id", "broad_sector"]],
    on="company_id",
    how="left"
)

high_leverage = []
icr_risk = []

checked = 0
debt_free = 0

for _, row in df.iterrows():

    checked += 1

    is_financial = (
        str(row["broad_sector"]).strip() == "Financials"
    )

    # -------------------------
    # Debt to Equity
    # -------------------------
    de = debt_to_equity(
        row["borrowings"],
        row["equity_capital"],
        row["reserves"]
    )

    high_flag = False

    if de is not None:
        high_flag = high_leverage_flag(
            de,
            is_financial
        )

    # -------------------------
    # Interest Coverage Ratio
    # -------------------------
    icr = interest_coverage_ratio(
        row["operating_profit"],
        row["other_income"],
        row["interest"]
    )

    label = icr_label(icr)

    if label == "Debt Free":
        debt_free += 1

    # -------------------------
    # Net Debt & Asset Turnover
    # -------------------------
    nd = net_debt(
        row["borrowings"],
        row["investments"]
    )

    turnover = asset_turnover(
        row["sales"],
        row["total_assets"]
    )

    # -------------------------
    # High Leverage Report
    # -------------------------
    if high_flag:
        high_leverage.append({
            "company_id": row["company_id"],
            "year": row["year"],
            "de_ratio": de,
            "net_debt": nd,
            "asset_turnover": turnover
        })

    # -------------------------
    # ICR Risk Report
    # Skip Financial companies
    # -------------------------
    if (
        (not is_financial)
        and (icr is not None)
        and (icr < 1.5)
    ):
        icr_risk.append({
            "company_id": row["company_id"],
            "year": row["year"],
            "icr": icr,
            "label": label
        })

# Save Reports
pd.DataFrame(high_leverage).to_csv(
    "reports/leverage_report.csv",
    index=False
)

pd.DataFrame(icr_risk).to_csv(
    "reports/icr_risk_report.csv",
    index=False
)

print(f"Checked Companies : {checked}")
print(f"Debt Free         : {debt_free}")
print(f"High Leverage     : {len(high_leverage)}")
print(f"ICR Risk          : {len(icr_risk)}")

print("\nReports Saved:")
print("reports/leverage_report.csv")
print("reports/icr_risk_report.csv")