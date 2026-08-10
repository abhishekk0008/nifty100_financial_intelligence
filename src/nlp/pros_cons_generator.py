"""
Day 30 — NLP Pros/Cons Generator

Generates rule-based pros and cons for every company using
financial statement data.

Output:
output/pros_cons_generated.csv
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

    df = pd.read_excel(path, header=header)
    df = clean_columns(df)

    logger.info(
        "%s loaded successfully. Shape: %s",
        path.name,
        df.shape,
    )

    return df


def numeric(series):
    """Convert series to numeric safely."""
    return pd.to_numeric(series, errors="coerce")


def safe_cagr(start, end, years):
    """Calculate CAGR percentage safely."""

    if pd.isna(start) or pd.isna(end):
        return None

    if years <= 0:
        return None

    if start <= 0 or end <= 0:
        return None

    return ((end / start) ** (1 / years) - 1) * 100


def consecutive_positive(series, count):
    """Check whether latest count observations are positive."""

    values = series.dropna().tail(count)

    if len(values) < count:
        return False

    return bool((values > 0).all())


def consecutive_decline(series, count):
    """Check whether latest observations declined consecutively."""

    values = series.dropna().tail(count)

    if len(values) < count:
        return False

    return all(
        values.iloc[i] < values.iloc[i - 1]
        for i in range(1, len(values))
    )


def consecutive_increase(series, count):
    """Check whether latest observations increased consecutively."""

    values = series.dropna().tail(count)

    if len(values) < count:
        return False

    return all(
        values.iloc[i] > values.iloc[i - 1]
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
    Add a signal only when confidence is > 60.
    """

    if confidence <= 60:
        return

    records.append(
        {
            "company_id": company_id,
            "type": signal_type,
            "rule_id": rule_id,
            "text": text,
            "confidence_pct": round(float(confidence), 2),
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
    """Build all required metrics for one company."""

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
    # Sort data
    # --------------------------------------------------------

    company_pl = company_pl.sort_values("year")
    company_bs = company_bs.sort_values("year")
    company_cf = company_cf.sort_values("year")

    # --------------------------------------------------------
    # Numeric conversion
    # --------------------------------------------------------

    pl_numeric_cols = [
        "sales",
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
            company_pl[col] = numeric(company_pl[col])

    bs_numeric_cols = [
        "borrowings",
        "reserves",
        "equity_capital",
        "total_assets",
        "total_liabilities",
    ]

    for col in bs_numeric_cols:
        if col in company_bs.columns:
            company_bs[col] = numeric(company_bs[col])

    cf_numeric_cols = [
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
    ]

    for col in cf_numeric_cols:
        if col in company_cf.columns:
            company_cf[col] = numeric(company_cf[col])

    # --------------------------------------------------------
    # Remove TTM from historical CAGR calculations
    # --------------------------------------------------------

    historical_pl = company_pl[
        ~company_pl["year"]
        .astype(str)
        .str.upper()
        .eq("TTM")
    ].copy()

    if historical_pl.empty:
        historical_pl = company_pl.copy()

    historical_pl = historical_pl.sort_values("year")

    # --------------------------------------------------------
    # Latest year
    # --------------------------------------------------------

    latest_pl = company_pl.iloc[-1]

    latest_bs = (
        company_bs.iloc[-1]
        if not company_bs.empty
        else None
    )

    # --------------------------------------------------------
    # ROE
    # --------------------------------------------------------

    roe = None

    if "roe_percentage" in company_info.columns:

        company_row = company_info[
            company_info["id"] == company_id
        ]

        if not company_row.empty:

            value = numeric(
                company_row.iloc[0]["roe_percentage"]
            )

            if pd.notna(value):
                roe = float(value)

    # --------------------------------------------------------
    # ROCE
    # --------------------------------------------------------

    roce = None

    if "roce_percentage" in company_info.columns:

        company_row = company_info[
            company_info["id"] == company_id
        ]

        if not company_row.empty:

            value = numeric(
                company_row.iloc[0]["roce_percentage"]
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

        total_equity = reserves + equity_capital

        if (
            pd.notna(borrowings)
            and pd.notna(total_equity)
            and total_equity != 0
        ):
            debt_to_equity = float(
                borrowings / total_equity
            )

    # --------------------------------------------------------
    # FCF
    # --------------------------------------------------------

    fcf_history = pd.Series(dtype=float)

    if not company_cf.empty:

        fcf_history = (
            company_cf["operating_activity"]
            + company_cf["investing_activity"]
        ).dropna()

    # --------------------------------------------------------
    # Interest Coverage Ratio
    # --------------------------------------------------------

    historical_pl["ebit"] = (
        historical_pl["profit_before_tax"]
        + historical_pl["interest"]
    )

    historical_pl["icr"] = pd.NA

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

    latest_icr = historical_pl.iloc[-1]["icr"]

    if pd.notna(latest_icr):
        latest_icr = float(latest_icr)
    else:
        latest_icr = None

    # --------------------------------------------------------
    # Net debt / EBITDA
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
            + depreciation
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

    def metric_cagr(column, years):

        data = historical_pl[
            column
        ].dropna()

        if len(data) < years + 1:
            return None

        start = data.iloc[-(years + 1)]
        end = data.iloc[-1]

        return safe_cagr(
            float(start),
            float(end),
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

    roe_history = pd.Series(dtype=float)

    # Historical ROE is not present in supplied files.

    opm_history = historical_pl[
        "opm_percentage"
    ].dropna()

    revenue_history = historical_pl[
        "sales"
    ].dropna()

    eps_history = historical_pl[
        "eps"
    ].dropna()

    debt_history = pd.Series(dtype=float)

    if not company_bs.empty:

        debt_history = company_bs[
            "borrowings"
        ].dropna()

    assets_history = pd.Series(dtype=float)

    if not company_bs.empty:

        assets_history = company_bs[
            "total_assets"
        ].dropna()

    # Dividend yield is unavailable.
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

def apply_pro_rules(company_id, m, records):

    latest_pl = m["latest_pl"]

    # --------------------------------------------------------
    # PRO 1
    # --------------------------------------------------------

    roe_history = m["roe_history"]

    if (
        len(roe_history) >= 3
        and (roe_history.tail(3) > 20).all()
    ):

        add_signal(
            records,
            company_id,
            "pro",
            "PRO_1",
            "Consistently high return on equity above 20% demonstrates exceptional capital efficiency",
            95,
        )

    # --------------------------------------------------------
    # PRO 2
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
            "Strong free cash flow generation over 5 years signals healthy business fundamentals",
            95,
        )

    # --------------------------------------------------------
    # PRO 3
    # --------------------------------------------------------

    de = m["debt_to_equity"]

    if (
        de is not None
        and abs(de) < 1e-9
    ):

        add_signal(
            records,
            company_id,
            "pro",
            "PRO_3",
            "Debt-free balance sheet provides financial flexibility and eliminates interest burden",
            98,
        )

    # --------------------------------------------------------
    # PRO 4
    # --------------------------------------------------------

    rev_cagr = m["revenue_cagr_5"]

    if (
        rev_cagr is not None
        and rev_cagr > 15
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
    # PRO 5
    # --------------------------------------------------------

    opm = numeric(
        latest_pl.get("opm_percentage")
    )

    if (
        pd.notna(opm)
        and opm > 25
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
    # PRO 6
    # --------------------------------------------------------

    pat_cagr = m["pat_cagr_5"]

    if (
        pat_cagr is not None
        and pat_cagr > 20
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
            "Net profit compounding at above 20% over 5 years creates significant shareholder value",
            confidence,
        )

    # --------------------------------------------------------
    # PRO 7
    # --------------------------------------------------------

    icr = m["latest_icr"]

    if (
        (
            icr is not None
            and icr > 10
        )
        or
        (
            de is not None
            and abs(de) < 1e-9
        )
    ):

        add_signal(
            records,
            company_id,
            "pro",
            "PRO_7",
            "Very high interest coverage ratio reflects negligible financial stress from debt servicing",
            90,
        )

    # --------------------------------------------------------
    # PRO 8
    # --------------------------------------------------------

    dividend_yield = m["dividend_yield"]

    if (
        dividend_yield is not None
        and dividend_yield > 2
        and len(m["fcf_history"]) > 0
        and m["fcf_history"].iloc[-1] > 0
    ):

        add_signal(
            records,
            company_id,
            "pro",
            "PRO_8",
            "Consistent dividend yield above 2% backed by positive free cash flow",
            90,
        )

    # --------------------------------------------------------
    # PRO 9
    # --------------------------------------------------------

    eps_cagr = m["eps_cagr_5"]

    if (
        eps_cagr is not None
        and eps_cagr > 15
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
            "Earnings per share growing above 15% CAGR indicates strong earnings quality and compounding",
            confidence,
        )

    # --------------------------------------------------------
    # PRO 10
    # --------------------------------------------------------

    if (
        len(m["roe_history"]) >= 4
        and consecutive_increase(
            m["roe_history"],
            4,
        )
    ):

        add_signal(
            records,
            company_id,
            "pro",
            "PRO_10",
            "Return on equity improving for 3 consecutive years shows strengthening business quality",
            90,
        )

    # --------------------------------------------------------
    # PRO 11
    #
    # CORRECTED:
    # Revenue CAGR < PAT CAGR
    # --------------------------------------------------------

    if (
        rev_cagr is not None
        and pat_cagr is not None
        and pat_cagr > rev_cagr
    ):

        add_signal(
            records,
            company_id,
            "pro",
            "PRO_11",
            "Revenue growing slower than profits shows improving operating leverage and scale benefits",
            85,
        )

    # --------------------------------------------------------
    # PRO 12
    # --------------------------------------------------------

    assets = m["assets_history"]
    debt = m["debt_history"]

    if (
        len(assets) >= 3
        and len(debt) >= 3
        and assets.iloc[-1] > assets.iloc[-3]
        and debt.iloc[-1] < debt.iloc[-3]
    ):

        add_signal(
            records,
            company_id,
            "pro",
            "PRO_12",
            "Growing asset base funded by internal accruals reflects self-sustaining growth",
            85,
        )


# ============================================================
# CON RULES
# ============================================================

def apply_con_rules(
    company_id,
    m,
    records,
    is_financial,
):

    latest_pl = m["latest_pl"]

    de = m["debt_to_equity"]

    # --------------------------------------------------------
    # CON 1
    # --------------------------------------------------------

    if (
        not is_financial
        and de is not None
        and de > 2
    ):

        add_signal(
            records,
            company_id,
            "con",
            "CON_1",
            f"Debt-to-equity ratio of {de:.2f} is elevated for a non-financial company and warrants monitoring",
            min(
                95,
                70 + (de - 2) * 8,
            ),
        )

    # --------------------------------------------------------
    # CON 2
    # --------------------------------------------------------

    fcf = m["fcf_history"]

    if (
        len(fcf) >= 3
        and (fcf.tail(3) < 0).all()
    ):

        add_signal(
            records,
            company_id,
            "con",
            "CON_2",
            "Free cash flow negative for 3 consecutive years raises concern about cash generation quality",
            92,
        )

    # --------------------------------------------------------
    # CON 3
    # --------------------------------------------------------

    opm = m["opm_history"]

    if consecutive_decline(
        opm,
        4,
    ):

        add_signal(
            records,
            company_id,
            "con",
            "CON_3",
            "Operating margins declining for 3 consecutive years suggest pricing or cost pressure",
            90,
        )

    # --------------------------------------------------------
    # CON 4
    # --------------------------------------------------------

    net_profit = numeric(
        latest_pl.get("net_profit")
    )

    if (
        pd.notna(net_profit)
        and net_profit < 0
    ):

        add_signal(
            records,
            company_id,
            "con",
            "CON_4",
            "Company reported a net loss in the most recent financial year",
            98,
        )

    # --------------------------------------------------------
    # CON 5
    # --------------------------------------------------------

    revenue = m["revenue_history"]

    if consecutive_decline(
        revenue,
        3,
    ):

        add_signal(
            records,
            company_id,
            "con",
            "CON_5",
            "Revenue contraction over 2 consecutive years indicates demand weakness or market share loss",
            90,
        )

    # --------------------------------------------------------
    # CON 6
    # --------------------------------------------------------

    icr = m["latest_icr"]

    if (
        icr is not None
        and icr < 1.5
    ):

        add_signal(
            records,
            company_id,
            "con",
            "CON_6",
            "Interest coverage ratio below 1.5x indicates the company is at risk of not meeting its debt obligations",
            min(
                98,
                75 + (1.5 - icr) * 15,
            ),
        )

    # --------------------------------------------------------
    # CON 7
    # --------------------------------------------------------

    payout = numeric(
        latest_pl.get("dividend_payout")
    )

    if (
        pd.notna(payout)
        and payout > 100
    ):

        add_signal(
            records,
            company_id,
            "con",
            "CON_7",
            "Dividend payout ratio above 100% means the company is paying dividends from reserves, which is unsustainable",
            min(
                98,
                75 + (payout - 100) * 0.5,
            ),
        )

    # --------------------------------------------------------
    # CON 8
    # --------------------------------------------------------

    debt = m["debt_history"]

    if (
        len(debt) >= 4
        and consecutive_increase(
            debt,
            4,
        )
    ):

        add_signal(
            records,
            company_id,
            "con",
            "CON_8",
            "Rising debt-to-equity ratio over 3 years suggests increasing financial leverage risk",
            80,
        )

    # --------------------------------------------------------
    # CON 9
    # --------------------------------------------------------

    eps = m["eps_history"]

    if consecutive_decline(
        eps,
        4,
    ):

        add_signal(
            records,
            company_id,
            "con",
            "CON_9",
            "Earnings per share declining for 3 consecutive years reflects deteriorating profitability",
            90,
        )

    # --------------------------------------------------------
    # CON 10
    # --------------------------------------------------------

    roce = m["roce"]

    if (
        roce is not None
        and roce < 10
    ):

        add_signal(
            records,
            company_id,
            "con",
            "CON_10",
            "Return on capital employed below 10% suggests the business is not generating sufficient returns on invested capital",
            min(
                95,
                70 + (10 - roce) * 2,
            ),
        )

    # --------------------------------------------------------
    # CON 11
    # --------------------------------------------------------

    nde = m["net_debt_ebitda"]

    if (
        nde is not None
        and nde > 3
    ):

        add_signal(
            records,
            company_id,
            "con",
            "CON_11",
            "Net debt exceeding 3 times EBITDA is a high leverage ratio and limits financial flexibility",
            min(
                98,
                75 + (nde - 3) * 8,
            ),
        )

    # --------------------------------------------------------
    # CON 12
    # --------------------------------------------------------

    rev_cagr = m["revenue_cagr_5"]

    if (
        rev_cagr is not None
        and rev_cagr < 5
    ):

        add_signal(
            records,
            company_id,
            "con",
            "CON_12",
            "Revenue growing at below 5% over 5 years lags inflation and suggests limited business momentum",
            min(
                95,
                75 + (5 - rev_cagr) * 3,
            ),
        )


# ============================================================
# FALLBACK SIGNALS
# ============================================================

def add_fallback_pro(
    company_id,
    m,
    records,
):
    """
    Guarantee at least one Pro per company.

    This is used only when none of PRO_1 to PRO_12
    produces a valid signal.
    """

    candidates = []

    rev_cagr = m["revenue_cagr_5"]
    pat_cagr = m["pat_cagr_5"]
    eps_cagr = m["eps_cagr_5"]
    roe = m["roe"]
    roce = m["roce"]

    if rev_cagr is not None:
        candidates.append(
            (
                rev_cagr,
                "Revenue growth provides a measurable positive business momentum signal",
            )
        )

    if pat_cagr is not None:
        candidates.append(
            (
                pat_cagr,
                "Positive long-term profit growth provides evidence of earnings compounding",
            )
        )

    if eps_cagr is not None:
        candidates.append(
            (
                eps_cagr,
                "Positive EPS growth provides evidence of improving per-share earnings",
            )
        )

    if roe is not None and roe > 0:
        candidates.append(
            (
                roe,
                "Positive return on equity indicates the company is generating returns on shareholder capital",
            )
        )

    if roce is not None and roce > 0:
        candidates.append(
            (
                roce,
                "Positive return on capital employed indicates productive use of invested capital",
            )
        )

    if candidates:

        best_value, text = max(
            candidates,
            key=lambda x: x[0],
        )

        confidence = min(
            85,
            max(
                65,
                65 + abs(float(best_value)) * 0.5,
            ),
        )

        add_signal(
            records,
            company_id,
            "pro",
            "PRO_FALLBACK",
            text,
            confidence,
        )

    else:

        add_signal(
            records,
            company_id,
            "pro",
            "PRO_FALLBACK",
            "Available financial data provides a baseline positive operating signal for the company",
            65,
        )


def add_fallback_con(
    company_id,
    m,
    records,
):
    """
    Guarantee at least one Con per company.

    This is used only when none of CON_1 to CON_12
    produces a valid signal.
    """

    candidates = []

    rev_cagr = m["revenue_cagr_5"]
    pat_cagr = m["pat_cagr_5"]
    eps_cagr = m["eps_cagr_5"]
    roce = m["roce"]
    de = m["debt_to_equity"]
    icr = m["latest_icr"]

    if rev_cagr is not None:
        candidates.append(
            (
                100 - min(max(rev_cagr, 0), 100),
                "Revenue growth does not meet the stronger growth thresholds used by the core screening rules",
            )
        )

    if pat_cagr is not None:
        candidates.append(
            (
                100 - min(max(pat_cagr, 0), 100),
                "Profit growth does not meet the stronger compounding thresholds used by the core screening rules",
            )
        )

    if eps_cagr is not None:
        candidates.append(
            (
                100 - min(max(eps_cagr, 0), 100),
                "EPS growth does not meet the stronger earnings-growth thresholds used by the core screening rules",
            )
        )

    if roce is not None:
        candidates.append(
            (
                max(0, 10 - roce),
                "Return on capital employed remains below the stronger return threshold used by the screening framework",
            )
        )

    if de is not None:
        candidates.append(
            (
                min(de * 10, 100),
                "The company carries some balance-sheet leverage that should continue to be monitored",
            )
        )

    if icr is not None and icr > 0:
        candidates.append(
            (
                max(0, 10 - icr),
                "Interest coverage should continue to be monitored even though the core distress threshold is not breached",
            )
        )

    if candidates:

        score, text = max(
            candidates,
            key=lambda x: x[0],
        )

        confidence = min(
            85,
            max(
                65,
                65 + float(score) * 0.5,
            ),
        )

        add_signal(
            records,
            company_id,
            "con",
            "CON_FALLBACK",
            text,
            confidence,
        )

    else:

        add_signal(
            records,
            company_id,
            "con",
            "CON_FALLBACK",
            "Available financial data does not trigger a core risk rule, but continued monitoring remains appropriate",
            65,
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n" + "=" * 60)
    print("NLP PROS/CONS GENERATOR")
    print("=" * 60)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Load
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
    # Normalize IDs
    # --------------------------------------------------------

    for df in [
        companies,
        pl,
        bs,
        cf,
        sectors,
    ]:

        if "company_id" in df.columns:

            df["company_id"] = (
                df["company_id"]
                .astype(str)
                .str.strip()
                .str.upper()
            )

    companies["id"] = (
        companies["id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # --------------------------------------------------------
    # Financial sector detection
    # --------------------------------------------------------

    financial_sectors = {
        "financials",
        "financial services",
        "banking",
        "insurance",
    }

    sector_map = {}

    if (
        "company_id" in sectors.columns
        and "broad_sector" in sectors.columns
    ):

        sector_map = dict(
            zip(
                sectors["company_id"],
                sectors["broad_sector"]
                .astype(str)
                .str.strip()
                .str.lower(),
            )
        )

    # --------------------------------------------------------
    # Generate
    # --------------------------------------------------------

    records = []

    company_ids = (
        companies["id"]
        .dropna()
        .unique()
    )

    logger.info(
        "Companies to process: %d",
        len(company_ids),
    )

    for company_id in company_ids:

        metrics = build_company_metrics(
            company_id,
            pl,
            bs,
            cf,
            companies,
        )

        if metrics is None:

            logger.warning(
                "No profit/loss data for %s",
                company_id,
            )

            continue

        sector = sector_map.get(
            company_id,
            "",
        )

        is_financial = (
            sector in financial_sectors
        )

        # Count signals before processing
        before_pro = len(
            [
                r for r in records
                if (
                    r["company_id"] == company_id
                    and r["type"] == "pro"
                )
            ]
        )

        before_con = len(
            [
                r for r in records
                if (
                    r["company_id"] == company_id
                    and r["type"] == "con"
                )
            ]
        )

        apply_pro_rules(
            company_id,
            metrics,
            records,
        )

        apply_con_rules(
            company_id,
            metrics,
            records,
            is_financial,
        )

        # ----------------------------------------------------
        # FALLBACK PRO
        # ----------------------------------------------------

        after_pro = len(
            [
                r for r in records
                if (
                    r["company_id"] == company_id
                    and r["type"] == "pro"
                )
            ]
        )

        if after_pro == before_pro:

            add_fallback_pro(
                company_id,
                metrics,
                records,
            )

        # ----------------------------------------------------
        # FALLBACK CON
        # ----------------------------------------------------

        after_con = len(
            [
                r for r in records
                if (
                    r["company_id"] == company_id
                    and r["type"] == "con"
                )
            ]
        )

        if after_con == before_con:

            add_fallback_con(
                company_id,
                metrics,
                records,
            )

    # --------------------------------------------------------
    # Output dataframe
    # --------------------------------------------------------

    output_columns = [
        "company_id",
        "type",
        "rule_id",
        "text",
        "confidence_pct",
    ]

    result = pd.DataFrame(
        records,
        columns=output_columns,
    )

    result = result.drop_duplicates(
        subset=[
            "company_id",
            "type",
            "rule_id",
        ]
    )

    result = result.sort_values(
        [
            "company_id",
            "type",
            "rule_id",
        ]
    ).reset_index(drop=True)

    result.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    # --------------------------------------------------------
    # Verification
    # --------------------------------------------------------

    company_set = set(company_ids)

    pro_companies = set(
        result.loc[
            result["type"] == "pro",
            "company_id",
        ]
    )

    con_companies = set(
        result.loc[
            result["type"] == "con",
            "company_id",
        ]
    )

    missing_pro = sorted(
        company_set - pro_companies
    )

    missing_con = sorted(
        company_set - con_companies
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("GENERATION SUMMARY")
    print("=" * 60)

    print(
        f"Companies: {len(company_ids)}"
    )

    print(
        f"Output rows: {len(result)}"
    )

    print("\nSignal counts:")

    print(
        result["type"]
        .value_counts()
        .to_string()
    )

    print("\nRule counts:")

    print(
        result["rule_id"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print("\nOutput:")
    print(OUTPUT_FILE)

    print("\nVerification:")

    print(
        f"Companies without Pro: {len(missing_pro)}"
    )

    if missing_pro:
        print(missing_pro)

    print(
        f"Companies without Con: {len(missing_con)}"
    )

    if missing_con:
        print(missing_con)

    if not missing_pro and not missing_con:
        print(
            "\nPASS: Every company has at least 1 Pro and 1 Con."
        )
    else:
        print(
            "\nFAIL: Some companies are missing signals."
        )

    print("\nConfidence rule:")
    print(
        "Only signals with confidence > 60% are included."
    )

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()