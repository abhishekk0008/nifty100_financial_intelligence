"""
Company Tearsheet Generator
Day 33 - Nifty 100 Financial Intelligence Platform

Generates a 2-page PDF tearsheet for one or more companies.

Page 1:
    - Navy header
    - 6 KPI tiles
    - 10-year Revenue / Net Profit bar chart
    - ROE / ROCE dual-axis line chart

Page 2:
    - Balance Sheet composition stacked bar
    - Latest-year Cash Flow waterfall
    - Pros
    - Cons
    - Capital Allocation badge

Usage:
    python src/reporting/tearsheet.py TCS
    python src/reporting/tearsheet.py TCS HDFCBANK RELIANCE SUNPHARMA TATASTEEL

If no ticker is supplied, the five Day-33 test companies are generated.
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ============================================================
# CONFIGURATION
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT_DIR / "data" / "raw"
REPORT_DIR = ROOT_DIR / "reports" / "tearsheets"
TEMP_DIR = ROOT_DIR / "reports" / "_tearsheet_tmp"

REPORT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

COMPANIES_FILE = DATA_DIR / "companies.xlsx"
PNL_FILE = DATA_DIR / "profitandloss.xlsx"
BALANCE_SHEET_FILE = DATA_DIR / "balancesheet.xlsx"
CASHFLOW_FILE = DATA_DIR / "cashflow.xlsx"

CAPITAL_ALLOCATION_FILE = (
    ROOT_DIR / "reports" / "capital_allocation.csv"
)

FINANCIAL_RATIOS_FILE = (
    DATA_DIR / "financial_ratios.xlsx"
)

PROS_CONS_FILE = (
    DATA_DIR / "prosandcons.xlsx"
)

PAGE_WIDTH, PAGE_HEIGHT = A4

LEFT_MARGIN = 0.9 * cm
RIGHT_MARGIN = 0.9 * cm
TOP_MARGIN = 0.8 * cm
BOTTOM_MARGIN = 0.8 * cm

CONTENT_WIDTH = (
    PAGE_WIDTH
    - LEFT_MARGIN
    - RIGHT_MARGIN
)

CONTENT_HEIGHT = (
    PAGE_HEIGHT
    - TOP_MARGIN
    - BOTTOM_MARGIN
)

NAVY = colors.HexColor("#0B1F3A")
NAVY_LIGHT = colors.HexColor("#17365D")

GREEN = colors.HexColor("#198754")
RED = colors.HexColor("#C62828")

LIGHT_GREEN = colors.HexColor("#EAF7EE")
LIGHT_RED = colors.HexColor("#FDECEC")
LIGHT_GREY = colors.HexColor("#F4F6F8")
MID_GREY = colors.HexColor("#D9DEE5")
DARK_GREY = colors.HexColor("#4B5563")

WHITE = colors.white
BLACK = colors.HexColor("#111827")

TEST_COMPANIES = [
    "TCS",
    "HDFCBANK",
    "RELIANCE",
    "SUNPHARMA",
    "TATASTEEL",
]


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# GENERAL HELPERS
# ============================================================

def normalize_column_name(value: object) -> str:
    """Normalize a dataframe column name."""

    text = str(value).strip().lower()

    text = re.sub(
        r"[^a-z0-9]+",
        "_",
        text,
    )

    return text.strip("_")


def normalize_company_id(value: object) -> str:
    """Normalize a company identifier."""

    if pd.isna(value):
        return ""

    text = str(value).strip().upper()

    if text.endswith(".0"):
        text = text[:-2]

    return text


def clean_text(value: object) -> str:
    """Convert a value to safe display text."""

    if pd.isna(value):
        return ""

    text = str(value).strip()

    if text.lower() in {
        "nan",
        "none",
        "null",
    }:
        return ""

    return text


def find_column(
    df: pd.DataFrame,
    candidates: Iterable[str],
    required: bool = True,
) -> str | None:
    """Find a dataframe column using normalized names."""

    normalized = {
        normalize_column_name(column): column
        for column in df.columns
    }

    candidate_names = [
        normalize_column_name(candidate)
        for candidate in candidates
    ]

    for candidate in candidate_names:

        if candidate in normalized:
            return normalized[candidate]

    if required:

        raise KeyError(
            f"Could not find any of {list(candidates)}. "
            f"Available columns: {list(df.columns)}"
        )

    return None


def find_header_row(
    file_path: Path,
    required_columns: Iterable[str],
    max_rows: int = 5,
) -> int:
    """Detect Excel header row."""

    required = {
        normalize_column_name(column)
        for column in required_columns
    }

    for header_row in range(max_rows):

        try:

            preview = pd.read_excel(
                file_path,
                header=header_row,
                nrows=2,
            )

        except Exception:

            continue

        available = {
            normalize_column_name(column)
            for column in preview.columns
        }

        if required.intersection(available):

            logger.info(
                "%s detected header row: %s",
                file_path.name,
                header_row,
            )

            return header_row

    logger.warning(
        "%s header row could not be confidently detected. "
        "Using header=1.",
        file_path.name,
    )

    return 1


def read_excel_flexible(
    file_path: Path,
    required_columns: Iterable[str],
) -> pd.DataFrame:
    """Read Excel file with automatic header detection."""

    if not file_path.exists():

        logger.warning(
            "File not found: %s",
            file_path,
        )

        return pd.DataFrame()

    header_row = find_header_row(
        file_path,
        required_columns,
    )

    df = pd.read_excel(
        file_path,
        header=header_row,
    )

    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    return df


def numeric_series(
    df: pd.DataFrame,
    column: str | None,
) -> pd.Series:
    """Return numeric series safely."""

    if column is None:

        return pd.Series(
            np.nan,
            index=df.index,
            dtype="float64",
        )

    return pd.to_numeric(
        df[column],
        errors="coerce",
    )


def format_number(value: object) -> str:
    """Format financial values compactly."""

    if value is None or pd.isna(value):
        return "N/A"

    value = float(value)

    absolute = abs(value)

    if absolute >= 1_000_000:

        return f"{value / 1_000_000:.1f}M"

    if absolute >= 1_000:

        return f"{value / 1_000:.1f}K"

    if absolute >= 100:

        return f"{value:,.0f}"

    return f"{value:,.1f}"


def format_percent(value: object) -> str:
    """Format percentage values."""

    if value is None or pd.isna(value):
        return "N/A"

    return f"{float(value):.1f}%"


def extract_year(value: object) -> float:
    """Extract year from values such as Mar 2024 or FY2024."""

    if pd.isna(value):
        return np.nan

    match = re.search(
        r"(19|20)\d{2}",
        str(value),
    )

    if not match:
        return np.nan

    return float(match.group())


def filter_company(
    df: pd.DataFrame,
    company_id: str,
) -> pd.DataFrame:
    """Filter dataframe to one company."""

    if df.empty:
        return df.copy()

    company_column = find_column(
        df,
        [
            "company_id",
            "companyid",
            "id",
            "symbol",
        ],
        required=False,
    )

    if company_column is None:
        return pd.DataFrame()

    result = df.copy()

    result["_company_normalized"] = (
        result[company_column]
        .apply(normalize_company_id)
    )

    result = result[
        result["_company_normalized"]
        == normalize_company_id(company_id)
    ].copy()

    return result.drop(
        columns=["_company_normalized"],
        errors="ignore",
    )


# ============================================================
# DATA LOADERS
# ============================================================

def load_companies() -> pd.DataFrame:
    """Load master company data."""

    df = read_excel_flexible(
        COMPANIES_FILE,
        [
            "id",
            "company_id",
            "company_name",
        ],
    )

    if df.empty:
        return df

    id_column = find_column(
        df,
        [
            "id",
            "company_id",
            "symbol",
        ],
    )

    name_column = find_column(
        df,
        [
            "company_name",
            "name",
        ],
    )

    result = pd.DataFrame(
        {
            "company_id": df[id_column].apply(
                normalize_company_id
            ),
            "company_name": df[name_column].apply(
                clean_text
            ),
        }
    )

    return result.drop_duplicates(
        "company_id"
    )


def load_pnl() -> pd.DataFrame:
    """Load profit and loss data."""

    return read_excel_flexible(
        PNL_FILE,
        [
            "company_id",
            "sales",
            "net_profit",
        ],
    )


def load_balance_sheet() -> pd.DataFrame:
    """Load balance sheet data."""

    return read_excel_flexible(
        BALANCE_SHEET_FILE,
        [
            "company_id",
            "borrowings",
        ],
    )


def load_cashflow() -> pd.DataFrame:
    """Load cash flow data."""

    return read_excel_flexible(
        CASHFLOW_FILE,
        [
            "company_id",
            "operating_activity",
            "investing_activity",
            "financing_activity",
            "net_cash_flow",
        ],
    )


def load_capital_allocation() -> pd.DataFrame:
    """Load capital allocation report."""

    if not CAPITAL_ALLOCATION_FILE.exists():

        logger.warning(
            "Capital allocation file not found: %s",
            CAPITAL_ALLOCATION_FILE,
        )

        return pd.DataFrame()

    return pd.read_csv(
        CAPITAL_ALLOCATION_FILE
    )


def load_financial_ratios() -> pd.DataFrame:
    """Load financial ratio data."""

    if not FINANCIAL_RATIOS_FILE.exists():

        logger.warning(
            "Financial ratios file not found: %s",
            FINANCIAL_RATIOS_FILE,
        )

        return pd.DataFrame()

    return read_excel_flexible(
        FINANCIAL_RATIOS_FILE,
        [
            "company_id",
            "roe",
            "roce",
        ],
    )


def load_pros_cons() -> pd.DataFrame:
    """Load pros and cons data."""

    if not PROS_CONS_FILE.exists():

        logger.warning(
            "Pros/cons file not found: %s",
            PROS_CONS_FILE,
        )

        return pd.DataFrame()

    return read_excel_flexible(
        PROS_CONS_FILE,
        [
            "company_id",
            "pros",
            "cons",
        ],
    )


# ============================================================
# DATA PREPARATION
# ============================================================

def get_company_name(
    companies: pd.DataFrame,
    company_id: str,
) -> str:
    """Return company display name."""

    if companies.empty:
        return company_id

    match = companies[
        companies["company_id"]
        == normalize_company_id(company_id)
    ]

    if match.empty:
        return company_id

    name = clean_text(
        match.iloc[0]["company_name"]
    )

    return name or company_id


def get_pnl_data(
    pnl: pd.DataFrame,
    company_id: str,
) -> pd.DataFrame:
    """Prepare P&L data."""

    result = filter_company(
        pnl,
        company_id,
    )

    if result.empty:
        return result

    year_column = find_column(
        result,
        [
            "year",
            "financial_year",
        ],
        required=False,
    )

    sales_column = find_column(
        result,
        [
            "sales",
            "revenue",
            "total_revenue",
        ],
        required=False,
    )

    profit_column = find_column(
        result,
        [
            "net_profit",
            "net_profit_after_tax",
            "profit_after_tax",
        ],
        required=False,
    )

    if year_column is None:
        return pd.DataFrame()

    result = result.copy()

    result["_year"] = (
        result[year_column]
        .apply(extract_year)
    )

    result["_revenue"] = numeric_series(
        result,
        sales_column,
    )

    result["_net_profit"] = numeric_series(
        result,
        profit_column,
    )

    result = result[
        result["_year"].notna()
    ]

    return (
        result
        .sort_values("_year")
        .drop_duplicates(
            "_year",
            keep="last",
        )
    )


def get_ratio_data(
    ratios: pd.DataFrame,
    company_id: str,
) -> pd.DataFrame:
    """Prepare ROE and ROCE data."""

    result = filter_company(
        ratios,
        company_id,
    )

    if result.empty:
        return result

    year_column = find_column(
        result,
        [
            "year",
            "financial_year",
        ],
        required=False,
    )

    roe_column = find_column(
        result,
        [
            "roe",
            "roe_percentage",
            "return_on_equity",
            "return_on_equity_percentage",
        ],
        required=False,
    )

    roce_column = find_column(
        result,
        [
            "roce",
            "roce_percentage",
            "return_on_capital_employed",
        ],
        required=False,
    )

    if year_column is None:
        return pd.DataFrame()

    result = result.copy()

    result["_year"] = (
        result[year_column]
        .apply(extract_year)
    )

    result["_roe"] = numeric_series(
        result,
        roe_column,
    )

    result["_roce"] = numeric_series(
        result,
        roce_column,
    )

    result = result[
        result["_year"].notna()
    ]

    return (
        result
        .sort_values("_year")
        .drop_duplicates(
            "_year",
            keep="last",
        )
    )


def get_balance_data(
    balance_sheet: pd.DataFrame,
    company_id: str,
) -> pd.DataFrame:
    """Prepare balance sheet composition."""

    result = filter_company(
        balance_sheet,
        company_id,
    )

    if result.empty:
        return result

    year_column = find_column(
        result,
        [
            "year",
            "financial_year",
        ],
        required=False,
    )

    if year_column is None:
        return pd.DataFrame()

    equity_capital = find_column(
        result,
        [
            "equity_capital",
            "equity",
            "shareholders_equity",
        ],
        required=False,
    )

    reserves = find_column(
        result,
        [
            "reserves",
            "reserves_surplus",
            "reserves_and_surplus",
        ],
        required=False,
    )

    borrowings = find_column(
        result,
        [
            "borrowings",
            "total_borrowings",
            "debt",
        ],
        required=False,
    )

    other_liabilities = find_column(
        result,
        [
            "other_liabilities",
            "other_liability",
            "other_liabilities_provisions",
        ],
        required=False,
    )

    result = result.copy()

    result["_year"] = (
        result[year_column]
        .apply(extract_year)
    )

    result["_equity"] = (
        numeric_series(
            result,
            equity_capital,
        ).fillna(0)
        +
        numeric_series(
            result,
            reserves,
        ).fillna(0)
    )

    result["_borrowings"] = numeric_series(
        result,
        borrowings,
    ).fillna(0)

    result["_other_liabilities"] = (
        numeric_series(
            result,
            other_liabilities,
        )
    )

    if result["_other_liabilities"].isna().all():

        total_liabilities_column = find_column(
            result,
            [
                "total_liabilities",
                "liabilities",
            ],
            required=False,
        )

        if total_liabilities_column:

            total_liabilities = numeric_series(
                result,
                total_liabilities_column,
            )

            result["_other_liabilities"] = (
                total_liabilities
                - result["_equity"]
                - result["_borrowings"]
            )

    result["_other_liabilities"] = (
        result["_other_liabilities"]
        .fillna(0)
        .clip(lower=0)
    )

    result = result[
        result["_year"].notna()
    ]

    return (
        result
        .sort_values("_year")
        .drop_duplicates(
            "_year",
            keep="last",
        )
    )


def get_cashflow_data(
    cashflow: pd.DataFrame,
    company_id: str,
) -> pd.DataFrame:
    """Prepare cash flow data."""

    result = filter_company(
        cashflow,
        company_id,
    )

    if result.empty:
        return result

    year_column = find_column(
        result,
        [
            "year",
            "financial_year",
        ],
        required=False,
    )

    cfo_column = find_column(
        result,
        [
            "operating_activity",
            "cash_from_operating_activity",
            "cfo",
        ],
        required=False,
    )

    cfi_column = find_column(
        result,
        [
            "investing_activity",
            "cash_from_investing_activity",
            "cfi",
        ],
        required=False,
    )

    cff_column = find_column(
        result,
        [
            "financing_activity",
            "cash_from_financing_activity",
            "cff",
        ],
        required=False,
    )

    net_column = find_column(
        result,
        [
            "net_cash_flow",
            "net_cash",
        ],
        required=False,
    )

    if year_column is None:
        return pd.DataFrame()

    result = result.copy()

    result["_year"] = (
        result[year_column]
        .apply(extract_year)
    )

    result["_cfo"] = numeric_series(
        result,
        cfo_column,
    )

    result["_cfi"] = numeric_series(
        result,
        cfi_column,
    )

    result["_cff"] = numeric_series(
        result,
        cff_column,
    )

    result["_net_cash_flow"] = numeric_series(
        result,
        net_column,
    )

    result = result[
        result["_year"].notna()
    ]

    return (
        result
        .sort_values("_year")
        .drop_duplicates(
            "_year",
            keep="last",
        )
    )


# ============================================================
# KPI CALCULATION
# ============================================================

def latest_numeric(
    df: pd.DataFrame,
    column: str,
) -> float:
    """Get latest non-null numeric value."""

    if df.empty or column not in df:
        return np.nan

    series = pd.to_numeric(
        df[column],
        errors="coerce",
    ).dropna()

    if series.empty:
        return np.nan

    return float(series.iloc[-1])


def calculate_kpis(
    pnl: pd.DataFrame,
    ratios: pd.DataFrame,
    cashflow: pd.DataFrame,
) -> dict[str, tuple[str, str]]:
    """Calculate six KPI values."""

    revenue = latest_numeric(
        pnl,
        "_revenue",
    )

    net_profit = latest_numeric(
        pnl,
        "_net_profit",
    )

    roe = latest_numeric(
        ratios,
        "_roe",
    )

    roce = latest_numeric(
        ratios,
        "_roce",
    )

    fcf = np.nan

    if not cashflow.empty:

        cfo = latest_numeric(
            cashflow,
            "_cfo",
        )

        cfi = latest_numeric(
            cashflow,
            "_cfi",
        )

        if (
            not pd.isna(cfo)
            and not pd.isna(cfi)
        ):

            fcf = cfo + cfi

    years = (
        str(
            int(
                pnl["_year"].nunique()
            )
        )
        if not pnl.empty
        else "N/A"
    )

    return {
        "Revenue": (
            format_number(revenue),
            "Latest available",
        ),
        "Net Profit": (
            format_number(net_profit),
            "Latest available",
        ),
        "ROE": (
            format_percent(roe),
            "Return on equity",
        ),
        "ROCE": (
            format_percent(roce),
            "Return on capital",
        ),
        "Free Cash Flow": (
            format_number(fcf),
            "CFO + CFI",
        ),
        "Years Covered": (
            years,
            "Historical records",
        ),
    }


# ============================================================
# PROS / CONS
# ============================================================

def extract_pros_cons(
    pros_cons: pd.DataFrame,
    company_id: str,
) -> tuple[list[str], list[str]]:
    """Extract source pros and cons."""

    if pros_cons.empty:
        return [], []

    result = filter_company(
        pros_cons,
        company_id,
    )

    if result.empty:
        return [], []

    pros_column = find_column(
        result,
        [
            "pros",
            "pro",
            "advantages",
            "strengths",
        ],
        required=False,
    )

    cons_column = find_column(
        result,
        [
            "cons",
            "con",
            "disadvantages",
            "weaknesses",
        ],
        required=False,
    )

    pros: list[str] = []
    cons: list[str] = []

    if pros_column:

        for value in result[
            pros_column
        ].dropna():

            text = clean_text(value)

            if text:

                parts = re.split(
                    r"\n|;|\|",
                    text,
                )

                pros.extend(
                    [
                        part.strip()
                        for part in parts
                        if part.strip()
                    ]
                )

    if cons_column:

        for value in result[
            cons_column
        ].dropna():

            text = clean_text(value)

            if text:

                parts = re.split(
                    r"\n|;|\|",
                    text,
                )

                cons.extend(
                    [
                        part.strip()
                        for part in parts
                        if part.strip()
                    ]
                )

    return (
        list(dict.fromkeys(pros))[:5],
        list(dict.fromkeys(cons))[:5],
    )


def generate_fallback_pros_cons(
    pnl: pd.DataFrame,
    cashflow: pd.DataFrame,
    ratios: pd.DataFrame,
) -> tuple[list[str], list[str]]:
    """Generate conservative observations."""

    pros: list[str] = []
    cons: list[str] = []

    if not pnl.empty and len(pnl) >= 2:

        revenue_first = pnl[
            "_revenue"
        ].iloc[0]

        revenue_last = pnl[
            "_revenue"
        ].iloc[-1]

        if (
            pd.notna(revenue_first)
            and pd.notna(revenue_last)
            and revenue_last > revenue_first
        ):

            pros.append(
                "Revenue has increased over the available historical period."
            )

        profit_first = pnl[
            "_net_profit"
        ].iloc[0]

        profit_last = pnl[
            "_net_profit"
        ].iloc[-1]

        if (
            pd.notna(profit_first)
            and pd.notna(profit_last)
            and profit_last > profit_first
        ):

            pros.append(
                "Net profit has improved over the available historical period."
            )

    if not ratios.empty:

        latest_roe = latest_numeric(
            ratios,
            "_roe",
        )

        latest_roce = latest_numeric(
            ratios,
            "_roce",
        )

        if (
            pd.notna(latest_roe)
            and latest_roe > 15
        ):

            pros.append(
                "Latest ROE is above 15%."
            )

        if (
            pd.notna(latest_roce)
            and latest_roce > 15
        ):

            pros.append(
                "Latest ROCE is above 15%."
            )

    if not cashflow.empty:

        latest_cfo = latest_numeric(
            cashflow,
            "_cfo",
        )

        latest_cfi = latest_numeric(
            cashflow,
            "_cfi",
        )

        if (
            pd.notna(latest_cfo)
            and latest_cfo > 0
        ):

            pros.append(
                "Latest operating cash flow is positive."
            )

        if (
            pd.notna(latest_cfo)
            and pd.notna(latest_cfi)
        ):

            latest_fcf = (
                latest_cfo
                + latest_cfi
            )

            if latest_fcf < 0:

                cons.append(
                    "Latest free cash flow is negative."
                )

    if not cons:

        cons.append(
            "Review leverage, capital expenditure and cash-flow trends before drawing investment conclusions."
        )

    if not pros:

        pros.append(
            "Financial history is available for analytical review."
        )

    return (
        pros[:5],
        cons[:5],
    )


# ============================================================
# CAPITAL ALLOCATION
# ============================================================

def get_capital_allocation_label(
    capital_allocation: pd.DataFrame,
    company_id: str,
) -> str:
    """Get latest capital allocation classification."""

    if capital_allocation.empty:
        return "Unknown"

    result = filter_company(
        capital_allocation,
        company_id,
    )

    if result.empty:
        return "Unknown"

    year_column = find_column(
        result,
        [
            "year",
            "financial_year",
        ],
        required=False,
    )

    label_column = find_column(
        result,
        [
            "pattern_label",
            "capital_allocation",
            "capital_allocation_label",
        ],
        required=False,
    )

    if label_column is None:
        return "Unknown"

    if year_column:

        result = result.copy()

        result["_year_num"] = (
            result[
                year_column
            ].apply(extract_year)
        )

        result = result.sort_values(
            "_year_num",
            na_position="first",
        )

    labels = result[
        label_column
    ].dropna()

    if labels.empty:
        return "Unknown"

    return (
        clean_text(
            labels.iloc[-1]
        )
        or "Unknown"
    )


# ============================================================
# CHART HELPERS
# ============================================================

def save_empty_message(
    ax,
    message: str,
) -> None:
    """Draw empty chart message."""

    ax.text(
        0.5,
        0.5,
        message,
        ha="center",
        va="center",
        fontsize=10,
    )

    ax.axis("off")


def save_revenue_profit_chart(
    pnl: pd.DataFrame,
    company_id: str,
) -> Path:
    """Create revenue/net profit chart."""

    output = (
        TEMP_DIR
        / f"{company_id}_revenue_profit.png"
    )

    data = pnl.tail(10).copy()

    fig, ax = plt.subplots(
        figsize=(10, 3.1),
        dpi=180,
    )

    if data.empty:

        save_empty_message(
            ax,
            "No P&L data available",
        )

    else:

        x = np.arange(
            len(data)
        )

        width = 0.36

        ax.bar(
            x - width / 2,
            data[
                "_revenue"
            ].fillna(0),
            width,
            label="Revenue",
        )

        ax.bar(
            x + width / 2,
            data[
                "_net_profit"
            ].fillna(0),
            width,
            label="Net Profit",
        )

        ax.set_xticks(x)

        ax.set_xticklabels(
            [
                str(int(year))
                for year in data["_year"]
            ],
            fontsize=7,
        )

        ax.set_ylabel(
            "Amount",
            fontsize=8,
        )

        ax.set_title(
            "10-Year Revenue and Net Profit",
            fontsize=10,
            fontweight="bold",
        )

        ax.grid(
            axis="y",
            alpha=0.2,
        )

        ax.legend(
            fontsize=7,
            frameon=False,
        )

        ax.tick_params(
            axis="y",
            labelsize=7,
        )

    fig.tight_layout()

    fig.savefig(
        output,
        bbox_inches="tight",
    )

    plt.close(fig)

    return output


def save_roe_roce_chart(
    ratios: pd.DataFrame,
    company_id: str,
) -> Path:
    """Create ROE/ROCE chart."""

    output = (
        TEMP_DIR
        / f"{company_id}_roe_roce.png"
    )

    data = ratios.tail(10).copy()

    fig, ax1 = plt.subplots(
        figsize=(10, 2.8),
        dpi=180,
    )

    if data.empty:

        save_empty_message(
            ax1,
            "No ROE / ROCE data available",
        )

    else:

        x = np.arange(
            len(data)
        )

        ax1.plot(
            x,
            data["_roe"],
            marker="o",
            linewidth=2,
            label="ROE",
        )

        ax1.set_ylabel(
            "ROE (%)",
            fontsize=8,
        )

        ax1.set_xticks(x)

        ax1.set_xticklabels(
            [
                str(int(year))
                for year in data["_year"]
            ],
            fontsize=7,
        )

        ax2 = ax1.twinx()

        ax2.plot(
            x,
            data["_roce"],
            marker="s",
            linewidth=2,
            linestyle="--",
            label="ROCE",
        )

        ax2.set_ylabel(
            "ROCE (%)",
            fontsize=8,
        )

        ax1.set_title(
            "ROE and ROCE Trend",
            fontsize=10,
            fontweight="bold",
        )

        ax1.grid(
            axis="y",
            alpha=0.2,
        )

        lines1, labels1 = (
            ax1.get_legend_handles_labels()
        )

        lines2, labels2 = (
            ax2.get_legend_handles_labels()
        )

        ax1.legend(
            lines1 + lines2,
            labels1 + labels2,
            fontsize=7,
            frameon=False,
            loc="upper left",
        )

    fig.tight_layout()

    fig.savefig(
        output,
        bbox_inches="tight",
    )

    plt.close(fig)

    return output


def save_balance_chart(
    balance: pd.DataFrame,
    company_id: str,
) -> Path:
    """Create balance sheet composition chart."""

    output = (
        TEMP_DIR
        / f"{company_id}_balance.png"
    )

    data = balance.tail(10).copy()

    fig, ax = plt.subplots(
        figsize=(10, 3.0),
        dpi=180,
    )

    if data.empty:

        save_empty_message(
            ax,
            "No balance sheet data available",
        )

    else:

        x = np.arange(
            len(data)
        )

        equity = (
            data["_equity"]
            .fillna(0)
        )

        borrowings = (
            data["_borrowings"]
            .fillna(0)
        )

        other = (
            data[
                "_other_liabilities"
            ].fillna(0)
        )

        ax.bar(
            x,
            equity,
            label="Equity",
        )

        ax.bar(
            x,
            borrowings,
            bottom=equity,
            label="Borrowings",
        )

        ax.bar(
            x,
            other,
            bottom=(
                equity
                + borrowings
            ),
            label="Other Liabilities",
        )

        ax.set_xticks(x)

        ax.set_xticklabels(
            [
                str(int(year))
                for year in data["_year"]
            ],
            fontsize=7,
        )

        ax.set_ylabel(
            "Amount",
            fontsize=8,
        )

        ax.set_title(
            "Balance Sheet Composition",
            fontsize=10,
            fontweight="bold",
        )

        ax.legend(
            fontsize=7,
            frameon=False,
            ncol=3,
            loc="upper left",
        )

        ax.grid(
            axis="y",
            alpha=0.2,
        )

    fig.tight_layout()

    fig.savefig(
        output,
        bbox_inches="tight",
    )

    plt.close(fig)

    return output


def save_cashflow_waterfall(
    cashflow: pd.DataFrame,
    company_id: str,
) -> Path:
    """
    Create latest-year cash-flow waterfall.

    Important:
    This function always produces a finite-size PNG.
    """

    output = (
        TEMP_DIR
        / f"{company_id}_cashflow.png"
    )

    fig, ax = plt.subplots(
        figsize=(7.0, 3.2),
        dpi=180,
    )

    if cashflow.empty:

        save_empty_message(
            ax,
            "No cash flow data available",
        )

    else:

        latest = cashflow.iloc[-1]

        labels = [
            "CFO",
            "CFI",
            "CFF",
            "Net Cash Flow",
        ]

        raw_values = [
            latest["_cfo"],
            latest["_cfi"],
            latest["_cff"],
            latest["_net_cash_flow"],
        ]

        values = []

        for value in raw_values:

            if pd.isna(value):
                values.append(0.0)

            else:
                values.append(
                    float(value)
                )

        cumulative = [0.0]

        for value in values[:3]:

            cumulative.append(
                cumulative[-1] + value
            )

        starts = [
            0.0,
            cumulative[1],
            cumulative[2],
        ]

        for index in range(3):

            value = values[index]

            if value >= 0:

                bottom = starts[index]

            else:

                bottom = (
                    starts[index]
                    + value
                )

            ax.bar(
                index,
                abs(value),
                bottom=bottom,
                width=0.55,
            )

        net = values[3]

        ax.bar(
            3,
            abs(net),
            bottom=(
                0
                if net >= 0
                else net
            ),
            width=0.55,
        )

        ax.axhline(
            0,
            linewidth=0.8,
        )

        ax.set_xticks(
            range(4)
        )

        ax.set_xticklabels(
            labels,
            fontsize=8,
        )

        ax.set_title(
            "Latest-Year Cash Flow",
            fontsize=10,
            fontweight="bold",
        )

        ax.set_ylabel(
            "Amount",
            fontsize=8,
        )

        ax.grid(
            axis="y",
            alpha=0.2,
        )

    fig.tight_layout()

    fig.savefig(
        output,
        bbox_inches="tight",
    )

    plt.close(fig)

    return output


# ============================================================
# REPORTLAB STYLES
# ============================================================

def create_styles() -> dict[str, ParagraphStyle]:
    """Create ReportLab styles."""

    return {

        "header": ParagraphStyle(
            "Header",
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=19,
            textColor=WHITE,
            alignment=TA_LEFT,
        ),

        "ticker": ParagraphStyle(
            "Ticker",
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=WHITE,
            alignment=TA_RIGHT,
        ),

        "section": ParagraphStyle(
            "Section",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            textColor=NAVY,
            spaceAfter=4,
        ),

        "kpi_label": ParagraphStyle(
            "KPI_Label",
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=8,
            textColor=DARK_GREY,
            alignment=TA_CENTER,
        ),

        "kpi_value": ParagraphStyle(
            "KPI_Value",
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=15,
            textColor=NAVY,
            alignment=TA_CENTER,
        ),

        "kpi_sub": ParagraphStyle(
            "KPI_Sub",
            fontName="Helvetica",
            fontSize=6,
            leading=7,
            textColor=DARK_GREY,
            alignment=TA_CENTER,
        ),

        "body": ParagraphStyle(
            "Body",
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=BLACK,
        ),

        "bullet_green": ParagraphStyle(
            "BulletGreen",
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=BLACK,
            leftIndent=8,
            firstLineIndent=-6,
        ),

        "bullet_red": ParagraphStyle(
            "BulletRed",
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=BLACK,
            leftIndent=8,
            firstLineIndent=-6,
        ),

        "badge": ParagraphStyle(
            "Badge",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=WHITE,
            alignment=TA_CENTER,
        ),

        "small": ParagraphStyle(
            "Small",
            fontName="Helvetica",
            fontSize=6.5,
            leading=8,
            textColor=DARK_GREY,
        ),
    }


# ============================================================
# PAGE BACKGROUND
# ============================================================

def draw_page_background(
    canvas,
    doc,
) -> None:
    """Draw white background and footer."""

    canvas.saveState()

    canvas.setFillColor(
        WHITE
    )

    canvas.rect(
        0,
        0,
        PAGE_WIDTH,
        PAGE_HEIGHT,
        stroke=0,
        fill=1,
    )

    canvas.setStrokeColor(
        MID_GREY
    )

    canvas.line(
        LEFT_MARGIN,
        0.55 * cm,
        PAGE_WIDTH - RIGHT_MARGIN,
        0.55 * cm,
    )

    canvas.setFont(
        "Helvetica",
        6.5,
    )

    canvas.setFillColor(
        DARK_GREY
    )

    canvas.drawRightString(
        PAGE_WIDTH - RIGHT_MARGIN,
        0.3 * cm,
        f"Page {doc.page}",
    )

    canvas.restoreState()


# ============================================================
# REPORT ELEMENTS
# ============================================================

def build_header(
    company_name: str,
    company_id: str,
    styles: dict[str, ParagraphStyle],
) -> Table:
    """Build company header."""

    table = Table(
        [
            [
                Paragraph(
                    clean_text(
                        company_name
                    ),
                    styles["header"],
                ),
                Paragraph(
                    clean_text(
                        company_id
                    ),
                    styles["ticker"],
                ),
            ]
        ],
        colWidths=[
            CONTENT_WIDTH * 0.78,
            CONTENT_WIDTH * 0.22,
        ],
        rowHeights=[
            1.25 * cm
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    NAVY,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (0, 0),
                    10,
                ),
                (
                    "RIGHTPADDING",
                    (-1, 0),
                    (-1, 0),
                    10,
                ),
            ]
        )
    )

    return table


def build_kpi_tiles(
    kpis: dict[str, tuple[str, str]],
    styles: dict[str, ParagraphStyle],
) -> Table:
    """Build six KPI tiles."""

    items = list(
        kpis.items()
    )[:6]

    rows = []

    tile_width = (
        CONTENT_WIDTH / 3
        - 0.18 * cm
    )

    for row_index in range(2):

        row = []

        for col_index in range(3):

            index = (
                row_index * 3
                + col_index
            )

            if index >= len(items):

                row.append("")

                continue

            label, values = items[index]

            value, subtitle = values

            tile = Table(
                [
                    [
                        Paragraph(
                            clean_text(label),
                            styles["kpi_label"],
                        )
                    ],
                    [
                        Paragraph(
                            clean_text(value),
                            styles["kpi_value"],
                        )
                    ],
                    [
                        Paragraph(
                            clean_text(subtitle),
                            styles["kpi_sub"],
                        )
                    ],
                ],
                colWidths=[
                    tile_width
                ],
                rowHeights=[
                    0.38 * cm,
                    0.62 * cm,
                    0.3 * cm,
                ],
            )

            tile.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, -1),
                            LIGHT_GREY,
                        ),
                        (
                            "BOX",
                            (0, 0),
                            (-1, -1),
                            0.5,
                            MID_GREY,
                        ),
                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "MIDDLE",
                        ),
                        (
                            "LEFTPADDING",
                            (0, 0),
                            (-1, -1),
                            3,
                        ),
                        (
                            "RIGHTPADDING",
                            (0, 0),
                            (-1, -1),
                            3,
                        ),
                    ]
                )
            )

            row.append(tile)

        rows.append(row)

    outer = Table(
        rows,
        colWidths=[
            CONTENT_WIDTH / 3
        ] * 3,
        hAlign="LEFT",
    )

    outer.setStyle(
        TableStyle(
            [
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
            ]
        )
    )

    return outer


def build_bullet_section(
    title: str,
    bullets: list[str],
    green: bool,
    styles: dict[str, ParagraphStyle],
) -> Table:
    """Build pros/cons section."""

    if not bullets:

        bullets = [
            "No source observation available."
        ]

    style = (
        styles["bullet_green"]
        if green
        else styles["bullet_red"]
    )

    content = [
        Paragraph(
            clean_text(title),
            styles["section"],
        )
    ]

    for bullet in bullets[:5]:

        text = clean_text(
            bullet
        )

        if text:

            content.append(
                Paragraph(
                    f"• {text}",
                    style,
                )
            )

    table = Table(
        [
            [
                content
            ]
        ],
        colWidths=[
            CONTENT_WIDTH / 2
            - 0.15 * cm
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    (
                        LIGHT_GREEN
                        if green
                        else LIGHT_RED
                    ),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    (
                        GREEN
                        if green
                        else RED
                    ),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    return table


def build_capital_badge(
    label: str,
    styles: dict[str, ParagraphStyle],
) -> Table:
    """Build capital allocation badge."""

    normalized_label = clean_text(
        label
    )

    if normalized_label == "Reinvestor":

        badge_color = GREEN

    elif normalized_label in {
        "Growth Funded by Debt",
        "Distress Signal",
    }:

        badge_color = RED

    else:

        badge_color = NAVY_LIGHT

    badge_width = (
        CONTENT_WIDTH * 0.35
    )

    badge = Table(
        [
            [
                Paragraph(
                    normalized_label
                    or "Unknown",
                    styles["badge"],
                )
            ]
        ],
        colWidths=[
            badge_width
        ],
        rowHeights=[
            1.0 * cm
        ],
    )

    badge.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    badge_color,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
            ]
        )
    )

    return badge


# ============================================================
# SAFE IMAGE HELPER
# ============================================================

def report_image(
    path: Path,
    width: float,
    height: float,
) -> Image:
    """
    Create a ReportLab Image with explicit finite dimensions.

    This prevents ReportLab's automatic image-size calculation
    from producing the 16777215-point height seen in the
    original Day-33 error.
    """

    image = Image(
        str(path),
        width=float(width),
        height=float(height),
    )

    image.hAlign = "LEFT"

    return image


# ============================================================
# PDF GENERATION
# ============================================================

def generate_tearsheet(
    company_id: str,
    companies: pd.DataFrame,
    pnl: pd.DataFrame,
    balance_sheet: pd.DataFrame,
    cashflow: pd.DataFrame,
    ratios: pd.DataFrame,
    capital_allocation: pd.DataFrame,
    pros_cons: pd.DataFrame,
) -> Path:
    """Generate a two-page company tearsheet."""

    company_id = normalize_company_id(
        company_id
    )

    company_name = get_company_name(
        companies,
        company_id,
    )

    logger.info(
        "Generating tearsheet: %s",
        company_id,
    )

    # --------------------------------------------------------
    # Company-specific data
    # --------------------------------------------------------

    company_pnl = get_pnl_data(
        pnl,
        company_id,
    )

    company_balance = get_balance_data(
        balance_sheet,
        company_id,
    )

    company_cashflow = get_cashflow_data(
        cashflow,
        company_id,
    )

    company_ratios = get_ratio_data(
        ratios,
        company_id,
    )

    # --------------------------------------------------------
    # KPIs
    # --------------------------------------------------------

    kpis = calculate_kpis(
        company_pnl,
        company_ratios,
        company_cashflow,
    )

    # --------------------------------------------------------
    # Pros / Cons
    # --------------------------------------------------------

    source_pros, source_cons = (
        extract_pros_cons(
            pros_cons,
            company_id,
        )
    )

    if (
        not source_pros
        or not source_cons
    ):

        fallback_pros, fallback_cons = (
            generate_fallback_pros_cons(
                company_pnl,
                company_cashflow,
                company_ratios,
            )
        )

        if not source_pros:
            source_pros = fallback_pros

        if not source_cons:
            source_cons = fallback_cons

    # --------------------------------------------------------
    # Capital Allocation
    # --------------------------------------------------------

    allocation_label = (
        get_capital_allocation_label(
            capital_allocation,
            company_id,
        )
    )

    # --------------------------------------------------------
    # Charts
    # --------------------------------------------------------

    revenue_chart = (
        save_revenue_profit_chart(
            company_pnl,
            company_id,
        )
    )

    roe_chart = (
        save_roe_roce_chart(
            company_ratios,
            company_id,
        )
    )

    balance_chart = (
        save_balance_chart(
            company_balance,
            company_id,
        )
    )

    cashflow_chart = (
        save_cashflow_waterfall(
            company_cashflow,
            company_id,
        )
    )

    # --------------------------------------------------------
    # Styles
    # --------------------------------------------------------

    styles = create_styles()

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    output_file = (
        REPORT_DIR
        / f"{company_id}_tearsheet.pdf"
    )

    doc = BaseDocTemplate(
        str(output_file),
        pagesize=A4,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
        title=(
            f"{company_name} "
            f"({company_id}) Tearsheet"
        ),
        author=(
            "Nifty 100 Financial "
            "Intelligence Platform"
        ),
        allowSplitting=0,
    )

    frame = Frame(
        LEFT_MARGIN,
        BOTTOM_MARGIN,
        CONTENT_WIDTH,
        CONTENT_HEIGHT,
        id="normal",
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )

    doc.addPageTemplates(
        [
            PageTemplate(
                id="tearsheet",
                frames=[frame],
                onPage=draw_page_background,
            )
        ]
    )

    story = []

    # ========================================================
    # PAGE 1
    # ========================================================

    story.append(
        build_header(
            company_name,
            company_id,
            styles,
        )
    )

    story.append(
        Spacer(
            1,
            0.15 * cm,
        )
    )

    story.append(
        build_kpi_tiles(
            kpis,
            styles,
        )
    )

    story.append(
        Spacer(
            1,
            0.12 * cm,
        )
    )

    story.append(
        Paragraph(
            "Financial Performance",
            styles["section"],
        )
    )

    # Fixed-size image.
    story.append(
        report_image(
            revenue_chart,
            CONTENT_WIDTH,
            5.0 * cm,
        )
    )

    story.append(
        Spacer(
            1,
            0.05 * cm,
        )
    )

    story.append(
        report_image(
            roe_chart,
            CONTENT_WIDTH,
            4.5 * cm,
        )
    )

    # ========================================================
    # PAGE 2
    # ========================================================

    story.append(
        PageBreak()
    )

    story.append(
        Paragraph(
            "Balance Sheet & Cash Flow",
            styles["section"],
        )
    )

    # Balance chart
    story.append(
        report_image(
            balance_chart,
            CONTENT_WIDTH,
            4.5 * cm,
        )
    )

    story.append(
        Spacer(
            1,
            0.10 * cm,
        )
    )

    # --------------------------------------------------------
    # Cash flow + Capital Allocation
    #
    # IMPORTANT:
    # No KeepTogether.
    # No dynamically sized Image.
    # No nested image inside KeepTogether.
    # --------------------------------------------------------

    cashflow_image = report_image(
        cashflow_chart,
        CONTENT_WIDTH * 0.60,
        3.45 * cm,
    )

    capital_title = Paragraph(
        "Capital Allocation",
        styles["section"],
    )

    capital_badge = build_capital_badge(
        allocation_label,
        styles,
    )

    capital_section = Table(
        [
            [
                capital_title
            ],
            [
                Spacer(
                    1,
                    0.08 * cm,
                )
            ],
            [
                capital_badge
            ],
        ],
        colWidths=[
            CONTENT_WIDTH * 0.35
        ],
    )

    capital_section.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
            ]
        )
    )

    cashflow_and_capital = Table(
        [
            [
                cashflow_image,
                capital_section,
            ]
        ],
        colWidths=[
            CONTENT_WIDTH * 0.62,
            CONTENT_WIDTH * 0.38,
        ],
        rowHeights=[
            3.45 * cm
        ],
    )

    cashflow_and_capital.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
            ]
        )
    )

    story.append(
        cashflow_and_capital
    )

    story.append(
        Spacer(
            1,
            0.12 * cm,
        )
    )

    # --------------------------------------------------------
    # Pros / Cons
    # --------------------------------------------------------

    pros_table = build_bullet_section(
        "Pros",
        source_pros,
        True,
        styles,
    )

    cons_table = build_bullet_section(
        "Cons",
        source_cons,
        False,
        styles,
    )

    pros_cons_table = Table(
        [
            [
                pros_table,
                cons_table,
            ]
        ],
        colWidths=[
            CONTENT_WIDTH / 2,
            CONTENT_WIDTH / 2,
        ],
    )

    pros_cons_table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
            ]
        )
    )

    story.append(
        pros_cons_table
    )

    # --------------------------------------------------------
    # Build
    # --------------------------------------------------------

    doc.build(
        story
    )

    logger.info(
        "Tearsheet saved: %s",
        output_file,
    )

    return output_file


# ============================================================
# PDF VALIDATION
# ============================================================

def validate_pdf(
    pdf_path: Path,
) -> bool:
    """Validate generated PDF has exactly two pages."""

    try:

        from pypdf import PdfReader

        reader = PdfReader(
            str(pdf_path)
        )

        page_count = len(
            reader.pages
        )

        if page_count != 2:

            logger.error(
                "%s has %s pages. Expected 2.",
                pdf_path.name,
                page_count,
            )

            return False

        logger.info(
            "%s: 2-page validation PASS",
            pdf_path.name,
        )

        return True

    except ImportError:

        logger.warning(
            "pypdf is not installed. "
            "Skipping automatic page-count validation."
        )

        return True

    except Exception as exc:

        logger.error(
            "PDF validation failed for %s: %s",
            pdf_path,
            exc,
        )

        return False


# ============================================================
# BATCH GENERATION
# ============================================================

def run(
    company_ids: list[str] | None = None,
) -> None:
    """
    Day-34 batch tearsheet generation.

    If company_ids is None:
        Generate tearsheets for all companies available
        in companies.xlsx.

    Companies with fewer than 3 distinct P&L financial
    years are skipped and written to:
        output/skipped_tearsheets.csv
    """

    logger.info("Loading source datasets...")

    companies = load_companies()
    pnl = load_pnl()
    balance_sheet = load_balance_sheet()
    cashflow = load_cashflow()
    ratios = load_financial_ratios()
    capital_allocation = load_capital_allocation()
    pros_cons = load_pros_cons()

    logger.info(
        "Companies loaded: %s",
        len(companies),
    )

    # --------------------------------------------------------
    # Determine companies to process
    # --------------------------------------------------------

    if company_ids is None:

        company_ids = (
            companies["company_id"]
            .dropna()
            .astype(str)
            .map(normalize_company_id)
            .dropna()
            .unique()
            .tolist()
        )

    else:

        normalized_ids = []

        for company_id in company_ids:

            normalized = normalize_company_id(
                company_id
            )

            if normalized:
                normalized_ids.append(normalized)

        company_ids = normalized_ids

    logger.info(
        "Companies requested for batch generation: %s",
        len(company_ids),
    )

    # --------------------------------------------------------
    # Minimum-year validation
    # --------------------------------------------------------

    def has_minimum_years(
        company_id: str,
    ) -> bool:
        """
        Return True when the company has at least
        3 distinct financial years in P&L data.
        """

        company_pnl = pnl[
            pnl["company_id"]
            .astype(str)
            .str.upper()
            .eq(company_id.upper())
        ]

        if company_pnl.empty:

            logger.warning(
                "%s skipped: no P&L data found",
                company_id,
            )

            return False

        years = (
            company_pnl["year"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
        )

        year_count = len(years)

        logger.info(
            "%s: %s years of P&L data",
            company_id,
            year_count,
        )

        return year_count >= 3

    # --------------------------------------------------------
    # Output directories
    # --------------------------------------------------------

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    skipped_file = (
        ROOT_DIR
        / "output"
        / "skipped_tearsheets.csv"
    )

    skipped_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Batch generation
    # --------------------------------------------------------

    successful = 0
    failed = 0
    skipped = []

    total = len(company_ids)

    logger.info(
        "Starting batch tearsheet generation for %s companies",
        total,
    )

    for index, company_id in enumerate(
        company_ids,
        start=1,
    ):

        company_id = normalize_company_id(
            company_id
        )

        if not company_id:
            continue

        logger.info(
            "[%s/%s] Processing %s",
            index,
            total,
            company_id,
        )

        # ----------------------------------------------------
        # Minimum 3 years check
        # ----------------------------------------------------

        if not has_minimum_years(company_id):

            skipped.append(
                {
                    "ticker": company_id,
                    "reason": "Fewer than 3 years of P&L data",
                }
            )

            logger.warning(
                "[%s/%s] Skipping %s: fewer than 3 years of data",
                index,
                total,
                company_id,
            )

            continue

        # ----------------------------------------------------
        # Generate tearsheet
        # ----------------------------------------------------

        try:

            output = generate_tearsheet(
                company_id,
                companies,
                pnl,
                balance_sheet,
                cashflow,
                ratios,
                capital_allocation,
                pros_cons,
            )

            # ------------------------------------------------
            # Validate generated PDF
            # ------------------------------------------------

            if validate_pdf(output):

                successful += 1

                logger.info(
                    "[%s/%s] SUCCESS: %s",
                    index,
                    total,
                    output,
                )

            else:

                failed += 1

                logger.error(
                    "[%s/%s] PDF validation failed: %s",
                    index,
                    total,
                    company_id,
                )

        except Exception as exc:

            failed += 1

            logger.exception(
                "[%s/%s] Failed to generate %s: %s",
                index,
                total,
                company_id,
                exc,
            )

    # --------------------------------------------------------
    # Save skipped companies
    # --------------------------------------------------------

    skipped_df = pd.DataFrame(
        skipped,
        columns=[
            "ticker",
            "reason",
        ],
    )

    skipped_df.to_csv(
        skipped_file,
        index=False,
    )

    logger.info(
        "Skipped-tearsheet report saved: %s",
        skipped_file,
    )

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("DAY 34 — BATCH TEARSHEET GENERATION")
    print("=" * 70)

    print(
        f"Requested : {len(company_ids)}"
    )

    print(
        f"Successful: {successful}"
    )

    print(
        f"Skipped   : {len(skipped)}"
    )

    print(
        f"Failed    : {failed}"
    )

    print(
        f"Expected PDFs: {len(company_ids) - len(skipped)}"
    )

    print(
        f"Output    : {REPORT_DIR}"
    )

    print(
        f"Skipped CSV: {skipped_file}"
    )

    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    """
    CLI entry point.

    Usage:

        python src\\reporting\\tearsheet.py

    Generates tearsheets for all companies.

    Or:

        python src\\reporting\\tearsheet.py TCS HDFCBANK RELIANCE

    Generates only the requested companies.
    """

    if len(sys.argv) > 1:

        company_ids = [
            normalize_company_id(value)
            for value in sys.argv[1:]
        ]

        company_ids = [
            value
            for value in company_ids
            if value
        ]

    else:

        company_ids = None

    run(company_ids)


if __name__ == "__main__":
    main()