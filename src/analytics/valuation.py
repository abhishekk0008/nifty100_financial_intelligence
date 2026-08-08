from pathlib import Path
import sys

import pandas as pd


# ============================================================
# PROJECT ROOT
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


# ============================================================
# DATA PATHS
# ============================================================

RAW_DIR = ROOT / "data" / "raw"
OUTPUT_DIR = ROOT / "output"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# LOAD DATA
# ============================================================

def load_data():

    companies_df = pd.read_excel(
        RAW_DIR / "companies.xlsx",
        header=1,
    )

    market_cap_df = pd.read_excel(
        RAW_DIR / "market_cap.xlsx"
    )

    ratios_df = pd.read_excel(
        RAW_DIR / "financial_ratios.xlsx"
    )

    sectors_df = pd.read_excel(
        RAW_DIR / "sectors.xlsx"
    )

    return (
        companies_df,
        market_cap_df,
        ratios_df,
        sectors_df,
    )


# ============================================================
# BUILD VALUATION
# ============================================================

def build_valuation():

    (
        companies_df,
        market_cap_df,
        ratios_df,
        sectors_df,
    ) = load_data()


    # ========================================================
    # STANDARDIZE IDS
    # ========================================================

    companies_df["id"] = (
        companies_df["id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    market_cap_df["company_id"] = (
        market_cap_df["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    ratios_df["company_id"] = (
        ratios_df["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    sectors_df["company_id"] = (
        sectors_df["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )


    # ========================================================
    # NUMERIC YEAR
    # ========================================================

    market_cap_df["year"] = pd.to_numeric(
        market_cap_df["year"],
        errors="coerce",
    )

    ratios_df["year"] = pd.to_numeric(
        ratios_df["year"],
        errors="coerce",
    )


    # ========================================================
    # LATEST MARKET DATA — COMPANY WISE
    # ========================================================

    latest_market = (
        market_cap_df
        .sort_values("year")
        .groupby("company_id")
        .tail(1)[
            [
                "company_id",
                "year",
                "market_cap_crore",
                "pe_ratio",
                "pb_ratio",
                "ev_ebitda",
                "dividend_yield_pct",
            ]
        ]
        .copy()
    )

    latest_year = latest_market["year"].max()


    # ========================================================
    # 5-YEAR HISTORICAL MEDIANS
    # ========================================================

    historical = market_cap_df[
        market_cap_df["year"] >= latest_year - 4
    ].copy()

    historical_median = (
        historical
        .groupby("company_id")
        .agg(
            pe_5yr_median=("pe_ratio", "median"),
            pb_5yr_median=("pb_ratio", "median"),
            ev_ebitda_5yr_median=("ev_ebitda", "median"),
        )
        .reset_index()
    )


    # ========================================================
    # LATEST FCF — COMPANY WISE
    # ========================================================

    latest_fcf = (
        ratios_df
        .sort_values("year")
        .groupby("company_id")
        .tail(1)[
            [
                "company_id",
                "free_cash_flow_cr",
            ]
        ]
        .copy()
    )


    # ========================================================
    # MERGE COMPANY INFORMATION
    # ========================================================

    result = companies_df[
        [
            "id",
            "company_name",
        ]
    ].merge(
        latest_market,
        left_on="id",
        right_on="company_id",
        how="left",
    )


    # ========================================================
    # MERGE HISTORICAL MEDIANS
    # ========================================================

    result = result.merge(
        historical_median,
        on="company_id",
        how="left",
    )


    # ========================================================
    # MERGE FCF
    # ========================================================

    result = result.merge(
        latest_fcf,
        on="company_id",
        how="left",
    )


    # ========================================================
    # MERGE SECTOR
    # ========================================================

    result = result.merge(
        sectors_df[
            [
                "company_id",
                "broad_sector",
            ]
        ],
        on="company_id",
        how="left",
    )


    # ========================================================
    # FCF YIELD
    # ========================================================

    result["fcf_yield_pct"] = (
        result["free_cash_flow_cr"]
        / result["market_cap_crore"]
        * 100
    )


    # ========================================================
    # SECTOR MEDIANS
    # ========================================================

    sector_medians = (
        result
        .groupby("broad_sector")
        .agg(
            sector_pe_median=("pe_ratio", "median"),
            sector_pb_median=("pb_ratio", "median"),
            sector_ev_ebitda_median=("ev_ebitda", "median"),
        )
        .reset_index()
    )


    result = result.merge(
        sector_medians,
        on="broad_sector",
        how="left",
    )


    # ========================================================
    # EV / EBITDA VS SECTOR
    # ========================================================

    result["ev_ebitda_vs_sector_pct"] = (
        (
            result["ev_ebitda"]
            / result["sector_ev_ebitda_median"]
        ) - 1
    ) * 100


    # ========================================================
    # EV / EBITDA FLAG
    # ========================================================

    result["ev_ebitda_flag"] = "Normal"

    result.loc[
        result["ev_ebitda_vs_sector_pct"] > 20,
        "ev_ebitda_flag",
    ] = "Above Sector"


    # ========================================================
    # P/E OVERVALUATION FLAG
    #
    # P/E > sector median × 1.5  -> Caution
    # P/E < sector median × 0.7  -> Discount
    # ========================================================

    result["flag"] = "Neutral"

    result.loc[
        result["pe_ratio"]
        > result["sector_pe_median"] * 1.5,
        "flag",
    ] = "Caution"

    result.loc[
        result["pe_ratio"]
        < result["sector_pe_median"] * 0.7,
        "flag",
    ] = "Discount"


    # ========================================================
    # FLAG RATIONALE
    # ========================================================

    result["flag_rationale"] = ""

    result.loc[
        result["flag"] == "Caution",
        "flag_rationale",
    ] = (
        "P/E is more than 1.5x the sector median"
    )

    result.loc[
        result["flag"] == "Discount",
        "flag_rationale",
    ] = (
        "P/E is below 70% of the sector median"
    )


    # ========================================================
    # SECTOR RANK — P/E
    # ========================================================

    result["sector_pe_rank"] = (
        result
        .groupby("broad_sector")["pe_ratio"]
        .rank(
            method="min",
            ascending=True,
        )
    )


    # ========================================================
    # FCF YIELD RANK
    # ========================================================

    result["fcf_yield_rank"] = (
        result["fcf_yield_pct"]
        .rank(
            method="min",
            ascending=False,
        )
    )


    # ========================================================
    # FINAL COLUMN ORDER
    # ========================================================

    final_columns = [
        "id",
        "company_id",
        "company_name",
        "broad_sector",
        "year",
        "market_cap_crore",

        "pe_ratio",
        "pe_5yr_median",
        "sector_pe_median",
        "sector_pe_rank",

        "pb_ratio",
        "pb_5yr_median",
        "sector_pb_median",

        "ev_ebitda",
        "ev_ebitda_5yr_median",
        "sector_ev_ebitda_median",
        "ev_ebitda_vs_sector_pct",
        "ev_ebitda_flag",

        "dividend_yield_pct",

        "free_cash_flow_cr",
        "fcf_yield_pct",
        "fcf_yield_rank",

        "flag",
        "flag_rationale",
    ]


    final_columns = [
        col
        for col in final_columns
        if col in result.columns
    ]

    result = result[final_columns]


    # ========================================================
    # ROUND NUMERIC COLUMNS
    # ========================================================

    numeric_columns = result.select_dtypes(
        include="number"
    ).columns

    result[numeric_columns] = (
        result[numeric_columns]
        .round(2)
    )


    # ========================================================
    # SORT BY FCF YIELD
    # ========================================================

    result = result.sort_values(
        "fcf_yield_pct",
        ascending=False,
        na_position="last",
    )


    # ========================================================
    # SAVE OUTPUT
    # ========================================================

    output_file = (
        OUTPUT_DIR
        / "valuation_summary.xlsx"
    )

    result.to_excel(
        output_file,
        index=False,
    )


    # ========================================================
    # SAVE FLAGS CSV
    # ========================================================

    flags = result[
        result["flag"].isin(
            [
                "Caution",
                "Discount",
            ]
        )
    ].copy()

    flags_file = (
        OUTPUT_DIR
        / "valuation_flags.csv"
    )

    flags.to_csv(
        flags_file,
        index=False,
    )


    # ========================================================
    # CONSOLE SUMMARY
    # ========================================================

    print("=" * 60)
    print("VALUATION MODULE")
    print("=" * 60)

    print(
        "Latest market year:",
        latest_year,
    )

    print(
        "Companies:",
        result["company_id"].nunique(),
    )

    print(
        "Valuation rows:",
        len(result),
    )

    print("\nValuation flags:")

    print(
        result["flag"]
        .value_counts(dropna=False)
    )

    print(
        "\nEV/EBITDA flags:"
    )

    print(
        result["ev_ebitda_flag"]
        .value_counts(dropna=False)
    )

    print(
        "\nOutput:",
        output_file,
    )

    print(
        "Flags CSV:",
        flags_file,
    )

    print("=" * 60)


    return result


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    build_valuation()