from pathlib import Path
import logging
import re

import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"

COMPANIES_FILE = RAW_DIR / "companies.xlsx"
CASHFLOW_FILE = RAW_DIR / "cashflow.xlsx"
PROFIT_LOSS_FILE = RAW_DIR / "profitandloss.xlsx"

REPORT_DIR = PROJECT_ROOT / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = REPORT_DIR / "capital_allocation.csv"


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# CONSTANTS
# ============================================================

EXPECTED_MASTER_COMPANIES = 92

EXPECTED_PATTERNS = [
    "Reinvestor",
    "Growth Funded by Debt",
    "Distress Signal",
    "Liquidating Assets",
    "Mixed",
    "Cash Accumulator",
    "Pre-Revenue",
    "Shareholder Returns",
]

MONTH_MAP = {
    "Mar": 3,
    "Jun": 6,
    "Sep": 9,
    "Dec": 12,
}


# ============================================================
# GENERAL HELPERS
# ============================================================

def clean_column_name(value):
    """
    Normalize Excel column names.

    Examples:
        Company ID -> company_id
        CompanyId  -> companyid
        Net Profit -> net_profit
    """

    if pd.isna(value):
        return ""

    value = str(value).strip().lower()

    value = value.replace("\n", " ")
    value = value.replace("\r", " ")

    value = re.sub(
        r"[^a-z0-9]+",
        "_",
        value,
    )

    value = re.sub(
        r"_+",
        "_",
        value,
    )

    return value.strip("_")


def clean_company_id(value):
    """
    Normalize company identifiers.
    """

    if pd.isna(value):
        return None

    value = str(value).strip().upper()

    if not value:
        return None

    # Remove accidental surrounding spaces.
    value = re.sub(r"\s+", "", value)

    return value


def normalize_year(value):
    """
    Normalize financial year labels.

    Supported:
        Mar 2013
        Mar-13
        Mar-2013
        Mar/13
        Mar2013
        Sep2016

    Output:
        Mar 2013
        Jun 2013
        Sep 2013
        Dec 2013
    """

    if pd.isna(value):
        return None

    # Handle pandas Timestamp / datetime.
    if isinstance(
        value,
        (
            pd.Timestamp,
            np.datetime64,
        ),
    ):
        try:
            timestamp = pd.to_datetime(value)

            month = timestamp.month
            year = timestamp.year

            reverse_month = {
                3: "Mar",
                6: "Jun",
                9: "Sep",
                12: "Dec",
            }

            if month in reverse_month:
                return f"{reverse_month[month]} {year}"

        except Exception:
            pass

    value = str(value).strip()

    if not value:
        return None

    # Remove .0 if Excel converted year-like values.
    value = re.sub(
        r"\.0$",
        "",
        value,
    )

    # Normalize separators.
    value = re.sub(
        r"[-_/]+",
        " ",
        value,
    )

    # Normalize whitespace.
    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip()

    # --------------------------------------------------------
    # Month + 2 digit year
    # --------------------------------------------------------

    match = re.match(
        r"^(Mar|Jun|Sep|Dec)\s*(\d{2})$",
        value,
        flags=re.IGNORECASE,
    )

    if match:
        month = match.group(1).title()
        year = 2000 + int(match.group(2))

        return f"{month} {year}"

    # --------------------------------------------------------
    # Month + 4 digit year
    # --------------------------------------------------------

    match = re.match(
        r"^(Mar|Jun|Sep|Dec)\s*(\d{4})$",
        value,
        flags=re.IGNORECASE,
    )

    if match:
        month = match.group(1).title()
        year = int(match.group(2))

        return f"{month} {year}"

    # --------------------------------------------------------
    # Month immediately followed by year
    # --------------------------------------------------------

    match = re.match(
        r"^(Mar|Jun|Sep|Dec)(\d{4})$",
        value,
        flags=re.IGNORECASE,
    )

    if match:
        month = match.group(1).title()
        year = int(match.group(2))

        return f"{month} {year}"

    # --------------------------------------------------------
    # Generic date-like values
    # --------------------------------------------------------

    try:
        parsed = pd.to_datetime(
            value,
            errors="coerce",
        )

        if not pd.isna(parsed):

            reverse_month = {
                3: "Mar",
                6: "Jun",
                9: "Sep",
                12: "Dec",
            }

            if parsed.month in reverse_month:
                return (
                    f"{reverse_month[parsed.month]} "
                    f"{parsed.year}"
                )

    except Exception:
        pass

    return value


def year_sort_key(value):
    """
    Return sortable tuple:

        (year, month)
    """

    if not value:
        return (0, 0)

    parts = str(value).split()

    if len(parts) != 2:
        return (0, 0)

    month = MONTH_MAP.get(
        parts[0].title(),
        0,
    )

    try:
        year = int(parts[1])
    except (
        ValueError,
        TypeError,
    ):
        year = 0

    return (
        year,
        month,
    )


