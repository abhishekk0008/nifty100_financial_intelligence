from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.analytics.cagr import cagr


P_AND_L_FILE = ROOT / "data" / "raw" / "profitandloss.xlsx"
PARSED_FILE = ROOT / "output" / "analysis_parsed.csv"

OUTPUT_FILE = ROOT / "output" / "cagr_validation.csv"


def load_profit_loss():
    df = pd.read_excel(P_AND_L_FILE, header=1)

    df["year"] = df["year"].astype(str)

    # Keep only actual yearly records.
    df = df[df["year"].str.match(r"^(Mar|Dec)\s+\d{4}$", na=False)].copy()

    df["year_num"] = (
        df["year"]
        .str.extract(r"(\d{4})")[0]
        .astype(int)
    )

    return df


def calculate_cagr(df, company_id, metric, years):
    company_df = (
        df[df["company_id"] == company_id]
        .sort_values("year_num")
    )

    if company_df.empty:
        return None, "INSUFFICIENT"

    latest = company_df.iloc[-1]
    target_year = latest["year_num"] - years

    previous = company_df[
        company_df["year_num"] <= target_year
    ]

    if previous.empty:
        return None, "INSUFFICIENT"

    start = previous.iloc[-1]
    end = latest

    start_value = start[metric]
    end_value = end[metric]

    if pd.isna(start_value) or pd.isna(end_value):
        return None, "INSUFFICIENT"

    return cagr(
        float(start_value),
        float(end_value),
        years,
    )


def main():
    print("=" * 60)
    print("CAGR CROSS-VALIDATION")
    print("=" * 60)

    financials = load_profit_loss()
    parsed = pd.read_csv(PARSED_FILE)

    print(f"Financial rows: {len(financials)}")
    print(f"Parsed rows: {len(parsed)}")

    metric_mapping = {
        "compounded_sales_growth": "sales",
        "compounded_profit_growth": "net_profit",
    }

    results = []

    for _, row in parsed.iterrows():

        metric_type = row["metric_type"]

        if metric_type not in metric_mapping:
            continue

        metric = metric_mapping[metric_type]

        years = int(row["period_years"])

        company_id = row["company_id"]

        calculated, calc_flag = calculate_cagr(
            financials,
            company_id,
            metric,
            years,
        )

        source_value = float(row["value_pct"])

        if calculated is None:
            difference = None
            status = "NOT_COMPARABLE"
        else:
            difference = round(
                abs(calculated - source_value),
                2,
            )

            if difference > 5:
                status = "MANUAL_REVIEW"
            else:
                status = "PASS"

        results.append(
            {
                "company_id": company_id,
                "metric_type": metric_type,
                "period_years": years,
                "source_value_pct": source_value,
                "calculated_value_pct": calculated,
                "difference_pct": difference,
                "calculation_flag": calc_flag,
                "validation_status": status,
            }
        )

    result_df = pd.DataFrame(results)

    result_df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print()
    print("Validation output:")
    print(OUTPUT_FILE)

    print()
    print("Validation status:")
    print(
        result_df["validation_status"]
        .value_counts()
    )

    print()
    print("Manual review records:")

    review = result_df[
        result_df["validation_status"] == "MANUAL_REVIEW"
    ]

    if review.empty:
        print("None")
    else:
        print(
            review.to_string(index=False)
        )

    print()
    print(f"Validation rows: {len(result_df)}")


if __name__ == "__main__":
    main()
