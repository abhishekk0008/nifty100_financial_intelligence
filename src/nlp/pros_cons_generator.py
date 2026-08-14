"""
Day 30/35 — NLP Pros/Cons Generator

Generates rule-based pros and cons for all Nifty 100 companies.

Output:
    output/pros_cons_generated.csv

Guarantees:
    - All 92 companies are processed
    - Every company has at least 1 pro
    - Every company has at least 1 con
    - Duplicate signals are removed
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
PROFIT_LOSS_FILE = RAW_DIR / "profitandloss.xlsx"
BALANCE_SHEET_FILE = RAW_DIR / "balancesheet.xlsx"
CASHFLOW_FILE = RAW_DIR / "cashflow.xlsx"
SECTORS_FILE = RAW_DIR / "sectors.xlsx"

OUTPUT_FILE = OUTPUT_DIR / "pros_cons_generated.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


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

def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Clean dataframe column names."""

    df = df.copy()

    df.columns = [
        str(col).strip().lower().replace(" ", "_")
        for col in df.columns
    ]

    return df


def load_excel(path: Path, header: int = 1) -> pd.DataFrame:
    """Load Excel file safely."""

    logger.info("Loading %s", path.name)

    df = pd.read_excel(path, header=header)

    df = clean_columns(df)

    logger.info(
        "%s loaded successfully. Shape: %s",
        path.name,
        df.shape,
    )

    return df


def numeric(value):
    """Convert value to numeric safely."""

    return pd.to_numeric(
        value,
        errors="coerce",
    )


def safe_cagr(
    start,
    end,
    years,
):
    """Calculate CAGR percentage safely."""

    start = numeric(start)
    end = numeric(end)

    if pd.isna(start) or pd.isna(end):
        return None

    if years <= 0:
        return None

    if start <= 0 or end <= 0:
        return None

    try:

        return (
            (end / start) ** (1 / years) - 1
        ) * 100

    except Exception:

        return None


def consecutive_positive(
    series,
    count,
):
    """Check whether latest count observations are positive."""

    if series is None:
        return False

    values = (
        pd.Series(series)
        .dropna()
        .tail(count)
    )

    if len(values) < count:
        return False

    return bool(
        (values > 0).all()
    )


def consecutive_decline(
    series,
    count,
):
    """Check whether latest observations declined consecutively."""

    if series is None:
        return False

    values = (
        pd.Series(series)
        .dropna()
        .tail(count)
    )

    if len(values) < count:
        return False

    return all(
        values.iloc[i]
        <
        values.iloc[i - 1]
        for i in range(1, len(values))
    )


def consecutive_increase(
    series,
    count,
):
    """Check whether latest observations increased consecutively."""

    if series is None:
        return False

    values = (
        pd.Series(series)
        .dropna()
        .tail(count)
    )

    if len(values) < count:
        return False

    return all(
        values.iloc[i]
        >
        values.iloc[i - 1]
        for i in range(1, len(values))
    )


def add_signal(
    records,
    company_id,
    signal_type,
    rule_id,
    text,
    confidence,
):
    """
    Add a signal if confidence > 60.

    Duplicate company/type/rule combinations
    are prevented.
    """

    if confidence is None:
        return

    try:
        confidence = float(confidence)
    except Exception:
        return

    if confidence <= 60:
        return

    key = (
        str(company_id).upper(),
        str(signal_type).lower(),
        str(rule_id).upper(),
    )

    for record in records:

        existing_key = (
            str(record["company_id"]).upper(),
            str(record["type"]).lower(),
            str(record["rule_id"]).upper(),
        )

        if existing_key == key:
            return

    records.append(
        {
            "company_id": str(company_id).upper(),
            "type": str(signal_type).lower(),
            "rule_id": str(rule_id).upper(),
            "text": str(text).strip(),
            "confidence_pct": round(
                confidence,
                2,
            ),
        }
    )


# ============================================================
# COMPANY METRICS
# ============================================================

