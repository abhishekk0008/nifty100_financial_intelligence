import pandas as pd

from src.etl.loader import ExcelLoader
from src.analytics.cagr import cagr

loader = ExcelLoader()
data = loader.load_all()

pl = data["profit_loss"].copy()

results = []

for company in pl["company_id"].unique():

    df = (
        pl[pl["company_id"] == company]
        .copy()
        .sort_values("year")
    )

    # Remove TTM
    df = df[df["year"] != "TTM"]

    if len(df) < 2:
        continue

    latest = df.iloc[-1]

    record = {
        "company_id": company
    }

    for years in [3, 5, 10]:

        if len(df) < years + 1:

            record[f"revenue_cagr_{years}y"] = None
            record[f"revenue_cagr_{years}y_flag"] = "INSUFFICIENT"

            record[f"pat_cagr_{years}y"] = None
            record[f"pat_cagr_{years}y_flag"] = "INSUFFICIENT"

            record[f"eps_cagr_{years}y"] = None
            record[f"eps_cagr_{years}y_flag"] = "INSUFFICIENT"

            continue

        old = df.iloc[-(years + 1)]

        # Revenue CAGR
        value, flag = cagr(
            old["sales"],
            latest["sales"],
            years,
        )

        record[f"revenue_cagr_{years}y"] = value
        record[f"revenue_cagr_{years}y_flag"] = flag

        # PAT CAGR
        value, flag = cagr(
            old["net_profit"],
            latest["net_profit"],
            years,
        )

        record[f"pat_cagr_{years}y"] = value
        record[f"pat_cagr_{years}y_flag"] = flag

        # EPS CAGR
        value, flag = cagr(
            old["eps"],
            latest["eps"],
            years,
        )

        record[f"eps_cagr_{years}y"] = value
        record[f"eps_cagr_{years}y_flag"] = flag

    results.append(record)

out = pd.DataFrame(results)

out.to_csv(
    "reports/cagr_report.csv",
    index=False
)

print(f"Companies Processed : {len(out)}")
print("\nReport Saved:")
print("reports/cagr_report.csv")