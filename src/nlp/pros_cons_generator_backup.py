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
    """
    Calculate CAGR percentage.

    Returns None for cases where conventional CAGR
    is not meaningful.
    """
    if pd.isna(start) or pd.isna(end):
        return None

    if years <= 0:
        return None

    if start <= 0 or end <= 0:
        return None

    return ((end / start) ** (1 / years) - 1) * 100


def consecutive_positive(series, count):
    """Check whether latest `count` observations are positive."""
    values = series.dropna().tail(count)

    if len(values) < count:
        return False

    return bool((values > 0).all())


def consecutive_decline(series, count):
    """
    Check whether the latest values declined consecutively.

    Example for count=3:
        year1 > year2 > year3
    """
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


def add_signal(records, company_id, signal_type, rule_id, text, confidence):
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
    """
    Build all required metrics for one company.
    """

    company_pl = pl[pl["company_id"] == company_id].copy()
    company_bs = bs[bs["company_id"] == company_id].copy()
    company_cf = cf[cf["company_id"] == company_id].copy()

    company_pl = company_pl.sort_values("year")
    company_bs = company_bs.sort_values("year")
    company_cf = company_cf.sort_values("year")

    if company_pl.empty:
        return None

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
    ]

    for col in pl_numeric_cols:
        if col in company_pl.columns:
            company_pl[col] = numeric(company_pl[col])

    bs_numeric_cols = [
        "borrowings",
        "reserves",
        "total_assets",
        "total_liabilities",
    ]

    for col in bs_numeric_cols:
        if col in company_bs.columns:
            company_bs[col] = numeric(company_bs[col])

    if not company_cf.empty:
        for col in [
            "operating_activity",
            "investing_activity",
            "financing_activity",
            "net_cash_flow",
        ]:
            if col in company_cf.columns:
                company_cf[col] = numeric(company_cf[col])

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
            roe = numeric(
                company_row.iloc[0]["roe_percentage"]
            )

            if pd.notna(roe):
                roe = float(roe)

    # --------------------------------------------------------
    # ROCE
    # --------------------------------------------------------

    roce = None

    if "roce_percentage" in company_info.columns:
        company_row = company_info[
            company_info["id"] == company_id
        ]

        if not company_row.empty:
            roce = numeric(
                company_row.iloc[0]["roce_percentage"]
            )

            if pd.notna(roce):
                roce = float(roce)

    # --------------------------------------------------------
    # Debt / Equity
    # --------------------------------------------------------

    debt_to_equity = None

    if latest_bs is not None:
        borrowings = latest_bs.get("borrowings")
        reserves = latest_bs.get("reserves")
        equity_capital = latest_bs.get("equity_capital")

        total_equity = (
            pd.to_numeric(reserves, errors="coerce")
            + pd.to_numeric(equity_capital, errors="coerce")
        )

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

    fcf = company_cf.copy()

    if not fcf.empty:
        fcf = fcf.sort_values("year")

    # --------------------------------------------------------
    # Interest Coverage Ratio
    # ICR = EBIT / Interest
    # EBIT = PBT + Interest
    # --------------------------------------------------------

    company_pl["ebit"] = (
        company_pl["profit_before_tax"]
        + company_pl["interest"]
    )

    company_pl["icr"] = None

    interest_positive = company_pl["interest"] > 0

    company_pl.loc[interest_positive, "icr"] = (
        company_pl.loc[interest_positive, "ebit"]
        / company_pl.loc[interest_positive, "interest"]
    )

    latest_icr = company_pl.iloc[-1]["icr"]

    if pd.notna(latest_icr):
        latest_icr = float(latest_icr)

    # --------------------------------------------------------
    # Net debt / EBITDA
    #
    # EBITDA approximation:
    # Operating Profit + Depreciation
    # --------------------------------------------------------

    net_debt_ebitda = None

    if latest_bs is not None:

        borrowings = pd.to_numeric(
            latest_bs.get("borrowings"),
            errors="coerce",
        )

        cash = 0.0

        if not fcf.empty:
            # No cash balance field exists in supplied
            # balance-sheet schema, so net debt is
            # approximated using borrowings.
            cash = 0.0

        latest_ebitda = (
            pd.to_numeric(
                latest_pl.get("operating_profit"),
                errors="coerce",
            )
        )

        if "depreciation" in latest_pl:
            depreciation = pd.to_numeric(
                latest_pl.get("depreciation"),
                errors="coerce",
            )

            if pd.notna(depreciation):
                latest_ebitda += depreciation

        if (
            pd.notna(borrowings)
            and pd.notna(latest_ebitda)
            and latest_ebitda > 0
        ):
            net_debt = borrowings - cash

            net_debt_ebitda = (
                net_debt / latest_ebitda
            )

    # --------------------------------------------------------
    # CAGR calculations
    # --------------------------------------------------------

    def metric_cagr(column, years):
        """
        Calculate CAGR using annual financial data.
        """
        data = company_pl[
            company_pl[column].notna()
        ].copy()

        if len(data) < years + 1:
            return None

        start = data.iloc[-(years + 1)][column]
        end = data.iloc[-1][column]

        return safe_cagr(
            float(start),
            float(end),
            years,
        )

    revenue_cagr_5 = metric_cagr("sales", 5)
    pat_cagr_5 = metric_cagr("net_profit", 5)
    eps_cagr_5 = metric_cagr("eps", 5)

    # --------------------------------------------------------
    # ROE history
    #
    # Companies.xlsx only contains latest ROE.
    # Therefore sustained ROE improvement cannot be
    # calculated historically from that file.
    # --------------------------------------------------------

    roe_history = None

    # --------------------------------------------------------
    # OPM history
    # --------------------------------------------------------

    opm_history = company_pl[
        "opm_percentage"
    ].dropna()

    # --------------------------------------------------------
    # Revenue history
    # --------------------------------------------------------

    revenue_history = company_pl[
        "sales"
    ].dropna()

    # --------------------------------------------------------
    # EPS history
    # --------------------------------------------------------

    eps_history = company_pl[
        "eps"
    ].dropna()

    # --------------------------------------------------------
    # Debt history
    # --------------------------------------------------------

    debt_history = pd.Series(dtype=float)

    if not company_bs.empty:
        debt_history = company_bs[
            "borrowings"
        ].dropna()

    # --------------------------------------------------------
    # Assets history
    # --------------------------------------------------------

    assets_history = pd.Series(dtype=float)

    if not company_bs.empty:
        assets_history = company_bs[
            "total_assets"
        ].dropna()

    # --------------------------------------------------------
    # FCF history
    #
    # Since cashflow.xlsx provides net_cash_flow rather
    # than a dedicated free_cash_flow field, use
    # operating activity + investing activity as FCF
    # proxy.
    # --------------------------------------------------------

    fcf_history = pd.Series(dtype=float)

    if not company_cf.empty:
        fcf_history = (
            company_cf["operating_activity"]
            + company_cf["investing_activity"]
        ).dropna()

    # --------------------------------------------------------
    # Dividend yield
    #
    # Dividend payout is available, but dividend yield is
    # not directly present in the supplied raw files.
    # Therefore this rule cannot be evaluated reliably.
    # --------------------------------------------------------

    dividend_yield = None

    return {
        "pl": company_pl,
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
    # ROE > 20% sustained for 3+ years
    #
    # Historical ROE is not available in supplied raw files.
    # We therefore only fire this when historical ROE exists.
    # --------------------------------------------------------

    roe_history = m["roe_history"]

    if (
        roe_history is not None
        and len(roe_history) >= 3
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
    # FCF positive for 5+ consecutive years
    # --------------------------------------------------------

    fcf = m["fcf_history"]

    if consecutive_positive(fcf, 5):
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
    # D/E = 0
    # --------------------------------------------------------

    de = m["debt_to_equity"]

    if de is not None and abs(de) < 1e-9:
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
    # Revenue CAGR > 15%
    # --------------------------------------------------------

    rev_cagr = m["revenue_cagr_5"]

    if rev_cagr is not None and rev_cagr > 15:
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
    # OPM > 25%
    # --------------------------------------------------------

    opm = latest_pl.get("opm_percentage")

    if pd.notna(opm) and opm > 25:

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
    # PAT CAGR > 20%
    # --------------------------------------------------------

    pat_cagr = m["pat_cagr_5"]

    if pat_cagr is not None and pat_cagr > 20:

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
    # ICR > 10 OR debt free
    # --------------------------------------------------------

    icr = m["latest_icr"]

    if (
        (icr is not None and icr > 10)
        or (de is not None and abs(de) < 1e-9)
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
    # Dividend yield > 2% + FCF positive
    #
    # Dividend yield is unavailable in supplied raw data.
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
    # EPS CAGR > 15%
    # --------------------------------------------------------

    eps_cagr = m["eps_cagr_5"]

    if eps_cagr is not None and eps_cagr > 15:

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
    # ROE improving for 3 consecutive years
    #
    # Historical ROE unavailable.
    # --------------------------------------------------------

    if (
        m["roe_history"] is not None
        and consecutive_increase(m["roe_history"], 4)
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
    # Revenue CAGR > PAT CAGR
    # --------------------------------------------------------

    if (
        rev_cagr is not None
        and pat_cagr is not None
        and rev_cagr > pat_cagr
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
    # Assets growing + declining debt
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

def apply_con_rules(company_id, m, records, is_financial):

    latest_pl = m["latest_pl"]

    de = m["debt_to_equity"]

    # --------------------------------------------------------
    # CON 1
    # D/E > 2 for non-financial companies
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
            min(95, 70 + (de - 2) * 8),
        )

    # --------------------------------------------------------
    # CON 2
    # FCF negative for 3 consecutive years
    # --------------------------------------------------------

    fcf = m["fcf_history"]

    if len(fcf) >= 3 and (fcf.tail(3) < 0).all():
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
    # OPM declining for 3 consecutive years
    # --------------------------------------------------------

    opm = m["opm_history"]

    if consecutive_decline(opm, 4):
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
    # Net profit negative latest year
    # --------------------------------------------------------

    net_profit = latest_pl.get("net_profit")

    if pd.notna(net_profit) and net_profit < 0:
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
    # Revenue declining for 2+ years
    # --------------------------------------------------------

    revenue = m["revenue_history"]

    if consecutive_decline(revenue, 3):
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
    # ICR < 1.5
    # --------------------------------------------------------

    icr = m["latest_icr"]

    if icr is not None and icr < 1.5:
        add_signal(
            records,
            company_id,
            "con",
            "CON_6",
            "Interest coverage ratio below 1.5x indicates the company is at risk of not meeting its debt obligations",
            min(98, 75 + (1.5 - icr) * 15),
        )

    # --------------------------------------------------------
    # CON 7
    # Dividend payout > 100%
    # --------------------------------------------------------

    payout = latest_pl.get("dividend_payout")

    if pd.notna(payout) and payout > 100:
        add_signal(
            records,
            company_id,
            "con",
            "CON_7",
            "Dividend payout ratio above 100% means the company is paying dividends from reserves, which is unsustainable",
            min(98, 75 + (payout - 100) * 0.5),
        )

    # --------------------------------------------------------
    # CON 8
    # D/E rising for 3 consecutive years
    # --------------------------------------------------------

    debt = m["debt_history"]

    if len(debt) >= 4:
        # Debt/equity history cannot be reconstructed exactly
        # from borrowings alone, so this is based on borrowings
        # trend as a leverage proxy.
        if consecutive_increase(debt, 4):
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
    # EPS declining for 3 consecutive years
    # --------------------------------------------------------

    eps = m["eps_history"]

    if consecutive_decline(eps, 4):
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
    # ROCE < 10%
    # --------------------------------------------------------

    roce = m["roce"]

    if roce is not None and roce < 10:
        add_signal(
            records,
            company_id,
            "con",
            "CON_10",
            "Return on capital employed below 10% suggests the business is not generating sufficient returns on invested capital",
            min(95, 70 + (10 - roce) * 2),
        )

    # --------------------------------------------------------
    # CON 11
    # Net Debt > 3x EBITDA
    # --------------------------------------------------------

    nde = m["net_debt_ebitda"]

    if nde is not None and nde > 3:
        add_signal(
            records,
            company_id,
            "con",
            "CON_11",
            "Net debt exceeding 3 times EBITDA is a high leverage ratio and limits financial flexibility",
            min(98, 75 + (nde - 3) * 8),
        )

    # --------------------------------------------------------
    # CON 12
    # Revenue CAGR < 5%
    # --------------------------------------------------------

    rev_cagr = m["revenue_cagr_5"]

    if rev_cagr is not None and rev_cagr < 5:
        add_signal(
            records,
            company_id,
            "con",
            "CON_12",
            "Revenue growing at below 5% over 5 years lags inflation and suggests limited business momentum",
            min(95, 75 + (5 - rev_cagr) * 3),
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
    # Load data
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
    # Generate signals
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

        is_financial = sector in financial_sectors

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

    # Remove accidental duplicates
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

    print(f"Companies: {len(company_ids)}")
    print(f"Output rows: {len(result)}")

    if not result.empty:
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

    if missing_pro:
        print(
            f"Companies without Pro: {len(missing_pro)}"
        )
        print(missing_pro)
    else:
        print(
            "Every company has at least 1 Pro."
        )

    if missing_con:
        print(
            f"Companies without Con: {len(missing_con)}"
        )
        print(missing_con)
    else:
        print(
            "Every company has at least 1 Con."
        )

    print("\nConfidence rule:")
    print("Only signals with confidence > 60% are included.")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()