def numeric_series(series):
    """
    Safely convert a pandas Series to numeric.
    """

    return pd.to_numeric(
        series,
        errors="coerce",
    )


# ============================================================
# EXCEL HEADER DETECTION
# ============================================================

def detect_header_row(
    file_path,
    required_terms,
):
    """
    Robust Excel header detection.

    IMPORTANT:
    Exact column matches are given priority.

    This prevents a title such as:

        mkt_fintech_nifty_100_companies_92_records

    from being incorrectly selected as the header merely
    because it contains the word 'companies'.
    """

    preview = pd.read_excel(
        file_path,
        header=None,
        nrows=20,
    )

    required_clean = [
        clean_column_name(term)
        for term in required_terms
    ]

    best_exact_row = None
    best_exact_score = -1

    best_fuzzy_row = None
    best_fuzzy_score = -1

    for row_index in range(
        len(preview)
    ):

        values = [
            clean_column_name(value)
            for value in preview.iloc[
                row_index
            ].tolist()
        ]

        values = [
            value
            for value in values
            if value
        ]

        if not values:
            continue

        exact_score = 0
        fuzzy_score = 0

        for term in required_clean:

            # Exact match.
            if term in values:
                exact_score += 1

            # Fuzzy match only for fallback.
            else:
                for value in values:
                    if (
                        term in value
                        or value in term
                    ):
                        fuzzy_score += 1
                        break

        # Exact matches always dominate.
        if exact_score > best_exact_score:
            best_exact_score = exact_score
            best_exact_row = row_index

        if fuzzy_score > best_fuzzy_score:
            best_fuzzy_score = fuzzy_score
            best_fuzzy_row = row_index

    # --------------------------------------------------------
    # Exact header detection
    # --------------------------------------------------------

    if best_exact_score > 0:
        logger.info(
            "%s detected header row: %s",
            file_path.name,
            best_exact_row,
        )

        return best_exact_row

    # --------------------------------------------------------
    # Fuzzy fallback
    # --------------------------------------------------------

    if best_fuzzy_score > 0:
        logger.warning(
            "%s: using fuzzy header detection. "
            "Detected row: %s",
            file_path.name,
            best_fuzzy_row,
        )

        return best_fuzzy_row

    logger.warning(
        "%s: could not detect header row. "
        "Using header=0.",
        file_path.name,
    )

    return 0


