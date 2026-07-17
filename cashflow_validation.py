import pandas as pd

from src.etl.loader import ExcelLoader
from src.analytics.cashflow import (
    free_cash_flow,
    cfo_quality_score,
    cfo_quality_label,
    capex_intensity,
    capex_label,
    fcf_conversion,
    capital_allocation_pattern,
)

loader = ExcelLoader()
data = loader.load_all()

pl = data["profit_loss"].copy()

cf = data["cash_flow"].copy()

cf = cf.drop_duplicates(
    subset=["company_id", "year"],
      keep="last"
      )

pl = pl.drop_duplicates(
    subset=["company_id", "year"], 
    keep="last"
    )

df = pl.merge(
    cf,
    on=["company_id", "year"],
    how="inner"
)

results = []

for _, row in df.iterrows():

    fcf = free_cash_flow(
        row["operating_activity"],
        row["investing_activity"]
    )

    quality = cfo_quality_score(
        row["operating_activity"],
        row["net_profit"]
    )

    quality_label = cfo_quality_label(quality)

    capex = capex_intensity(
        row["investing_activity"],
        row["sales"]
    )

    capex_type = capex_label(capex)

    conversion = fcf_conversion(
        fcf,
        row["operating_profit"]
    )

    cfo_sign, cfi_sign, cff_sign, pattern = capital_allocation_pattern(
        row["operating_activity"],
        row["investing_activity"],
        row["financing_activity"]
    )

    results.append({
        "company_id": row["company_id"],
        "year": row["year"],
        "free_cash_flow": fcf,
        "cfo_quality": quality,
        "cfo_quality_label": quality_label,
        "capex_intensity": capex,
        "capex_label": capex_type,
        "fcf_conversion": conversion,
        "cfo_sign": cfo_sign,
        "cfi_sign": cfi_sign,
        "cff_sign": cff_sign,
        "pattern_label": pattern,
    })

report = pd.DataFrame(results)

report.to_csv(
    "reports/capital_allocation.csv",
    index=False
)

print(f"Companies Processed : {len(report)}")
print("\nReport Saved:")
print("reports/capital_allocation.csv")