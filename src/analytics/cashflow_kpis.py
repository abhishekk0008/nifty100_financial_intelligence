"""
Day 31 — Cash Flow Intelligence Module

Features:
1. CFO Quality Score
2. CapEx Intensity
3. Distress Signal
4. Deleveraging Flag
5. FCF CAGR (5-year)
6. FCF Conversion
7. Capital Allocation Classification
8. Output Excel + Distress CSV

Outputs:
    output/cashflow_intelligence.xlsx
    output/distress_alerts.csv
"""

from pathlib import Path
import logging

import pandas as pd


# ============================================================
# CONFIG
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = ROOT / "data" / "raw"
OUTPUT_DIR = ROOT / "output"

COMPANIES_FILE = RAW_DIR / "companies.xlsx"
CASHFLOW_FILE = RAW_DIR / "cashflow.xlsx"
PROFIT_LOSS_FILE = RAW_DIR / "profitandloss.xlsx"
BALANCE_SHEET_FILE = RAW_DIR / "balancesheet.xlsx"
SECTORS_FILE = RAW_DIR / "sectors.xlsx"

OUTPUT_FILE = OUTPUT_DIR / "cashflow_intelligence.xlsx"
DISTRESS_FILE = OUTPUT_DIR / "distress_alerts.csv"


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# HELPERS
# ============================================================

def clean_columns(df):
    """Clean dataframe column names."""

    df = df.copy()

    df.columns = [
        str(col).strip().lower().replace(" ", "_")
        for col in df.columns
    ]

    return df


def load_excel(path, header=1):
    """Load Excel file."""

    logger.info("Loading %s", path.name)

    df = pd.read_excel(
        path,
        header=header,
    )

    df = clean_columns(df)

    logger.info(
        "%s loaded successfully. Shape: %s",
        path.name,
        df.shape,
    )

    return df


def normalize_ids(df, column="company_id"):
    """Normalize company IDs."""

    if column not in df.columns:
        return df

    df = df.copy()

    df[column] = (
        df[column]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    return df


def normalize_numeric(df, columns):
    """Safely convert selected columns to numeric."""

    df = df.copy()

    for col in columns:

        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce",
            )

    return df


def safe_cagr(start, end, years):
    """
    Calculate CAGR.

    Conventional CAGR requires:
        start > 0
        end > 0
        years > 0

    Otherwise return NaN.
    """

    if pd.isna(start) or pd.isna(end):
        return float("nan")

    if years <= 0:
        return float("nan")

    if start <= 0 or end <= 0:
        return float("nan")

    return (
        ((end / start) ** (1 / years)) - 1
    ) * 100


def get_latest(df):
    """Return latest row after sorting by year."""

    if df.empty:
        return None

    return df.sort_values(
        "year"
    ).iloc[-1]


# ============================================================
# COMPANY ID NORMALIZATION
# ============================================================

