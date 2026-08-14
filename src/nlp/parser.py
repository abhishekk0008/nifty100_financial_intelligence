from pathlib import Path
import logging
import re

import pandas as pd


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = BASE_DIR / "data" / "raw" / "analysis.xlsx"
OUTPUT_DIR = BASE_DIR / "output"

PARSED_FILE = OUTPUT_DIR / "analysis_parsed.csv"
FAILURE_FILE = OUTPUT_DIR / "parse_failures.csv"


# ---------------------------------------------------------
# LOGGING
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# TARGET METRICS
# ---------------------------------------------------------
TARGET_METRICS = [
    "compounded_sales_growth",
    "compounded_profit_growth",
    "stock_price_cagr",
    "roe",
]


# ---------------------------------------------------------
# REGEX
# ---------------------------------------------------------
# Handles:
#   10 Years: 21%
#   5 Years: 6%
#   3 Years: -2%
#   TTM: 43%
#   Last Year: 12%
#
# Captures:
#   group 1 -> period
#   group 2 -> value
#
# The numeric-year pattern follows the task requirement:
# (\d+)\s*Years?
#
# Additional TTM / Last Year support is included because
# those values are present in the actual analysis.xlsx file.
PERIOD_VALUE_PATTERN = re.compile(
    r"^\s*(?:(\d+)\s*Years?|TTM|Last\s+Year)\s*:\s*([-+]?\d+(?:\.\d+)?)\s*%\s*$",
    re.IGNORECASE,
)


# ---------------------------------------------------------
# PERIOD NORMALIZATION
# ---------------------------------------------------------
def normalize_period(text: str):
    """
    Convert period text into numeric years.

    Examples:
        '10 Years' -> 10
        '5 Years'  -> 5
        '3 Years'  -> 3
        'TTM'      -> 1
        'Last Year' -> 1
    """

    text = str(text).strip().lower()

    year_match = re.match(r"(\d+)\s*years?", text)

    if year_match:
        return int(year_match.group(1))

    if text == "ttm":
        return 1

    if text == "last year":
        return 1

    return None


# ---------------------------------------------------------
# PARSE ONE CELL
# ---------------------------------------------------------
def parse_metric_text(value):
    """
    Parse one analysis text cell.

    Returns:
        period_years, value_pct
    """

    if pd.isna(value):
        return None, None

    text = str(value).strip()

    match = PERIOD_VALUE_PATTERN.match(text)

    if not match:
        return None, None

    numeric_years = match.group(1)
    percentage = float(match.group(2))

    if numeric_years is not None:
        period_years = int(numeric_years)
    else:
        # TTM / Last Year
        period_years = normalize_period(text.split(":")[0])

    return period_years, percentage


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------
def load_analysis():
    logger.info("Loading analysis.xlsx")

    # Actual Excel file has title row at row 1.
    # Real column headers are on row 2.
    df = pd.read_excel(INPUT_FILE, header=1)

    logger.info("analysis.xlsx loaded successfully. Shape: %s", df.shape)

    return df


# ---------------------------------------------------------
# BUILD PARSED OUTPUT
# ---------------------------------------------------------
def build_parser():
    df = load_analysis()

    required_columns = [
        "company_id",
        *TARGET_METRICS,
    ]

    missing_columns = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns in analysis.xlsx: {missing_columns}"
        )

    parsed_rows = []
    failure_rows = []

    for _, row in df.iterrows():

        company_id = row["company_id"]

        for metric in TARGET_METRICS:

            raw_text = row[metric]

            period_years, value_pct = parse_metric_text(raw_text)

            if period_years is None or value_pct is None:

                failure_rows.append(
                    {
                        "company_id": company_id,
                        "metric_type": metric,
                        "raw_text": raw_text,
                        "reason": "Pattern did not match",
                    }
                )

                logger.warning(
                    "Parse failure | company=%s | metric=%s | value=%s",
                    company_id,
                    metric,
                    raw_text,
                )

                continue

            parsed_rows.append(
                {
                    "company_id": company_id,
                    "metric_type": metric,
                    "period_years": period_years,
                    "value_pct": value_pct,
                }
            )

    parsed_df = pd.DataFrame(
        parsed_rows,
        columns=[
            "company_id",
            "metric_type",
            "period_years",
            "value_pct",
        ],
    )

    failures_df = pd.DataFrame(
        failure_rows,
        columns=[
            "company_id",
            "metric_type",
            "raw_text",
            "reason",
        ],
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    parsed_df.to_csv(PARSED_FILE, index=False)
    failures_df.to_csv(FAILURE_FILE, index=False)

    logger.info(
        "Parsed output written: %s | rows=%d",
        PARSED_FILE,
        len(parsed_df),
    )

    logger.info(
        "Parse failures written: %s | rows=%d",
        FAILURE_FILE,
        len(failures_df),
    )

    return parsed_df, failures_df


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
if __name__ == "__main__":

    parsed, failures = build_parser()

    print("\n" + "=" * 60)
    print("NLP ANALYSIS TEXT PARSER")
    print("=" * 60)

    print(f"Input rows: {20}")
    print(f"Parsed rows: {len(parsed)}")
    print(f"Parse failures: {len(failures)}")

    print("\nMetric counts:")
    print(parsed["metric_type"].value_counts())

    print("\nParsed sample:")
    print(parsed.head(20).to_string(index=False))

    if len(failures) > 0:
        print("\nFailures:")
        print(failures.to_string(index=False))
    else:
        print("\nNo parse failures.")