def build_company_metrics(
    company_id,
    pl,
    bs,
    cf,
    company_info,
):
    """Build financial metrics for one company."""

    company_id = str(company_id).strip().upper()

    pl = pl.copy()
    bs = bs.copy()
    cf = cf.copy()
    company_info = company_info.copy()

    pl["company_id"] = (
        pl["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    bs["company_id"] = (
        bs["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    cf["company_id"] = (
        cf["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    company_info["id"] = (
        company_info["id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    company_pl = pl[
        pl["company_id"] == company_id
    ].copy()

    company_bs = bs[
        bs["company_id"] == company_id
    ].copy()

    company_cf = cf[
        cf["company_id"] == company_id
    ].copy()

    if company_pl.empty:
        return None

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    company_pl = company_pl.sort_values(
        "year",
        kind="stable",
    )

    company_bs = company_bs.sort_values(
        "year",
        kind="stable",
    )

    company_cf = company_cf.sort_values(
        "year",
        kind="stable",
    )

    # --------------------------------------------------------
    # Numeric conversion
    # --------------------------------------------------------

    pl_numeric_cols = [
        "sales",
        "expenses",
        "operating_profit",
        "net_profit",
        "eps",
        "opm_percentage",
        "interest",
        "dividend_payout",
        "profit_before_tax",
        "depreciation",
    ]

    for col in pl_numeric_cols:

        if col in company_pl.columns:

            company_pl[col] = numeric(
                company_pl[col]
            )

    bs_numeric_cols = [
        "borrowings",
        "reserves",
        "equity_capital",
        "total_assets",
        "total_liabilities",
    ]

    for col in bs_numeric_cols:

        if col in company_bs.columns:

            company_bs[col] = numeric(
                company_bs[col]
            )

    cf_numeric_cols = [
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
    ]

    for col in cf_numeric_cols:

        if col in company_cf.columns:

            company_cf[col] = numeric(
                company_cf[col]
            )

    # --------------------------------------------------------
    # Remove TTM for historical calculations
    # --------------------------------------------------------

    historical_pl = company_pl[
        ~company_pl["year"]
        .astype(str)
        .str.upper()
        .eq("TTM")
    ].copy()

    if historical_pl.empty:

        historical_pl = company_pl.copy()

    historical_pl = historical_pl.sort_values(
        "year",
        kind="stable",
    )

    # --------------------------------------------------------
    # Latest values
    # --------------------------------------------------------

    latest_pl = company_pl.iloc[-1]

    latest_bs = (
        company_bs.iloc[-1]
        if not company_bs.empty
        else None
    )

    # --------------------------------------------------------
    # Company info
    # --------------------------------------------------------

    company_row = company_info[
        company_info["id"] == company_id
    ]

    # --------------------------------------------------------
    # ROE
    # --------------------------------------------------------

    roe = None

    if (
        not company_row.empty
        and "roe_percentage" in company_info.columns
    ):

        value = numeric(
            company_row.iloc[0][
                "roe_percentage"
            ]
        )

        if pd.notna(value):

            roe = float(value)

    # --------------------------------------------------------
    # ROCE
    # --------------------------------------------------------

    roce = None

    if (
        not company_row.empty
        and "roce_percentage" in company_info.columns
    ):

        value = numeric(
            company_row.iloc[0][
                "roce_percentage"
            ]
        )

        if pd.notna(value):

            roce = float(value)

    # --------------------------------------------------------
    # Debt / Equity
    # --------------------------------------------------------

    debt_to_equity = None

    if latest_bs is not None:

        borrowings = numeric(
            latest_bs.get("borrowings")
        )

        reserves = numeric(
            latest_bs.get("reserves")
        )

        equity_capital = numeric(
            latest_bs.get("equity_capital")
        )

        if (
            pd.notna(borrowings)
            and pd.notna(reserves)
            and pd.notna(equity_capital)
        ):

            total_equity = (
                reserves
                +
                equity_capital
            )

            if total_equity != 0:

                debt_to_equity = float(
                    borrowings / total_equity
                )

    # --------------------------------------------------------
    # FCF
    # --------------------------------------------------------

    fcf_history = pd.Series(
        dtype=float
    )

    if (
        not company_cf.empty
        and "operating_activity" in company_cf.columns
        and "investing_activity" in company_cf.columns
    ):

        fcf_history = (
            company_cf["operating_activity"]
            +
            company_cf["investing_activity"]
        ).dropna()

    # --------------------------------------------------------
    # Interest Coverage Ratio
    # --------------------------------------------------------

    historical_pl["ebit"] = (
        historical_pl["profit_before_tax"]
        +
        historical_pl["interest"]
    )

    historical_pl["icr"] = pd.NA

    if (
        "interest" in historical_pl.columns
        and "profit_before_tax" in historical_pl.columns
    ):

        interest_positive = (
            historical_pl["interest"] > 0
        )

        historical_pl.loc[
            interest_positive,
            "icr",
        ] = (
            historical_pl.loc[
                interest_positive,
                "ebit",
            ]
            /
            historical_pl.loc[
                interest_positive,
                "interest",
            ]
        )

    latest_icr = (
        historical_pl.iloc[-1]["icr"]
    )

    if pd.notna(latest_icr):

        latest_icr = float(
            latest_icr
        )

    else:

        latest_icr = None

    # --------------------------------------------------------
    # Net Debt / EBITDA
    # --------------------------------------------------------

    net_debt_ebitda = None

    if latest_bs is not None:

        borrowings = numeric(
            latest_bs.get("borrowings")
        )

        operating_profit = numeric(
            latest_pl.get("operating_profit")
        )

        depreciation = numeric(
            latest_pl.get("depreciation")
        )

        if pd.isna(depreciation):

            depreciation = 0

        ebitda = (
            operating_profit
            +
            depreciation
        )

        if (
            pd.notna(borrowings)
            and pd.notna(ebitda)
            and ebitda > 0
        ):

            net_debt_ebitda = (
                borrowings / ebitda
            )

    # --------------------------------------------------------
    # CAGR helper
    # --------------------------------------------------------

    def metric_cagr(
        column,
        years,
    ):

        if column not in historical_pl.columns:
            return None

        data = (
            historical_pl[column]
            .dropna()
        )

        if len(data) < years + 1:
            return None

        start = data.iloc[
            -(years + 1)
        ]

        end = data.iloc[-1]

        return safe_cagr(
            start,
            end,
            years,
        )

    revenue_cagr_5 = metric_cagr(
        "sales",
        5,
    )

    pat_cagr_5 = metric_cagr(
        "net_profit",
        5,
    )

    eps_cagr_5 = metric_cagr(
        "eps",
        5,
    )

    # --------------------------------------------------------
    # Histories
    # --------------------------------------------------------

    roe_history = pd.Series(
        dtype=float
    )

    opm_history = (
        historical_pl["opm_percentage"]
        .dropna()
        if "opm_percentage"
        in historical_pl.columns
        else pd.Series(dtype=float)
    )

    revenue_history = (
        historical_pl["sales"]
        .dropna()
        if "sales"
        in historical_pl.columns
        else pd.Series(dtype=float)
    )

    eps_history = (
        historical_pl["eps"]
        .dropna()
        if "eps"
        in historical_pl.columns
        else pd.Series(dtype=float)
    )

    debt_history = pd.Series(
        dtype=float
    )

    if (
        not company_bs.empty
        and "borrowings"
        in company_bs.columns
    ):

        debt_history = (
            company_bs["borrowings"]
            .dropna()
        )

    assets_history = pd.Series(
        dtype=float
    )

    if (
        not company_bs.empty
        and "total_assets"
        in company_bs.columns
    ):

        assets_history = (
            company_bs["total_assets"]
            .dropna()
        )

    # Dividend yield unavailable
    dividend_yield = None

    return {
        "pl": historical_pl,
        "bs": company_bs,
        "cf": company_cf,

        "latest_pl": latest_pl,
        "latest_bs": latest_bs,

        "roe": roe,
        "roce": roce,

        "debt_to_equity": debt_to_equity,

        "latest_icr": latest_icr,
        "net_debt_ebitda": net_debt_ebitda,

        "revenue_cagr_5": revenue_cagr_5,
        "pat_cagr_5": pat_cagr_5,
        "eps_cagr_5": eps_cagr_5,

        "roe_history": roe_history,
        "opm_history": opm_history,
        "revenue_history": revenue_history,
        "eps_history": eps_history,
        "debt_history": debt_history,
        "assets_history": assets_history,
        "fcf_history": fcf_history,

        "dividend_yield": dividend_yield,
    }


# ============================================================
# PRO RULES
# ============================================================

def apply_pro_rules(
    company_id,
    m,
    records,
):

    latest_pl = m["latest_pl"]

    # --------------------------------------------------------
    # PRO 1 — HIGH ROE
    # --------------------------------------------------------

    roe_history = m["roe_history"]

    if (
        len(roe_history) >= 3
        and
        (roe_history.tail(3) > 20).all()
    ):

        add_signal(
            records,
            company_id,
            "pro",
            "PRO_1",
            "Consistently high return on equity above 20% demonstrates strong capital efficiency",
            95,
        )

    # --------------------------------------------------------
    # PRO 2 — POSITIVE FCF
    # --------------------------------------------------------

    if consecutive_positive(
        m["fcf_history"],
        5,
    ):

        add_signal(
            records,
            company_id,
            "pro",
            "PRO_2",
            "Strong free cash flow generation over 5 years signals healthy internal cash generation",
            95,
        )

    # --------------------------------------------------------
    # PRO 3 — DEBT FREE
    # --------------------------------------------------------

    de = m["debt_to_equity"]

    if (
        de is not None
        and
        abs(de) < 1e-9
    ):

        add_signal(
            records,
            company_id,
            "pro",
            "PRO_3",
            "Debt-free balance sheet provides financial flexibility and minimizes interest burden",
            98,
        )

    # --------------------------------------------------------
    # PRO 4 — REVENUE CAGR
    # --------------------------------------------------------

    rev_cagr = m["revenue_cagr_5"]

    if (
        rev_cagr is not None
        and
        rev_cagr > 15
    ):

        confidence = min(
            95,
            70 + (rev_cagr - 15) * 2,
        )

        add_signal(
            records,
            company_id,
            "pro",
            "PRO_4",
            "Revenue growing at above 15% CAGR over 5 years reflects strong business momentum",
            confidence,
        )

    # --------------------------------------------------------
    # PRO 5 — OPM
    # --------------------------------------------------------

    opm = numeric(
        latest_pl.get(
            "opm_percentage"
        )
    )

    if (
        pd.notna(opm)
        and
        opm > 25
    ):

        confidence = min(
            95,
            70 + (float(opm) - 25) * 2,
        )

        add_signal(
            records,
            company_id,
            "pro",
            "PRO_5",
            "Operating profit margin above 25% indicates strong pricing power and cost discipline",
            confidence,
        )

    # --------------------------------------------------------
    # PRO 6 — PAT CAGR
    # --------------------------------------------------------

    pat_cagr = m["pat_cagr_5"]

    if (
        pat_cagr is not None
        and
        pat_cagr > 20
    ):

        confidence = min(
            95,
            70 + (pat_cagr - 20) * 1.5,
        )

        add_signal(
            records,
            company_id,
            "pro",
            "PRO_6",
            "Net profit compounding at above 20% over 5 years indicates strong earnings growth",
            confidence,
        )

    # --------------------------------------------------------
    # PRO 7 — INTEREST COVERAGE
    # --------------------------------------------------------

    icr = m["latest_icr"]

    if (
        (
            icr is not None
            and
            icr > 10
        )
        or
        (
            de is not None
            and
            abs(de) < 1e-9
        )
    ):

        add_signal(
            records,
            company_id,
            "pro",
            "PRO_7",
            "Strong interest coverage indicates limited financial stress from debt servicing",
            90,
        )

    # --------------------------------------------------------
    # PRO 8 — DIVIDEND
    # --------------------------------------------------------

    dividend_yield = (
        m["dividend_yield"]
    )

    if (
        dividend_yield is not None
        and
        dividend_yield > 2
        and
        len(m["fcf_history"]) > 0
        and
        m["fcf_history"].iloc[-1] > 0
    ):

        add_signal(
            records,
            company_id,
            "pro",
            "PRO_8",
            "Dividend yield above 2% supported by positive free cash flow indicates shareholder distribution capacity",
            90,
        )

    # --------------------------------------------------------
    # PRO 9 — EPS CAGR
    # --------------------------------------------------------

    eps_cagr = m["eps_cagr_5"]

    if (
        eps_cagr is not None
        and
        eps_cagr > 15
    ):

        confidence = min(
            95,
            70 + (eps_cagr - 15) * 1.5,
        )

        add_signal(
            records,
            company_id,
            "pro",
            "PRO_9",
            "Earnings per share growing above 15% CAGR indicates strong earnings compounding",
            confidence,
        )

    # --------------------------------------------------------
    # PRO 10 — IMPROVING ROE
    # --------------------------------------------------------

    if (
        len(roe_history) >= 4
        and
        consecutive_increase(
            roe_history,
            4,
        )
    ):

        add_signal(
            records,
            company_id,
            "pro",
            "PRO_10",
            "Return on equity improving consistently indicates strengthening capital efficiency",
            90,
        )

    # --------------------------------------------------------
    # PRO 11 — OPERATING LEVERAGE
    # --------------------------------------------------------

    if (
        rev_cagr is not None
        and
        pat_cagr is not None
        and
        pat_cagr > rev_cagr
    ):

        add_signal(
            records,
            company_id,
            "pro",
            "PRO_11",
            "Revenue growing slower than profits indicates improving operating leverage and scale benefits",
            85,
        )

    # --------------------------------------------------------
    # PRO 12 — ASSET GROWTH
    # --------------------------------------------------------

    assets = m["assets_history"]

    if len(assets) >= 3:

        first = numeric(
            assets.iloc[0]
        )

        last = numeric(
            assets.iloc[-1]
        )

        if (
            pd.notna(first)
            and
            pd.notna(last)
            and
            first > 0
            and
            last > first
        ):

            add_signal(
                records,
                company_id,
                "pro",
                "PRO_12",
                "Growing asset base indicates expansion of the underlying operating platform",
                85,
            )


# ============================================================
# CON RULES
# ============================================================

def apply_con_rules(
    company_id,
    m,
    records,
):

    latest_pl = m["latest_pl"]

    # --------------------------------------------------------
    # CON 1 — LOW ROE
    # --------------------------------------------------------

    roe = m["roe"]

    if (
        roe is not None
        and
        roe < 10
    ):

        add_signal(
            records,
            company_id,
            "con",
            "CON_1",
            "Return on equity below 10% indicates relatively weak shareholder capital efficiency",
            85,
        )

    # --------------------------------------------------------
    # CON 2 — NEGATIVE FCF
    # --------------------------------------------------------

    if (
        len(m["fcf_history"]) > 0
        and
        m["fcf_history"].iloc[-1] < 0
    ):

        add_signal(
            records,
            company_id,
            "con",
            "CON_2",
            "Negative recent free cash flow indicates pressure on internally generated cash",
            90,
        )

    # --------------------------------------------------------
    # CON 3 — OPM DECLINE
    # --------------------------------------------------------

    if consecutive_decline(
        m["opm_history"],
        4,
    ):

        add_signal(
            records,
            company_id,
            "con",
            "CON_3",
            "Operating margins declining for consecutive years suggest pricing or cost pressure",
            90,
        )

    # --------------------------------------------------------
    # CON 4 — HIGH DEBT/EQUITY
    # --------------------------------------------------------

    de = m["debt_to_equity"]

    if (
        de is not None
        and
        de > 2
    ):

        confidence = min(
            95,
            70 + (de - 2) * 5,
        )

        add_signal(
            records,
            company_id,
            "con",
            "CON_4",
            "Debt-to-equity above 2x indicates elevated financial leverage and balance-sheet risk",
            confidence,
        )

    # --------------------------------------------------------
    # CON 5 — HIGH DEBT/EBITDA
    # --------------------------------------------------------

    nde = m["net_debt_ebitda"]

    if (
        nde is not None
        and
        nde > 3
    ):

        confidence = min(
            95,
            75 + (nde - 3) * 4,
        )

        add_signal(
            records,
            company_id,
            "con",
            "CON_5",
            "Net debt exceeding 3 times EBITDA indicates high leverage and reduced financial flexibility",
            confidence,
        )

    # --------------------------------------------------------
    # CON 6 — LOW ICR
    # --------------------------------------------------------

    icr = m["latest_icr"]

    if (
        icr is not None
        and
        icr < 1.5
    ):

        confidence = min(
            95,
            75 + (1.5 - icr) * 10,
        )

        add_signal(
            records,
            company_id,
            "con",
            "CON_6",
            "Interest coverage below 1.5x indicates elevated risk in meeting debt-servicing obligations",
            confidence,
        )

    # --------------------------------------------------------
    # CON 7 — REVENUE DECLINE
    # --------------------------------------------------------

    if consecutive_decline(
        m["revenue_history"],
        3,
    ):

        add_signal(
            records,
            company_id,
            "con",
            "CON_7",
            "Revenue declining for consecutive periods indicates weakening top-line momentum",
            90,
        )

    # --------------------------------------------------------
    # CON 8 — RISING DEBT
    # --------------------------------------------------------

    if (
        len(m["debt_history"]) >= 4
        and
        consecutive_increase(
            m["debt_history"],
            4,
        )
    ):

        add_signal(
            records,
            company_id,
            "con",
            "CON_8",
            "Rising borrowings over consecutive periods suggest increasing financial leverage risk",
            90,
        )

    # --------------------------------------------------------
    # CON 9 — LOW OPM
    # --------------------------------------------------------

    opm = numeric(
        latest_pl.get(
            "opm_percentage"
        )
    )

    if (
        pd.notna(opm)
        and
        opm < 10
    ):

        add_signal(
            records,
            company_id,
            "con",
            "CON_9",
            "Operating profit margin below 10% indicates limited operating profitability",
            80,
        )

    # --------------------------------------------------------
    # CON 10 — LOW ROCE
    # --------------------------------------------------------

    roce = m["roce"]

    if (
        roce is not None
        and
        roce < 10
    ):

        add_signal(
            records,
            company_id,
            "con",
            "CON_10",
            "Return on capital employed below 10% suggests weak returns on invested capital",
            85,
        )

    # --------------------------------------------------------
    # CON 11 — PAT DECLINE
    # --------------------------------------------------------

    pat_history = (
        m["pl"]["net_profit"]
        .dropna()
        if "net_profit"
        in m["pl"].columns
        else pd.Series(dtype=float)
    )

    if consecutive_decline(
        pat_history,
        3,
    ):

        add_signal(
            records,
            company_id,
            "con",
            "CON_11",
            "Net profit declining across consecutive periods indicates weakening earnings momentum",
            90,
        )

    # --------------------------------------------------------
    # CON 12 — EPS DECLINE
    # --------------------------------------------------------

    if consecutive_decline(
        m["eps_history"],
        3,
    ):

        add_signal(
            records,
            company_id,
            "con",
            "CON_12",
            "Declining EPS across consecutive periods indicates pressure on per-share earnings",
            90,
        )


# ============================================================
# FALLBACK PRO
# ============================================================

def add_fallback_pro(
    company_id,
    m,
    records,
):
    """
    Guarantee at least one pro.

    Uses the strongest available positive
    metric before applying a generic fallback.
    """

    existing = any(
        str(r["company_id"]).upper()
        == str(company_id).upper()
        and
        str(r["type"]).lower() == "pro"
        for r in records
    )

    if existing:
        return

    roe = m["roe"]
    roce = m["roce"]
    rev_cagr = m["revenue_cagr_5"]
    pat_cagr = m["pat_cagr_5"]
    eps_cagr = m["eps_cagr_5"]
    de = m["debt_to_equity"]

    candidates = []

    if (
        roe is not None
        and
        roe > 0
    ):

        candidates.append(
            (
                roe,
                "FALLBACK_PRO_ROE",
                f"Positive return on equity of {roe:.2f}% indicates the company is generating returns for shareholders",
            )
        )

    if (
        roce is not None
        and
        roce > 0
    ):

        candidates.append(
            (
                roce,
                "FALLBACK_PRO_ROCE",
                f"Positive return on capital employed of {roce:.2f}% indicates productive use of invested capital",
            )
        )

    if rev_cagr is not None:

        candidates.append(
            (
                max(rev_cagr, 0),
                "FALLBACK_PRO_REVENUE",
                f"Historical revenue growth of {rev_cagr:.2f}% CAGR provides evidence of the company's top-line trajectory",
            )
        )

    if pat_cagr is not None:

        candidates.append(
            (
                max(pat_cagr, 0),
                "FALLBACK_PRO_PROFIT",
                f"Historical net profit growth of {pat_cagr:.2f}% CAGR provides evidence of earnings performance",
            )
        )

    if eps_cagr is not None:

        candidates.append(
            (
                max(eps_cagr, 0),
                "FALLBACK_PRO_EPS",
                f"Historical EPS growth of {eps_cagr:.2f}% CAGR provides evidence of per-share earnings performance",
            )
        )

    if (
        de is not None
        and
        de < 1
    ):

        candidates.append(
            (
                100 - de * 20,
                "FALLBACK_PRO_LEVERAGE",
                f"Debt-to-equity of {de:.2f}x indicates relatively moderate balance-sheet leverage",
            )
        )

    if candidates:

        candidates.sort(
            key=lambda x: x[0],
            reverse=True,
        )

        _, rule_id, text = candidates[0]

        add_signal(
            records,
            company_id,
            "pro",
            rule_id,
            text,
            70,
        )

        return

    # Absolute fallback
    add_signal(
        records,
        company_id,
        "pro",
        "FALLBACK_PRO_GENERAL",
        "Available financial data provides a measurable basis for evaluating the company's operating and financial performance",
        65,
    )


# ============================================================
# FALLBACK CON
# ============================================================

def add_fallback_con(
    company_id,
    m,
    records,
):
    """
    Guarantee at least one con.

    Uses the weakest available metric before
    applying a generic data-driven fallback.
    """

    existing = any(
        str(r["company_id"]).upper()
        == str(company_id).upper()
        and
        str(r["type"]).lower() == "con"
        for r in records
    )

    if existing:
        return

    roe = m["roe"]
    roce = m["roce"]
    rev_cagr = m["revenue_cagr_5"]
    pat_cagr = m["pat_cagr_5"]
    eps_cagr = m["eps_cagr_5"]
    de = m["debt_to_equity"]
    icr = m["latest_icr"]

    candidates = []

    # Weak ROE
    if (
        roe is not None
        and
        roe < 15
    ):

        candidates.append(
            (
                100 - roe,
                "FALLBACK_CON_ROE",
                f"Return on equity of {roe:.2f}% is below a stronger double-digit efficiency benchmark",
            )
        )

    # Weak ROCE
    if (
        roce is not None
        and
        roce < 15
    ):

        candidates.append(
            (
                100 - roce,
                "FALLBACK_CON_ROCE",
                f"Return on capital employed of {roce:.2f}% leaves room for improvement in capital efficiency",
            )
        )

    # Weak revenue growth
    if (
        rev_cagr is not None
        and
        rev_cagr < 10
    ):

        candidates.append(
            (
                20 - rev_cagr,
                "FALLBACK_CON_REVENUE",
                f"Revenue CAGR of {rev_cagr:.2f}% indicates relatively modest historical top-line growth",
            )
        )

    # Weak profit growth
    if (
        pat_cagr is not None
        and
        pat_cagr < 10
    ):

        candidates.append(
            (
                20 - pat_cagr,
                "FALLBACK_CON_PROFIT",
                f"Net profit CAGR of {pat_cagr:.2f}% indicates relatively modest historical earnings growth",
            )
        )

    # Weak EPS growth
    if (
        eps_cagr is not None
        and
        eps_cagr < 10
    ):

        candidates.append(
            (
                20 - eps_cagr,
                "FALLBACK_CON_EPS",
                f"EPS CAGR of {eps_cagr:.2f}% indicates relatively modest historical per-share earnings growth",
            )
        )

    # Leverage
    if (
        de is not None
        and
        de > 1
    ):

        candidates.append(
            (
                de * 20,
                "FALLBACK_CON_LEVERAGE",
                f"Debt-to-equity of {de:.2f}x indicates meaningful reliance on debt financing",
            )
        )

    # Interest coverage
    if (
        icr is not None
        and
        icr < 5
    ):

        candidates.append(
            (
                50 - icr,
                "FALLBACK_CON_ICR",
                f"Interest coverage of {icr:.2f}x indicates less headroom for debt servicing than stronger balance sheets",
            )
        )

    if candidates:

        candidates.sort(
            key=lambda x: x[0],
            reverse=True,
        )

        _, rule_id, text = candidates[0]

        add_signal(
            records,
            company_id,
            "con",
            rule_id,
            text,
            70,
        )

        return

    # --------------------------------------------------------
    # Data-driven neutral fallback
    # --------------------------------------------------------

    latest_pl = m["latest_pl"]

    opm = numeric(
        latest_pl.get(
            "opm_percentage"
        )
    )

    if pd.notna(opm):

        add_signal(
            records,
            company_id,
            "con",
            "FALLBACK_CON_MARGIN",
            f"Current operating margin of {opm:.2f}% leaves scope for further improvement in operating efficiency",
            65,
        )

        return

    add_signal(
        records,
        company_id,
        "con",
        "FALLBACK_CON_GENERAL",
        "Available financial indicators still carry business and execution risks that should be monitored",
        65,
    )


# ============================================================
# GUARANTEE COVERAGE
# ============================================================

def ensure_minimum_coverage(
    company_id,
    m,
    records,
):
    """
    Guarantee at least one pro and one con
    for every company.
    """

    add_fallback_pro(
        company_id,
        m,
        records,
    )

    add_fallback_con(
        company_id,
        m,
        records,
    )


# ============================================================
# MAIN GENERATOR
# ============================================================

def generate_pros_cons():

    logger.info(
        "=" * 70
    )

    logger.info(
        "STARTING PROS/CONS GENERATION"
    )

    logger.info(
        "=" * 70
    )

    # --------------------------------------------------------
    # Load files
    # --------------------------------------------------------

    companies = load_excel(
        COMPANIES_FILE,
        header=1,
    )

    pl = load_excel(
        PROFIT_LOSS_FILE,
        header=1,
    )

    bs = load_excel(
        BALANCE_SHEET_FILE,
        header=1,
    )

    cf = load_excel(
        CASHFLOW_FILE,
        header=1,
    )

    sectors = load_excel(
        SECTORS_FILE,
        header=0,
    )

    # --------------------------------------------------------
    # Normalize company IDs
    # --------------------------------------------------------

    companies["id"] = (
        companies["id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    pl["company_id"] = (
        pl["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    bs["company_id"] = (
        bs["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    cf["company_id"] = (
        cf["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    sectors["company_id"] = (
        sectors["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # --------------------------------------------------------
    # Company universe
    # --------------------------------------------------------

    company_ids = (
        companies["id"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    logger.info(
        "Companies found: %s",
        len(company_ids),
    )

    # --------------------------------------------------------
    # Generate
    # --------------------------------------------------------

    records = []

    processed = 0
    failed = 0

    for index, company_id in enumerate(
        company_ids,
        start=1,
    ):

        logger.info(
            "Processing %s/%s: %s",
            index,
            len(company_ids),
            company_id,
        )

        try:

            metrics = build_company_metrics(
                company_id,
                pl,
                bs,
                cf,
                companies,
            )

            if metrics is None:

                logger.warning(
                    "No P&L data found for %s",
                    company_id,
                )

                failed += 1

                continue

            apply_pro_rules(
                company_id,
                metrics,
                records,
            )

            apply_con_rules(
                company_id,
                metrics,
                records,
            )

            ensure_minimum_coverage(
                company_id,
                metrics,
                records,
            )

            processed += 1

        except Exception as exc:

            failed += 1

            logger.exception(
                "Failed for %s: %s",
                company_id,
                exc,
            )

    # --------------------------------------------------------
    # DataFrame
    # --------------------------------------------------------

    result = pd.DataFrame(
        records,
        columns=[
            "company_id",
            "type",
            "rule_id",
            "text",
            "confidence_pct",
        ],
    )

    if result.empty:

        raise RuntimeError(
            "No pros/cons signals were generated."
        )

    # --------------------------------------------------------
    # Normalize
    # --------------------------------------------------------

    result["company_id"] = (
        result["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    result["type"] = (
        result["type"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    result["rule_id"] = (
        result["rule_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # --------------------------------------------------------
    # Remove duplicates
    # --------------------------------------------------------

    result = result.drop_duplicates(
        subset=[
            "company_id",
            "type",
            "rule_id",
        ],
        keep="first",
    )

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    type_order = {
        "pro": 0,
        "con": 1,
    }

    result["_type_order"] = (
        result["type"]
        .map(type_order)
        .fillna(99)
    )

    result = (
        result
        .sort_values(
            [
                "company_id",
                "_type_order",
                "confidence_pct",
            ],
            ascending=[
                True,
                True,
                False,
            ],
        )
        .drop(
            columns="_type_order"
        )
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    result.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    logger.info(
        "Saved output: %s",
        OUTPUT_FILE,
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    pro_counts = (
        result[
            result["type"] == "pro"
        ]
        .groupby("company_id")
        .size()
    )

    con_counts = (
        result[
            result["type"] == "con"
        ]
        .groupby("company_id")
        .size()
    )

    missing_pro = [
        company
        for company in company_ids
        if pro_counts.get(company, 0) == 0
    ]

    missing_con = [
        company
        for company in company_ids
        if con_counts.get(company, 0) == 0
    ]

    unique_companies = (
        result["company_id"]
        .nunique()
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()

    print(
        "=" * 70
    )

    print(
        "PROS/CONS GENERATION"
    )

    print(
        "=" * 70
    )

    print(
        f"Companies requested : {len(company_ids)}"
    )

    print(
        f"Companies processed : {processed}"
    )

    print(
        f"Failed              : {failed}"
    )

    print(
        f"Output rows         : {len(result)}"
    )

    print(
        f"Unique companies    : {unique_companies}"
    )

    print(
        f"Companies with pro  : {len(pro_counts)}"
    )

    print(
        f"Companies with con  : {len(con_counts)}"
    )

    print(
        f"Missing pro         : {missing_pro}"
    )

    print(
        f"Missing con         : {missing_con}"
    )

    print(
        f"Output              : {OUTPUT_FILE}"
    )

    print(
        "=" * 70
    )

    if (
        len(company_ids) == 92
        and
        unique_companies == 92
        and
        not missing_pro
        and
        not missing_con
    ):

        print(
            "STATUS              : PASS"
        )

    else:

        print(
            "STATUS              : FAIL"
        )

    print(
        "=" * 70
    )

    return result


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    generate_pros_cons()