def fix_known_id_mismatches(cashflow):
    """
    Fix known company-ID typo in cashflow.xlsx.

    Raw data:
        cashflow.xlsx -> AGTL

    Correct company ID:
        ATGL

    Raw Excel file is NOT modified.
    """

    cashflow = cashflow.copy()

    if "company_id" not in cashflow.columns:
        return cashflow

    mask = (
        cashflow["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
        .eq("AGTL")
    )

    count = int(mask.sum())

    if count > 0:

        cashflow.loc[
            mask,
            "company_id",
        ] = "ATGL"

        logger.info(
            "Applied company ID normalization: AGTL -> ATGL (%d rows)",
            count,
        )

    return cashflow


# ============================================================
# FCF
# ============================================================

def calculate_fcf(cashflow):
    """
    FCF proxy:

        FCF = CFO + Investing Activity

    Investing activity is normally negative when
    the company spends on CapEx.

    Therefore:
        FCF = operating_activity + investing_activity
    """

    cashflow = cashflow.copy()

    cashflow["fcf"] = (
        cashflow["operating_activity"]
        + cashflow["investing_activity"]
    )

    return cashflow


# ============================================================
# CFO QUALITY
# ============================================================

def calculate_cfo_quality(company_cf, company_pl):
    """
    CFO Quality Score:

        CFO / PAT

    Average over available years.

    Labels:
        > 1.0       High Quality
        0.5 - 1.0   Moderate
        < 0.5       Accrual Risk
    """

    merged = pd.merge(
        company_cf[
            [
                "year",
                "operating_activity",
            ]
        ],
        company_pl[
            [
                "year",
                "net_profit",
            ]
        ],
        on="year",
        how="inner",
    )

    if merged.empty:
        return float("nan"), None

    merged["cfo_pat_ratio"] = float("nan")

    valid = (
        merged["net_profit"].notna()
        & merged["operating_activity"].notna()
        & (merged["net_profit"] != 0)
    )

    merged.loc[
        valid,
        "cfo_pat_ratio",
    ] = (
        merged.loc[
            valid,
            "operating_activity",
        ]
        / merged.loc[
            valid,
            "net_profit",
        ]
    )

    ratios = (
        merged["cfo_pat_ratio"]
        .replace([float("inf"), float("-inf")], float("nan"))
        .dropna()
    )

    if ratios.empty:
        return float("nan"), None

    # Use latest 5 available years
    ratios = ratios.tail(5)

    score = float(ratios.mean())

    if score > 1.0:
        label = "High Quality"

    elif score >= 0.5:
        label = "Moderate"

    else:
        label = "Accrual Risk"

    return score, label


# ============================================================
# CAPEX INTENSITY
# ============================================================

def calculate_capex_intensity(
    latest_cf,
    latest_pl,
):
    """
    CapEx Intensity:

        abs(investing_activity) / sales * 100

    Labels:
        < 3%      Asset Light
        3-8%      Moderate
        > 8%      Capital Intensive
    """

    if latest_cf is None or latest_pl is None:
        return float("nan"), None

    investing = latest_cf.get(
        "investing_activity"
    )

    sales = latest_pl.get(
        "sales"
    )

    if pd.isna(investing) or pd.isna(sales):
        return float("nan"), None

    if sales == 0:
        return float("nan"), None

    intensity = (
        abs(float(investing))
        / float(sales)
    ) * 100

    if intensity < 3:
        label = "Asset Light"

    elif intensity <= 8:
        label = "Moderate"

    else:
        label = "Capital Intensive"

    return intensity, label


# ============================================================
# FCF CAGR
# ============================================================

def calculate_fcf_cagr_5yr(company_cf):
    """
    Calculate 5-year FCF CAGR.

    Requires at least 6 annual observations:
        Year 0 -> Year 5

    CAGR is calculated only when:
        starting FCF > 0
        ending FCF > 0
    """

    if company_cf.empty:
        return float("nan")

    data = (
        company_cf[
            ["year", "fcf"]
        ]
        .dropna()
        .sort_values("year")
    )

    if len(data) < 6:
        return float("nan")

    start = data.iloc[-6]["fcf"]
    end = data.iloc[-1]["fcf"]

    return safe_cagr(
        float(start),
        float(end),
        5,
    )


# ============================================================
# FCF CONVERSION
# ============================================================

def calculate_fcf_conversion(
    company_cf,
    company_pl,
):
    """
    FCF Conversion:

        Latest FCF / Latest PAT * 100
    """

    if company_cf.empty or company_pl.empty:
        return float("nan")

    latest_cf = get_latest(company_cf)
    latest_pl = get_latest(company_pl)

    if latest_cf is None or latest_pl is None:
        return float("nan")

    fcf = latest_cf.get("fcf")
    pat = latest_pl.get("net_profit")

    if pd.isna(fcf) or pd.isna(pat):
        return float("nan")

    if pat == 0:
        return float("nan")

    return (
        float(fcf)
        / float(pat)
    ) * 100


# ============================================================
# DISTRESS SIGNAL
# ============================================================

def calculate_distress(
    latest_cf,
):
    """
    Distress signal:

        CFO < 0
        AND
        CFF > 0

    Meaning:
        Operations are burning cash while
        financing is providing cash.
    """

    if latest_cf is None:
        return False

    cfo = latest_cf.get(
        "operating_activity"
    )

    cff = latest_cf.get(
        "financing_activity"
    )

    if pd.isna(cfo) or pd.isna(cff):
        return False

    return (
        float(cfo) < 0
        and float(cff) > 0
    )


# ============================================================
# DELEVERAGING
# ============================================================

def calculate_deleveraging(
    company_cf,
    company_bs,
):
    """
    Deleveraging signal:

        CFF < 0
        AND
        borrowings declining YoY
    """

    if (
        company_cf.empty
        or company_bs.empty
    ):
        return False

    latest_cf = get_latest(company_cf)

    if latest_cf is None:
        return False

    cff = latest_cf.get(
        "financing_activity"
    )

    if pd.isna(cff):
        return False

    if float(cff) >= 0:
        return False

    debt = (
        company_bs[
            [
                "year",
                "borrowings",
            ]
        ]
        .dropna()
        .sort_values("year")
    )

    if len(debt) < 2:
        return False

    latest_debt = debt.iloc[-1]["borrowings"]
    previous_debt = debt.iloc[-2]["borrowings"]

    if pd.isna(latest_debt) or pd.isna(previous_debt):
        return False

    return (
        float(latest_debt)
        < float(previous_debt)
    )


# ============================================================
# CAPITAL ALLOCATION
# ============================================================

def calculate_capital_allocation(
    distress_flag,
    deleveraging_flag,
    latest_cf,
):
    """
    Capital allocation classification.
    """

    if distress_flag:
        return "Distress Financing"

    if deleveraging_flag:
        return "Deleveraging"

    if latest_cf is None:
        return "Balanced"

    cff = latest_cf.get(
        "financing_activity"
    )

    investing = latest_cf.get(
        "investing_activity"
    )

    if pd.isna(cff) or pd.isna(investing):
        return "Balanced"

    cff = float(cff)
    investing = float(investing)

    if (
        investing < 0
        and cff < 0
    ):
        return "Growth Investment"

    if cff < 0:
        return "Shareholder Returns / Debt Reduction"

    if cff > 0:
        return "Shareholder Returns / Debt Reduction"

    return "Balanced"


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n" + "=" * 60)
    print("CASH FLOW INTELLIGENCE MODULE")
    print("=" * 60)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------------

    companies = load_excel(
        COMPANIES_FILE,
        header=1,
    )

    cashflow = load_excel(
        CASHFLOW_FILE,
        header=1,
    )

    profit_loss = load_excel(
        PROFIT_LOSS_FILE,
        header=1,
    )

    balance_sheet = load_excel(
        BALANCE_SHEET_FILE,
        header=1,
    )

    sectors = load_excel(
        SECTORS_FILE,
        header=0,
    )

    # --------------------------------------------------------
    # NORMALIZE IDs
    # --------------------------------------------------------

    cashflow = normalize_ids(
        cashflow,
        "company_id",
    )

    profit_loss = normalize_ids(
        profit_loss,
        "company_id",
    )

    balance_sheet = normalize_ids(
        balance_sheet,
        "company_id",
    )

    sectors = normalize_ids(
        sectors,
        "company_id",
    )

    # companies.xlsx uses "id"
    companies["id"] = (
        companies["id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # --------------------------------------------------------
    # FIX KNOWN CASHFLOW ID TYPO
    # --------------------------------------------------------

    cashflow = fix_known_id_mismatches(
        cashflow
    )

    # --------------------------------------------------------
    # NUMERIC CONVERSION
    # --------------------------------------------------------

    cashflow = normalize_numeric(
        cashflow,
        [
            "operating_activity",
            "investing_activity",
            "financing_activity",
            "net_cash_flow",
        ],
    )

    profit_loss = normalize_numeric(
        profit_loss,
        [
            "sales",
            "net_profit",
        ],
    )

    balance_sheet = normalize_numeric(
        balance_sheet,
        [
            "borrowings",
        ],
    )

    # --------------------------------------------------------
    # FCF
    # --------------------------------------------------------

    cashflow = calculate_fcf(
        cashflow
    )

    # --------------------------------------------------------
    # SECTOR MAP
    # --------------------------------------------------------

    sector_map = dict(
        zip(
            sectors["company_id"],
            sectors["broad_sector"]
            .astype(str)
            .str.strip(),
        )
    )

    # --------------------------------------------------------
    # COMPANY IDS
    # --------------------------------------------------------

    company_ids = (
        companies["id"]
        .dropna()
        .unique()
    )

    logger.info(
        "Companies to process: %d",
        len(company_ids),
    )

    # --------------------------------------------------------
    # GENERATION
    # --------------------------------------------------------

    records = []

    distress_records = []

    for company_id in company_ids:

        company_cf = cashflow[
            cashflow["company_id"]
            == company_id
        ].copy()

        company_pl = profit_loss[
            profit_loss["company_id"]
            == company_id
        ].copy()

        company_bs = balance_sheet[
            balance_sheet["company_id"]
            == company_id
        ].copy()

        company_cf = company_cf.sort_values(
            "year"
        )

        company_pl = company_pl.sort_values(
            "year"
        )

        company_bs = company_bs.sort_values(
            "year"
        )

        latest_cf = get_latest(
            company_cf
        )

        latest_pl = get_latest(
            company_pl
        )

        # ----------------------------------------------------
        # Sector
        # ----------------------------------------------------

        sector = sector_map.get(
            company_id
        )

        # ----------------------------------------------------
        # CFO QUALITY
        # ----------------------------------------------------

        cfo_quality_score, cfo_quality_label = (
            calculate_cfo_quality(
                company_cf,
                company_pl,
            )
        )

        # ----------------------------------------------------
        # CAPEX
        # ----------------------------------------------------

        capex_intensity_pct, capex_label = (
            calculate_capex_intensity(
                latest_cf,
                latest_pl,
            )
        )

        # ----------------------------------------------------
        # FCF CAGR
        # ----------------------------------------------------

        fcf_cagr_5yr = (
            calculate_fcf_cagr_5yr(
                company_cf
            )
        )

        # ----------------------------------------------------
        # FCF CONVERSION
        # ----------------------------------------------------

        fcf_conversion_pct = (
            calculate_fcf_conversion(
                company_cf,
                company_pl,
            )
        )

        # ----------------------------------------------------
        # DISTRESS
        # ----------------------------------------------------

        distress_flag = calculate_distress(
            latest_cf
        )

        # ----------------------------------------------------
        # DELEVERAGING
        # ----------------------------------------------------

        deleveraging_flag = (
            calculate_deleveraging(
                company_cf,
                company_bs,
            )
        )

        # ----------------------------------------------------
        # CAPITAL ALLOCATION
        # ----------------------------------------------------

        capital_allocation_label = (
            calculate_capital_allocation(
                distress_flag,
                deleveraging_flag,
                latest_cf,
            )
        )

        # ----------------------------------------------------
        # MAIN RECORD
        # ----------------------------------------------------

        records.append(
            {
                "company_id": company_id,
                "sector": sector,
                "cfo_quality_score": cfo_quality_score,
                "cfo_quality_label": cfo_quality_label,
                "capex_intensity_pct": capex_intensity_pct,
                "capex_label": capex_label,
                "fcf_cagr_5yr": fcf_cagr_5yr,
                "fcf_conversion_pct": fcf_conversion_pct,
                "distress_flag": distress_flag,
                "deleveraging_flag": deleveraging_flag,
                "capital_allocation_label": capital_allocation_label,
            }
        )

        # ----------------------------------------------------
        # DISTRESS ALERT
        # ----------------------------------------------------

        if distress_flag:

            cfo_value = (
                latest_cf["operating_activity"]
                if latest_cf is not None
                else float("nan")
            )

            cff_value = (
                latest_cf["financing_activity"]
                if latest_cf is not None
                else float("nan")
            )

            latest_net_profit = (
                latest_pl["net_profit"]
                if latest_pl is not None
                else float("nan")
            )

            distress_records.append(
                {
                    "company_id": company_id,
                    "sector": sector,
                    "cfo": cfo_value,
                    "cff": cff_value,
                    "latest_net_profit": latest_net_profit,
                }
            )

    # ========================================================
    # OUTPUT DATAFRAME
    # ========================================================

    output_columns = [
        "company_id",
        "sector",
        "cfo_quality_score",
        "cfo_quality_label",
        "capex_intensity_pct",
        "capex_label",
        "fcf_cagr_5yr",
        "fcf_conversion_pct",
        "distress_flag",
        "deleveraging_flag",
        "capital_allocation_label",
    ]

    result = pd.DataFrame(
        records,
        columns=output_columns,
    )

    result = result.sort_values(
        "company_id"
    ).reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # ROUND NUMBERS
    # --------------------------------------------------------

    for col in [
        "cfo_quality_score",
        "capex_intensity_pct",
        "fcf_cagr_5yr",
        "fcf_conversion_pct",
    ]:

        result[col] = result[col].round(4)

    # --------------------------------------------------------
    # WRITE EXCEL
    # --------------------------------------------------------

    result.to_excel(
        OUTPUT_FILE,
        index=False,
    )

    # --------------------------------------------------------
    # DISTRESS CSV
    # --------------------------------------------------------

    distress_df = pd.DataFrame(
        distress_records,
        columns=[
            "company_id",
            "sector",
            "cfo",
            "cff",
            "latest_net_profit",
        ],
    )

    distress_df.to_csv(
        DISTRESS_FILE,
        index=False,
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    print("\n" + "=" * 60)
    print("GENERATION SUMMARY")
    print("=" * 60)

    print(
        f"Companies processed: {len(result)}"
    )

    print(
        f"Output rows: {len(result)}"
    )

    print(
        f"Distress companies: "
        f"{int(result['distress_flag'].sum())}"
    )

    print(
        f"Deleveraging companies: "
        f"{int(result['deleveraging_flag'].sum())}"
    )

    print("\nCFO Quality:")

    print(
        result[
            "cfo_quality_label"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print("\nCapEx Classification:")

    print(
        result[
            "capex_label"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print("\nCapital Allocation:")

    print(
        result[
            "capital_allocation_label"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    # ========================================================
    # VALIDATION CHECKS
    # ========================================================

    print("\n" + "=" * 60)
    print("VALIDATION")
    print("=" * 60)

    expected_companies = set(
        company_ids
    )

    output_companies = set(
        result["company_id"]
    )

    missing_companies = (
        expected_companies
        - output_companies
    )

    if not missing_companies:
        print(
            "PASS: All companies are present."
        )
    else:
        print(
            "FAIL: Missing companies:",
            sorted(missing_companies),
        )

    expected_sectors = set(
        company_ids
    )

    missing_sectors = sorted(
        cid
        for cid in expected_sectors
        if cid not in sector_map
    )

    if not missing_sectors:
        print(
            "PASS: All companies have sector."
        )
    else:
        print(
            "FAIL: Companies missing sector:",
            missing_sectors,
        )

    # --------------------------------------------------------
    # ATGL SPECIFIC CHECK
    # --------------------------------------------------------

    atgl_row = result[
        result["company_id"] == "ATGL"
    ]

    if not atgl_row.empty:

        row = atgl_row.iloc[0]

        print("\nATGL validation:")

        print(
            "CFO Quality:",
            row["cfo_quality_score"],
            row["cfo_quality_label"],
        )

        print(
            "CapEx Intensity:",
            row["capex_intensity_pct"],
            row["capex_label"],
        )

        print(
            "FCF Conversion:",
            row["fcf_conversion_pct"],
        )

        if (
            pd.notna(row["cfo_quality_score"])
            and pd.notna(row["capex_intensity_pct"])
            and pd.notna(row["fcf_conversion_pct"])
        ):
            print(
                "PASS: ATGL cash-flow metrics calculated."
            )

        else:
            print(
                "FAIL: ATGL still contains core NaN."
            )

    # --------------------------------------------------------
    # NAN SUMMARY
    # --------------------------------------------------------

    print("\nNaN summary:")

    print(
        result.isna()
        .sum()
        .to_string()
    )

    # --------------------------------------------------------
    # FCF CAGR NOTE
    # --------------------------------------------------------

    fcf_cagr_nan = int(
        result[
            "fcf_cagr_5yr"
        ]
        .isna()
        .sum()
    )

    print(
        f"\nFCF CAGR NaN: {fcf_cagr_nan}"
    )

    print("\nOutput:")
    print(OUTPUT_FILE)

    print("\nDistress alerts:")
    print(DISTRESS_FILE)

    print("\n" + "=" * 60)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()