def load_excel(
    file_path,
    required_terms,
):
    """
    Load Excel robustly.
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    header_row = detect_header_row(
        file_path,
        required_terms,
    )

    df = pd.read_excel(
        file_path,
        header=header_row,
    )

    # Normalize columns.
    df.columns = [
        clean_column_name(column)
        for column in df.columns
    ]

    # Remove empty columns.
    df = df.dropna(
        axis=1,
        how="all",
    )

    # Remove completely empty rows.
    df = df.dropna(
        axis=0,
        how="all",
    )

    logger.info(
        "%s loaded successfully. Shape: %s",
        file_path.name,
        df.shape,
    )

    return df.reset_index(
        drop=True
    )


# ============================================================
# COLUMN FINDER
# ============================================================

def find_column(
    df,
    candidates,
    required=True,
):
    """
    Find a column.

    Exact matching first.
    Fuzzy matching second.

    Prevents accidental matching of title-like columns.
    """

    columns = list(df.columns)

    normalized = {
        clean_column_name(column): column
        for column in columns
    }

    # --------------------------------------------------------
    # Exact match
    # --------------------------------------------------------

    for candidate in candidates:

        candidate_clean = (
            clean_column_name(candidate)
        )

        if candidate_clean in normalized:
            return normalized[
                candidate_clean
            ]

    # --------------------------------------------------------
    # Fuzzy match
    # --------------------------------------------------------

    for candidate in candidates:

        candidate_clean = (
            clean_column_name(candidate)
        )

        for (
            column_clean,
            original,
        ) in normalized.items():

            if (
                candidate_clean in column_clean
                or column_clean in candidate_clean
            ):
                return original

    if required:
        raise KeyError(
            "Could not find any of these "
            f"columns: {candidates}. "
            f"Available columns: {columns}"
        )

    return None


# ============================================================
# MASTER COMPANIES
# ============================================================

def load_master_companies():
    """
    Load authoritative company universe.

    Expected: 92 companies.
    """

    logger.info(
        "Loading companies.xlsx"
    )

    companies = load_excel(
        COMPANIES_FILE,
        [
            "id",
            "company_id",
            "companyid",
            "symbol",
            "company_name",
            "company",
        ],
    )

    company_col = find_column(
        companies,
        [
            "id",
            "company_id",
            "companyid",
            "symbol",
            "company",
        ],
    )

    companies["company_id"] = (
        companies[company_col]
        .apply(clean_company_id)
    )

    companies = companies[
        companies["company_id"].notna()
    ].copy()

    companies = companies.drop_duplicates(
        subset=["company_id"],
        keep="first",
    )

    master_ids = sorted(
        companies["company_id"].unique()
    )

    logger.info(
        "Master company universe: %s companies",
        len(master_ids),
    )

    if len(master_ids) != EXPECTED_MASTER_COMPANIES:
        logger.warning(
            "Expected %s master companies, "
            "found %s.",
            EXPECTED_MASTER_COMPANIES,
            len(master_ids),
        )

    return companies[
        ["company_id"]
    ].copy()


# ============================================================
# NORMALIZE DATASET
# ============================================================

def normalize_dataset(
    df,
    dataset_name,
    master_ids,
):
    """
    Normalize company_id and year.

    Then restrict to master universe.
    """

    company_col = find_column(
        df,
        [
            "company_id",
            "companyid",
            "id",
            "symbol",
            "company",
        ],
    )

    year_col = find_column(
        df,
        [
            "year",
            "date",
            "period",
            "financial_year",
            "financialyear",
        ],
    )

    if company_col != "company_id":

        df = df.rename(
            columns={
                company_col:
                    "company_id"
            }
        )

    if year_col != "year":

        df = df.rename(
            columns={
                year_col:
                    "year"
            }
        )

    df["company_id"] = (
        df["company_id"]
        .apply(clean_company_id)
    )

    df["year"] = (
        df["year"]
        .apply(normalize_year)
    )

    # Remove rows with no usable company/year.
    df = df[
        df["company_id"].notna()
        & df["year"].notna()
    ].copy()

    logger.info(
        "%s normalized. Rows: %s",
        dataset_name,
        len(df),
    )

    before = len(df)

    df = df[
        df["company_id"].isin(
            master_ids
        )
    ].copy()

    after = len(df)

    logger.info(
        "%s rows before master filtering: %s",
        dataset_name,
        before,
    )

    logger.info(
        "%s rows after master filtering: %s",
        dataset_name,
        after,
    )

    logger.info(
        "%s rows removed because company is "
        "outside master universe: %s",
        dataset_name,
        before - after,
    )

    return df.reset_index(
        drop=True
    )


# ============================================================
# DUPLICATE HANDLING
# ============================================================

def deduplicate_company_year(
    df,
    dataset_name,
):
    """
    Deduplicate AFTER company/year normalization.

    Therefore:

        Mar 2013
        Mar-13

    become the same key.
    """

    duplicate_mask = df.duplicated(
        [
            "company_id",
            "year",
        ],
        keep=False,
    )

    duplicate_rows = int(
        duplicate_mask.sum()
    )

    duplicate_combinations = int(
        df.loc[
            duplicate_mask,
            [
                "company_id",
                "year",
            ],
        ]
        .drop_duplicates()
        .shape[0]
    )

    if duplicate_rows:

        logger.warning(
            "%s contains %s duplicate "
            "company-year rows across "
            "%s combinations.",
            dataset_name,
            duplicate_rows,
            duplicate_combinations,
        )

        # Keep the last source row deterministically.
        df = (
            df.reset_index(
                drop=False
            )
            .rename(
                columns={
                    "index":
                        "_source_order"
                }
            )
            .sort_values(
                [
                    "company_id",
                    "year",
                    "_source_order",
                ]
            )
            .drop_duplicates(
                subset=[
                    "company_id",
                    "year",
                ],
                keep="last",
            )
            .drop(
                columns=[
                    "_source_order"
                ]
            )
        )

    remaining = int(
        df.duplicated(
            [
                "company_id",
                "year",
            ]
        ).sum()
    )

    logger.info(
        "%s: remaining duplicate "
        "company-year rows: %s",
        dataset_name,
        remaining,
    )

    return df.reset_index(
        drop=True
    )


# ============================================================
# CASHFLOW
# ============================================================

def load_cashflow(
    master_ids,
):

    logger.info(
        "Loading cashflow.xlsx"
    )

    cashflow = load_excel(
        CASHFLOW_FILE,
        [
            "company_id",
            "company",
            "symbol",
            "id",
            "year",
            "cash_flow",
            "cashflow",
        ],
    )

    cashflow = normalize_dataset(
        cashflow,
        "Cashflow",
        master_ids,
    )

    # --------------------------------------------------------
    # CFO
    # --------------------------------------------------------

    operating_cash_flow_col = find_column(
        cashflow,
        [
            "cash_from_operating_activity",
            "cash_from_operating_activities",
            "cash_flow_from_operating_activity",
            "cash_flow_from_operating_activities",
            "operating_cash_flow",
            "cash_from_operations",
            "cfo",
        ],
        required=False,
    )

    # --------------------------------------------------------
    # CFI
    # --------------------------------------------------------

    investing_cash_flow_col = find_column(
        cashflow,
        [
            "cash_from_investing_activity",
            "cash_from_investing_activities",
            "cash_flow_from_investing_activity",
            "cash_flow_from_investing_activities",
            "investing_cash_flow",
            "cfi",
        ],
        required=False,
    )

    # --------------------------------------------------------
    # CFF
    # --------------------------------------------------------

    financing_cash_flow_col = find_column(
        cashflow,
        [
            "cash_from_financing_activity",
            "cash_from_financing_activities",
            "cash_flow_from_financing_activity",
            "cash_flow_from_financing_activities",
            "financing_cash_flow",
            "cff",
        ],
        required=False,
    )

    rename_map = {}

    if operating_cash_flow_col:
        rename_map[
            operating_cash_flow_col
        ] = "cfo"

    if investing_cash_flow_col:
        rename_map[
            investing_cash_flow_col
        ] = "cfi"

    if financing_cash_flow_col:
        rename_map[
            financing_cash_flow_col
        ] = "cff"

    cashflow = cashflow.rename(
        columns=rename_map
    )

    # Always create internal columns.
    for column in [
        "cfo",
        "cfi",
        "cff",
    ]:

        if column not in cashflow.columns:
            cashflow[column] = np.nan

        cashflow[column] = numeric_series(
            cashflow[column]
        )

    # Deduplicate only AFTER normalization.
    cashflow = deduplicate_company_year(
        cashflow,
        "cashflow.xlsx",
    )

    return cashflow


# ============================================================
# PROFIT & LOSS
# ============================================================

def load_profit_loss(
    master_ids,
):

    logger.info(
        "Loading profitandloss.xlsx"
    )

    pnl = load_excel(
        PROFIT_LOSS_FILE,
        [
            "company_id",
            "company",
            "symbol",
            "id",
            "year",
            "profit",
            "profit_loss",
            "net_profit",
            "net_profit_loss",
        ],
    )

    pnl = normalize_dataset(
        pnl,
        "P&L",
        master_ids,
    )

    net_profit_col = find_column(
        pnl,
        [
            "net_profit",
            "net_profit_loss",
            "profit_after_tax",
            "profit_after_tax_pat",
            "pat",
            "profit",
        ],
        required=False,
    )

    if net_profit_col:

        if net_profit_col != "net_profit":

            pnl = pnl.rename(
                columns={
                    net_profit_col:
                        "net_profit"
                }
            )

        pnl["net_profit"] = numeric_series(
            pnl["net_profit"]
        )

    else:

        logger.warning(
            "No net profit column found "
            "in profitandloss.xlsx."
        )

        pnl["net_profit"] = np.nan

    pnl = deduplicate_company_year(
        pnl,
        "profitandloss.xlsx",
    )

    return pnl


# ============================================================
# SIGN
# ============================================================

def calculate_sign(series):
    """
    Return:
        + positive
        - negative
        0 zero
        Unknown missing
    """

    numeric = numeric_series(
        series
    )

    result = pd.Series(
        "Unknown",
        index=numeric.index,
        dtype="object",
    )

    result.loc[
        numeric > 0
    ] = "+"

    result.loc[
        numeric < 0
    ] = "-"

    result.loc[
        numeric == 0
    ] = "0"

    return result


# ============================================================
# CFO QUALITY
# ============================================================

def calculate_cfo_quality(
    df,
):
    """
    CFO quality:

        CFO / absolute net income

    Missing/zero denominator -> NaN.
    """

    result = df.copy()

    cfo = numeric_series(
        result["cfo"]
    )

    net_income = numeric_series(
        result.get(
            "net_profit",
            pd.Series(
                np.nan,
                index=result.index,
            ),
        )
    )

    denominator = net_income.abs()

    valid = (
        denominator.notna()
        & denominator.ne(0)
        & cfo.notna()
    )

    result["cfo_quality"] = np.nan

    result.loc[
        valid,
        "cfo_quality",
    ] = (
        cfo.loc[valid]
        / denominator.loc[valid]
    )

    # --------------------------------------------------------
    # IMPORTANT:
    # Do NOT use np.select here.
    # It can produce string/float dtype conflict.
    # --------------------------------------------------------

    label = pd.Series(
        "Unknown",
        index=result.index,
        dtype="object",
    )

    quality = result[
        "cfo_quality"
    ]

    label.loc[
        quality < 0.5
    ] = "Weak"

    label.loc[
        quality.ge(0.5)
        & quality.lt(1.0)
    ] = "Moderate"

    label.loc[
        quality.ge(1.0)
    ] = "Strong"

    result[
        "cfo_quality_label"
    ] = label

    return result


# ============================================================
# CAPITAL ALLOCATION CLASSIFICATION
# ============================================================

def classify_capital_allocation(
    df,
):
    """
    Eight-pattern capital allocation matrix.

    Priority:
        1. Pre-Revenue
        2. Distress Signal
        3. Liquidating Assets
        4. Growth Funded by Debt
        5. Shareholder Returns
        6. Reinvestor
        7. Cash Accumulator
        8. Mixed
    """

    cfo = numeric_series(
        df["cfo"]
    )

    cfi = numeric_series(
        df["cfi"]
    )

    cff = numeric_series(
        df["cff"]
    )

    fcf = numeric_series(
        df["free_cash_flow"]
    )

    net_profit = numeric_series(
        df.get(
            "net_profit",
            pd.Series(
                np.nan,
                index=df.index,
            ),
        )
    )

    cfo_positive = cfo > 0
    cfo_negative = cfo < 0

    cfi_positive = cfi > 0
    cfi_negative = cfi < 0

    cff_positive = cff > 0
    cff_negative = cff < 0

    # --------------------------------------------------------
    # Missing financial data
    #
    # Do not label a completely empty row as a real pattern.
    # Such rows are represented as Mixed for the project-wide
    # 8-pattern output while the underlying metrics remain NaN.
    # --------------------------------------------------------

    no_cashflow_data = (
        cfo.isna()
        & cfi.isna()
        & cff.isna()
    )

    # --------------------------------------------------------
    # Pre-Revenue
    # --------------------------------------------------------

    pre_revenue = (
        cfo_negative
        & (
            net_profit.isna()
            | net_profit.le(0)
        )
    )

    # --------------------------------------------------------
    # Distress
    # --------------------------------------------------------

    distress = (
        cfo_negative
        & cff_positive
    )

    # --------------------------------------------------------
    # Liquidating Assets
    # --------------------------------------------------------

    liquidating = (
        cfo_positive
        & cfi_positive
        & ~distress
    )

    # --------------------------------------------------------
    # Growth Funded by Debt
    # --------------------------------------------------------

    growth_debt = (
        cfo_positive
        & cfi_negative
        & cff_positive
        & ~distress
        & ~liquidating
    )

    # --------------------------------------------------------
    # Shareholder Returns
    # --------------------------------------------------------

    shareholder_returns = (
        cfo_positive
        & fcf.gt(0)
        & cff_negative
        & cfi_negative
        & ~growth_debt
        & ~distress
        & ~liquidating
    )

    # --------------------------------------------------------
    # Reinvestor
    # --------------------------------------------------------

    reinvestor = (
        cfo_positive
        & cfi_negative
        & cff_negative
        & ~shareholder_returns
        & ~growth_debt
        & ~distress
        & ~liquidating
    )

    # --------------------------------------------------------
    # Cash Accumulator
    # --------------------------------------------------------

    cash_accumulator = (
        cfo_positive
        & fcf.gt(0)
        & cfi_negative
        & ~growth_debt
        & ~reinvestor
        & ~shareholder_returns
        & ~distress
        & ~liquidating
    )

    # --------------------------------------------------------
    # Dtype-safe classification
    # --------------------------------------------------------

    result = pd.Series(
        "Mixed",
        index=df.index,
        dtype="object",
    )

    result.loc[
        pre_revenue
    ] = "Pre-Revenue"

    result.loc[
        distress
    ] = "Distress Signal"

    result.loc[
        liquidating
    ] = "Liquidating Assets"

    result.loc[
        growth_debt
    ] = "Growth Funded by Debt"

    result.loc[
        shareholder_returns
    ] = "Shareholder Returns"

    result.loc[
        reinvestor
    ] = "Reinvestor"

    result.loc[
        cash_accumulator
    ] = "Cash Accumulator"

    # Completely missing source data remains Mixed.
    result.loc[
        no_cashflow_data
    ] = "Mixed"

    return result


# ============================================================
# CALCULATE METRICS
# ============================================================

def calculate_metrics(
    combined,
):
    """
    Calculate all capital allocation metrics.

    IMPORTANT:
    The input must already contain:
        company_id
        year
        cfo
        cfi
        cff
        net_profit

    No second merge is performed here.
    """

    logger.info(
        "Calculating capital allocation metrics"
    )

    merged = combined.copy()

    # --------------------------------------------------------
    # CFO QUALITY
    # --------------------------------------------------------

    merged = calculate_cfo_quality(
        merged
    )

    # --------------------------------------------------------
    # FREE CASH FLOW
    #
    # FCF = CFO + CFI
    # --------------------------------------------------------

    cfo = numeric_series(
        merged["cfo"]
    )

    cfi = numeric_series(
        merged["cfi"]
    )

    merged["free_cash_flow"] = (
        cfo + cfi
    )

    # --------------------------------------------------------
    # CAPEX INTENSITY
    #
    # Absolute CFI / absolute CFO * 100
    # --------------------------------------------------------

    cfo_abs = cfo.abs()
    cfi_abs = cfi.abs()

    valid_capex = (
        cfo_abs.notna()
        & cfo_abs.ne(0)
        & cfi_abs.notna()
    )

    merged["capex_intensity"] = np.nan

    merged.loc[
        valid_capex,
        "capex_intensity",
    ] = (
        cfi_abs.loc[valid_capex]
        / cfo_abs.loc[valid_capex]
        * 100
    )

    capex_label = pd.Series(
        "Unknown",
        index=merged.index,
        dtype="object",
    )

    capex = merged[
        "capex_intensity"
    ]

    capex_label.loc[
        capex < 25
    ] = "Low"

    capex_label.loc[
        capex.ge(25)
        & capex.lt(50)
    ] = "Moderate"

    capex_label.loc[
        capex.ge(50)
    ] = "High"

    merged[
        "capex_label"
    ] = capex_label

    # --------------------------------------------------------
    # FCF CONVERSION
    #
    # FCF / CFO * 100
    # --------------------------------------------------------

    valid_conversion = (
        cfo.notna()
        & cfo.ne(0)
        & merged[
            "free_cash_flow"
        ].notna()
    )

    merged[
        "fcf_conversion"
    ] = np.nan

    merged.loc[
        valid_conversion,
        "fcf_conversion",
    ] = (
        merged.loc[
            valid_conversion,
            "free_cash_flow",
        ]
        / cfo.loc[
            valid_conversion
        ]
        * 100
    )

    # --------------------------------------------------------
    # SIGNS
    # --------------------------------------------------------

    merged["cfo_sign"] = calculate_sign(
        merged["cfo"]
    )

    merged["cfi_sign"] = calculate_sign(
        merged["cfi"]
    )

    merged["cff_sign"] = calculate_sign(
        merged["cff"]
    )

    # --------------------------------------------------------
    # PATTERN
    # --------------------------------------------------------

    merged[
        "pattern_label"
    ] = classify_capital_allocation(
        merged
    )

    return merged


# ============================================================
# ENSURE MASTER COVERAGE
# ============================================================

def add_missing_master_companies(
    result,
    master_ids,
):
    """
    Ensure all 92 master companies are present.

    IMPORTANT:
    This does NOT fabricate financial values.

    If a master company has no financial records in either
    source file, a placeholder row is created with:

        year = None
        financial metrics = NaN
        pattern = Mixed

    This allows the portfolio universe to remain complete
    without inventing financial data.
    """

    result = result.copy()

    result["company_id"] = (
        result["company_id"]
        .apply(clean_company_id)
    )

    present = set(
        result[
            "company_id"
        ]
        .dropna()
        .unique()
    )

    missing = sorted(
        set(master_ids)
        - present
    )

    if not missing:
        return result

    logger.warning(
        "Companies missing from financial source data: %s",
        missing,
    )

    placeholder_rows = []

    for company_id in missing:

        placeholder_rows.append(
            {
                "company_id":
                    company_id,
                "year":
                    None,
                "cfo":
                    np.nan,
                "cfi":
                    np.nan,
                "cff":
                    np.nan,
                "net_profit":
                    np.nan,
                "free_cash_flow":
                    np.nan,
                "cfo_quality":
                    np.nan,
                "cfo_quality_label":
                    "Unknown",
                "capex_intensity":
                    np.nan,
                "capex_label":
                    "Unknown",
                "fcf_conversion":
                    np.nan,
                "cfo_sign":
                    "Unknown",
                "cfi_sign":
                    "Unknown",
                "cff_sign":
                    "Unknown",
                "pattern_label":
                    "Mixed",
            }
        )

    placeholders = pd.DataFrame(
        placeholder_rows
    )

    result = pd.concat(
        [
            result,
            placeholders,
        ],
        ignore_index=True,
    )

    return result


# ============================================================
# VALIDATION
# ============================================================

def validate_master_coverage(
    result,
    master_ids,
):
    """
    Validate final company coverage.
    """

    master_set = set(
        master_ids
    )

    output_set = set(
        result[
            "company_id"
        ]
        .dropna()
        .astype(str)
        .str.upper()
    )

    extra = sorted(
        output_set
        - master_set
    )

    missing = sorted(
        master_set
        - output_set
    )

    print(
        "\n"
        + "=" * 60
    )

    print(
        "VALIDATION"
    )

    print(
        "=" * 60
    )

    print(
        f"MASTER COMPANIES: "
        f"{len(master_set)}"
    )

    print(
        f"OUTPUT COMPANIES: "
        f"{len(output_set)}"
    )

    if extra:

        print(
            "FAIL: Extra companies:",
            extra,
        )

    else:

        print(
            "PASS: No extra companies."
        )

    if missing:

        print(
            "FAIL: Missing companies:",
            missing,
        )

    else:

        print(
            "PASS: All master companies present."
        )

    duplicates = int(
        result.duplicated(
            [
                "company_id",
                "year",
            ]
        ).sum()
    )

    # Rows with missing year are placeholders.
    # Multiple missing-year rows should never exist.
    if duplicates:

        print(
            "FAIL: Duplicate "
            f"company-year rows: {duplicates}"
        )

    else:

        print(
            "PASS: No duplicate "
            "company-year rows."
        )

    return (
        len(extra) == 0
        and len(missing) == 0
        and duplicates == 0
    )


# ============================================================
# OUTPUT COLUMNS
# ============================================================

def select_output_columns(
    result,
):
    """
    Keep exact expected output structure.
    """

    output_columns = [
        "company_id",
        "year",
        "free_cash_flow",
        "cfo_quality",
        "cfo_quality_label",
        "capex_intensity",
        "capex_label",
        "fcf_conversion",
        "cfo_sign",
        "cfi_sign",
        "cff_sign",
        "pattern_label",
    ]

    for column in output_columns:

        if column not in result.columns:

            if column in [
                "cfo_quality_label",
                "capex_label",
                "cfo_sign",
                "cfi_sign",
                "cff_sign",
                "pattern_label",
            ]:

                result[column] = (
                    "Unknown"
                )

            else:

                result[column] = np.nan

    return result[
        output_columns
    ].copy()


# ============================================================
# SAVE REPORT
# ============================================================

def save_report(
    result,
):
    """
    Save final capital allocation CSV.
    """

    result = select_output_columns(
        result
    )

    # Normalize one final time.
    result["company_id"] = (
        result["company_id"]
        .apply(clean_company_id)
    )

    result["year"] = (
        result["year"]
        .apply(normalize_year)
    )

    # --------------------------------------------------------
    # Remove duplicate company/year combinations one final time
    # --------------------------------------------------------

    result = (
        result
        .reset_index(
            drop=False
        )
        .rename(
            columns={
                "index":
                    "_save_order"
            }
        )
        .sort_values(
            [
                "company_id",
                "_save_order",
            ]
        )
        .drop_duplicates(
            subset=[
                "company_id",
                "year",
            ],
            keep="last",
        )
        .drop(
            columns=[
                "_save_order"
            ]
        )
    )

    # --------------------------------------------------------
    # Sort chronologically
    # --------------------------------------------------------

    result["_year_sort"] = (
        result["year"]
        .map(year_sort_key)
    )

    result = (
        result
        .sort_values(
            [
                "company_id",
                "_year_sort",
            ]
        )
        .drop(
            columns=[
                "_year_sort"
            ]
        )
    )

    result.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    logger.info(
        "Capital allocation report saved: %s",
        OUTPUT_FILE,
    )

    return result.reset_index(
        drop=True
    )


# ============================================================
# SUMMARY
# ============================================================

def print_summary(
    result,
):
    """
    Print capital allocation summary.
    """

    print(
        "\n"
        + "=" * 60
    )

    print(
        "CAPITAL ALLOCATION SUMMARY"
    )

    print(
        "=" * 60
    )

    print(
        f"Companies: "
        f"{result['company_id'].nunique()}"
    )

    print(
        f"Rows: {len(result)}"
    )

    print(
        "\nPattern distribution:"
    )

    print(
        result[
            "pattern_label"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    # --------------------------------------------------------
    # Latest year
    # --------------------------------------------------------

    valid_years = (
        result[
            "year"
        ]
        .dropna()
        .unique()
    )

    if len(valid_years):

        latest_year = sorted(
            valid_years,
            key=year_sort_key,
        )[-1]

        print(
            "\nLatest available year:"
        )

        print(
            result.loc[
                result["year"]
                == latest_year,
                "year",
            ]
            .value_counts()
            .to_string()
        )


# ============================================================
# DATA QUALITY
# ============================================================

def print_data_quality(
    result,
):
    """
    Print final data-quality statistics.
    """

    print(
        "\nRows per company:"
    )

    print(
        result.groupby(
            "company_id"
        )
        .size()
        .value_counts()
        .sort_index()
        .to_string()
    )

    print(
        "\nMissing values:"
    )

    print(
        result.isna()
        .sum()
        .to_string()
    )


# ============================================================
# FINAL VALIDATION
# ============================================================

def final_validation(
    master_ids,
):
    """
    Reload saved CSV and validate exactly what was written.
    """

    saved = pd.read_csv(
        OUTPUT_FILE
    )

    saved["company_id"] = (
        saved["company_id"]
        .apply(clean_company_id)
    )

    saved["year"] = (
        saved["year"]
        .apply(normalize_year)
    )

    final_duplicates = int(
        saved.duplicated(
            [
                "company_id",
                "year",
            ]
        ).sum()
    )

    final_companies = (
        saved[
            "company_id"
        ]
        .nunique()
    )

    missing_final = sorted(
        set(master_ids)
        - set(
            saved[
                "company_id"
            ]
            .dropna()
            .unique()
        )
    )

    print(
        "\n"
        + "=" * 60
    )

    print(
        "FINAL OUTPUT VALIDATION"
    )

    print(
        "=" * 60
    )

    print(
        f"Companies: {final_companies}"
    )

    print(
        f"Rows: {len(saved)}"
    )

    print(
        "Duplicate company-year rows: "
        f"{final_duplicates}"
    )

    if missing_final:

        print(
            "FAIL: Missing companies:",
            missing_final,
        )

    else:

        print(
            "PASS: All 92 master companies present."
        )

    if final_duplicates:

        print(
            "FAIL: Duplicate "
            "company-year rows remain."
        )

    else:

        print(
            "PASS: No duplicate "
            "company-year rows."
        )

    # --------------------------------------------------------
    # TCS sanity check
    # --------------------------------------------------------

    tcs = saved[
        saved["company_id"]
        == "TCS"
    ]

    if not tcs.empty:

        print(
            "\nTCS sanity check:"
        )

        print(
            tcs[
                [
                    "company_id",
                    "year",
                    "cfo_quality",
                    "pattern_label",
                ]
            ]
            .to_string(
                index=False
            )
        )

    # --------------------------------------------------------
    # ATGL sanity check
    # --------------------------------------------------------

    atgl = saved[
        saved["company_id"]
        == "ATGL"
    ]

    if not atgl.empty:

        print(
            "\nATGL sanity check:"
        )

        print(
            atgl.to_string(
                index=False
            )
        )

    print(
        "\nOutput:"
    )

    print(
        OUTPUT_FILE
    )

    return (
        not missing_final
        and final_duplicates == 0
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=" * 60
    )

    print(
        "CAPITAL ALLOCATION MODULE"
    )

    print(
        "=" * 60
    )

    # --------------------------------------------------------
    # MASTER
    # --------------------------------------------------------

    master = (
        load_master_companies()
    )

    master_ids = set(
        master[
            "company_id"
        ]
    )

    # --------------------------------------------------------
    # CASHFLOW
    # --------------------------------------------------------

    cashflow = load_cashflow(
        master_ids
    )

    # --------------------------------------------------------
    # P&L
    # --------------------------------------------------------

    pnl = load_profit_loss(
        master_ids
    )

    # --------------------------------------------------------
    # Merge cashflow and P&L without dropping rows that exist
    # in either source.
    # --------------------------------------------------------

    combined = pd.merge(
        cashflow,
        pnl[
            [
                "company_id",
                "year",
                "net_profit",
            ]
        ],
        on=[
            "company_id",
            "year",
        ],
        how="outer",
        validate="one_to_one",
    )

    # --------------------------------------------------------
    # Ensure columns exist
    # --------------------------------------------------------

    for column in [
        "cfo",
        "cfi",
        "cff",
        "net_profit",
    ]:

        if column not in combined.columns:
            combined[column] = np.nan

    combined["company_id"] = (
        combined["company_id"]
        .apply(clean_company_id)
    )

    combined["year"] = (
        combined["year"]
        .apply(normalize_year)
    )

    # --------------------------------------------------------
    # Deduplicate merged dataset
    # --------------------------------------------------------

    combined = deduplicate_company_year(
        combined,
        "combined financial dataset",
    )

    # --------------------------------------------------------
    # Calculate metrics
    #
    # NO SECOND P&L MERGE.
    # --------------------------------------------------------

    result = calculate_metrics(
        combined
    )

    # --------------------------------------------------------
    # Keep only master universe
    # --------------------------------------------------------

    result = result[
        result["company_id"].isin(
            master_ids
        )
    ].copy()

    # --------------------------------------------------------
    # ADD MISSING MASTER COMPANIES
    #
    # This is what fixes ATGL disappearing.
    # --------------------------------------------------------

    result = add_missing_master_companies(
        result,
        master_ids,
    )

    # --------------------------------------------------------
    # Final validation before save
    # --------------------------------------------------------

    validation_passed = (
        validate_master_coverage(
            result,
            master_ids,
        )
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    result = save_report(
        result
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print_summary(
        result
    )

    print_data_quality(
        result
    )

    # --------------------------------------------------------
    # Reload and validate actual CSV
    # --------------------------------------------------------

    final_passed = final_validation(
        master_ids
    )

    if (
        not validation_passed
        or not final_passed
    ):

        logger.warning(
            "Final validation reported issues."
        )

    else:

        logger.info(
            "CAPITAL ALLOCATION MODULE "
            "COMPLETED SUCCESSFULLY."
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()