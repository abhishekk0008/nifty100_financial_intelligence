"""
Day 37 — Cluster Profiling & Statistics

Deliverables
------------
1. output/cluster_profile_stats.csv
2. reports/correlation_heatmap.png
3. output/outlier_report.csv
4. output/portfolio_stats.csv

Also updates:
5. output/cluster_labels.csv with descriptive cluster names
"""

from pathlib import Path
import logging

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


# ============================================================
# CONFIG
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = ROOT / "data" / "raw"
OUTPUT_DIR = ROOT / "output"
REPORTS_DIR = ROOT / "reports"

RATIOS_FILE = RAW_DIR / "financial_ratios.xlsx"
CLUSTER_FILE = OUTPUT_DIR / "cluster_labels.csv"
SECTORS_FILE = RAW_DIR / "sectors.xlsx"

CLUSTER_PROFILE_FILE = (
    OUTPUT_DIR / "cluster_profile_stats.csv"
)

CORRELATION_HEATMAP = (
    REPORTS_DIR / "correlation_heatmap.png"
)

OUTLIER_FILE = (
    OUTPUT_DIR / "outlier_report.csv"
)

PORTFOLIO_STATS_FILE = (
    OUTPUT_DIR / "portfolio_stats.csv"
)


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
        str(column).strip().lower().replace(" ", "_")
        for column in df.columns
    ]

    return df

def numeric(series):
    return pd.to_numeric(
        series,
        errors="coerce",
    )


def load_excel(path, header=0):
    logger.info(
        "Loading %s",
        path.name,
    )

    df = pd.read_excel(
        path,
        header=header,
    )

    df = clean_columns(df)

    logger.info(
        "%s shape: %s",
        path.name,
        df.shape,
    )

    return df


def latest_year_rows(df):
    """
    Select latest available year for each company.
    """

    data = df.copy()

    year_text = (
        data["year"]
        .astype(str)
        .str.extract(
            r"(\d{4})",
            expand=False,
        )
    )

    data["_year_num"] = pd.to_numeric(
        year_text,
        errors="coerce",
    )

    data = data.sort_values(
        [
            "company_id",
            "_year_num",
        ]
    )

    latest = (
        data
        .groupby(
            "company_id",
            as_index=False,
        )
        .tail(1)
        .copy()
    )

    return latest


# ============================================================
# CLUSTER PROFILE
# ============================================================

CLUSTER_FEATURES = [
    "return_on_equity_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "fcf_cagr_5yr",
    "operating_profit_margin_pct",
]


def profile_clusters(cluster_df, ratios):
    """
    Compute mean and median of all five clustering features
    for each cluster.
    """

    # The five feature values for revenue/FCF CAGR are already
    # represented indirectly in cluster labels, but we need
    # actual values for profiling.

    data = cluster_df.copy()

    # If the clustering script has already produced the feature
    # values elsewhere, use them. Otherwise reconstruct the
    # available ratio features and leave CAGR values to be
    # calculated from source files where possible.
    available = [
        c for c in CLUSTER_FEATURES
        if c in data.columns
    ]

    if len(available) == 5:
        profile_source = data.copy()

    else:
        profile_source = data.merge(
            ratios[
                [
                    "company_id",
                    "return_on_equity_pct",
                    "debt_to_equity",
                    "operating_profit_margin_pct",
                ]
            ],
            on="company_id",
            how="left",
            suffixes=("", "_ratio"),
        )

        for col in [
            "return_on_equity_pct",
            "debt_to_equity",
            "operating_profit_margin_pct",
        ]:
            if col not in profile_source.columns:
                profile_source[col] = np.nan

    # CAGR columns may not exist in cluster_labels.csv.
    # This is handled gracefully.
    for col in [
        "revenue_cagr_5yr",
        "fcf_cagr_5yr",
    ]:
        if col not in profile_source.columns:
            profile_source[col] = np.nan

    rows = []

    for cluster_id, group in profile_source.groupby(
        "cluster_id"
    ):

        row = {
            "cluster_id": int(cluster_id),
            "company_count": len(group),
        }

        for feature in CLUSTER_FEATURES:

            values = numeric(
                group[feature]
            ).dropna()

            row[
                f"{feature}_mean"
            ] = (
                round(float(values.mean()), 4)
                if len(values)
                else np.nan
            )

            row[
                f"{feature}_median"
            ] = (
                round(float(values.median()), 4)
                if len(values)
                else np.nan
            )

        rows.append(row)

    result = pd.DataFrame(rows)

    result = result.sort_values(
        "cluster_id"
    ).reset_index(drop=True)

    return result


# ============================================================
# CLUSTER NAME GENERATION
# ============================================================

def generate_cluster_names(profile):
    """
    Generate descriptive names based on cluster profile.

    Names are based on relative characteristics:
    - ROE
    - leverage
    - revenue growth
    - FCF growth
    - operating margin
    """

    p = profile.copy()

    for feature in CLUSTER_FEATURES:

        median_col = (
            f"{feature}_median"
        )

        if median_col in p.columns:
            p[median_col] = numeric(
                p[median_col]
            )

    # Rank every cluster on each characteristic.
    p["growth_score"] = (
        p["revenue_cagr_5yr_median"].rank(
            pct=True
        )
        +
        p["fcf_cagr_5yr_median"].rank(
            pct=True
        )
    ) / 2

    p["quality_score"] = (
        p["return_on_equity_pct_median"].rank(
            pct=True
        )
        +
        p["operating_profit_margin_pct_median"].rank(
            pct=True
        )
    ) / 2

    # Lower debt = better balance sheet.
    p["balance_score"] = (
        1 -
        p["debt_to_equity_median"].rank(
            pct=True
        )
    )

    p["overall_score"] = (
        0.45 * p["quality_score"]
        + 0.35 * p["growth_score"]
        + 0.20 * p["balance_score"]
    )

    # Determine five unique archetypes.
    names = {}

    if len(p) != 5:
        return {
            int(row["cluster_id"]):
            f"Cluster {int(row['cluster_id'])}"
            for _, row in p.iterrows()
        }

    # Highest overall quality + growth.
    best = p.sort_values(
        "overall_score",
        ascending=False,
    ).iloc[0]

    names[
        int(best["cluster_id"])
    ] = "High-Quality Compounders"

    remaining = p[
        ~p["cluster_id"].eq(
            best["cluster_id"]
        )
    ].copy()

    # Highest growth among remaining.
    growth = remaining.sort_values(
        "growth_score",
        ascending=False,
    ).iloc[0]

    names[
        int(growth["cluster_id"])
    ] = "Emerging Growth"

    remaining = remaining[
        ~remaining["cluster_id"].eq(
            growth["cluster_id"]
        )
    ].copy()

    # Highest leverage.
    leveraged = remaining.sort_values(
        "debt_to_equity_median",
        ascending=False,
    ).iloc[0]

    names[
        int(leveraged["cluster_id"])
    ] = "Leveraged / Turnaround"

    remaining = remaining[
        ~remaining["cluster_id"].eq(
            leveraged["cluster_id"]
        )
    ].copy()

    # Strongest balance sheet among remaining.
    defensive = remaining.sort_values(
        "balance_score",
        ascending=False,
    ).iloc[0]

    names[
        int(defensive["cluster_id"])
    ] = "Defensive Quality"

    remaining = remaining[
        ~remaining["cluster_id"].eq(
            defensive["cluster_id"]
        )
    ].copy()

    # Last cluster.
    if len(remaining) == 1:

        cluster_id = int(
            remaining.iloc[0]["cluster_id"]
        )

        names[
            cluster_id
        ] = "Value / Cyclical"

    return names


# ============================================================
# CORRELATION MATRIX
# ============================================================

CORRELATION_KPIS = [
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
    "return_on_equity_pct",
    "debt_to_equity",
    "interest_coverage",
    "asset_turnover",
    "free_cash_flow_cr",
    "earnings_per_share",
    "book_value_per_share",
    "dividend_payout_ratio_pct",
]


def generate_correlation_heatmap(latest):
    """
    Pearson correlation matrix for 10 latest-year KPIs.
    """

    logger.info(
        "Generating Pearson correlation heatmap..."
    )

    data = latest[
        CORRELATION_KPIS
    ].copy()

    for col in CORRELATION_KPIS:
        data[col] = numeric(
            data[col]
        )

    correlation = data.corr(
        method="pearson"
    )

    # Friendly display names.
    display_names = {
        "net_profit_margin_pct": "Net Profit Margin",
        "operating_profit_margin_pct": "Operating Margin",
        "return_on_equity_pct": "ROE",
        "debt_to_equity": "Debt / Equity",
        "interest_coverage": "Interest Coverage",
        "asset_turnover": "Asset Turnover",
        "free_cash_flow_cr": "Free Cash Flow",
        "earnings_per_share": "EPS",
        "book_value_per_share": "Book Value / Share",
        "dividend_payout_ratio_pct": "Dividend Payout",
    }

    correlation = correlation.rename(
        index=display_names,
        columns=display_names,
    )

    plt.figure(
        figsize=(13, 10)
    )

    sns.heatmap(
        correlation,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        center=0,
        square=True,
        linewidths=0.5,
        cbar_kws={
            "label": "Pearson Correlation"
        },
    )

    plt.title(
        "Nifty 100 — Latest-Year KPI Correlation Matrix"
    )

    plt.xticks(
        rotation=45,
        ha="right",
    )

    plt.yticks(
        rotation=0,
    )

    plt.tight_layout()

    plt.savefig(
        CORRELATION_HEATMAP,
        dpi=180,
        bbox_inches="tight",
    )

    plt.close()

    logger.info(
        "Correlation heatmap saved: %s",
        CORRELATION_HEATMAP,
    )

    return correlation


# ============================================================
# OUTLIER DETECTION
# ============================================================

def generate_outlier_report(latest):
    """
    Compute sector-wise Z-scores.

    Flag company if ANY KPI has |Z| > 3.
    """

    logger.info(
        "Running sector-wise outlier detection..."
    )

    data = latest.copy()

    outlier_records = []

    for sector, sector_df in data.groupby(
        "broad_sector"
    ):

        sector_df = sector_df.copy()

        for metric in CORRELATION_KPIS:

            values = numeric(
                sector_df[metric]
            )

            mean = values.mean()
            std = values.std(
                ddof=0
            )

            if pd.isna(std) or std == 0:
                z_scores = pd.Series(
                    0.0,
                    index=sector_df.index,
                )
            else:
                z_scores = (
                    values - mean
                ) / std

            for idx in sector_df.index:

                value = values.loc[idx]

                if pd.isna(value):
                    continue

                z = float(
                    z_scores.loc[idx]
                )

                if abs(z) > 3:

                    outlier_records.append(
                        {
                            "company_id":
                                sector_df.loc[
                                    idx,
                                    "company_id",
                                ],
                            "broad_sector":
                                sector,
                            "metric":
                                metric,
                            "value":
                                round(
                                    float(value),
                                    4,
                                ),
                            "sector_mean":
                                round(
                                    float(mean),
                                    4,
                                ),
                            "sector_std":
                                round(
                                    float(std),
                                    4,
                                ),
                            "z_score":
                                round(
                                    z,
                                    4,
                                ),
                            "absolute_z_score":
                                round(
                                    abs(z),
                                    4,
                                ),
                        }
                    )

    result = pd.DataFrame(
        outlier_records
    )

    if not result.empty:

        result = result.sort_values(
            [
                "company_id",
                "absolute_z_score",
            ],
            ascending=[
                True,
                False,
            ],
        )

    result.to_csv(
        OUTLIER_FILE,
        index=False,
    )

    logger.info(
        "Outlier report saved: %s",
        OUTLIER_FILE,
    )

    return result


# ============================================================
# PORTFOLIO STATISTICS
# ============================================================

def generate_portfolio_stats(latest):
    """
    Generate P10, P25, P50, P75, P90, Mean and Std
    for all 10 KPIs.
    """

    logger.info(
        "Generating portfolio statistics..."
    )

    rows = []

    for metric in CORRELATION_KPIS:

        values = numeric(
            latest[metric]
        ).dropna()

        if values.empty:
            continue

        rows.append(
            {
                "kpi": metric,
                "p10": round(
                    float(
                        values.quantile(0.10)
                    ),
                    4,
                ),
                "p25": round(
                    float(
                        values.quantile(0.25)
                    ),
                    4,
                ),
                "p50": round(
                    float(
                        values.quantile(0.50)
                    ),
                    4,
                ),
                "p75": round(
                    float(
                        values.quantile(0.75)
                    ),
                    4,
                ),
                "p90": round(
                    float(
                        values.quantile(0.90)
                    ),
                    4,
                ),
                "mean": round(
                    float(
                        values.mean()
                    ),
                    4,
                ),
                "std": round(
                    float(
                        values.std(
                            ddof=1
                        )
                    ),
                    4,
                ),
                "non_null_count": int(
                    values.count()
                ),
            }
        )

    result = pd.DataFrame(rows)

    result.to_csv(
        PORTFOLIO_STATS_FILE,
        index=False,
    )

    logger.info(
        "Portfolio statistics saved: %s",
        PORTFOLIO_STATS_FILE,
    )

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    logger.info(
        "Starting Day 37 cluster profiling..."
    )

    # --------------------------------------------------------
    # LOAD CLUSTERS
    # --------------------------------------------------------

    if not CLUSTER_FILE.exists():

        raise FileNotFoundError(
            "output/cluster_labels.csv not found. "
            "Run Day 36 clustering first."
        )

    clusters = pd.read_csv(
        CLUSTER_FILE
    )

    logger.info(
        "Cluster labels loaded: %d rows",
        len(clusters),
    )

    # --------------------------------------------------------
    # LOAD SECTORS
    # --------------------------------------------------------

    sectors = load_excel(
        SECTORS_FILE,
        header=0,
    )

    sectors = sectors[
        [
            "company_id",
            "broad_sector",
        ]
    ].drop_duplicates(
        subset=["company_id"]
    )

    # --------------------------------------------------------
    # LOAD RATIOS
    # --------------------------------------------------------

    ratios = load_excel(
        RATIOS_FILE,
        header=0,
    )

    latest = latest_year_rows(
        ratios
    )

    # --------------------------------------------------------
    # MERGE SECTOR
    # --------------------------------------------------------

    latest = latest.merge(
        sectors,
        on="company_id",
        how="left",
    )

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if len(clusters) != 92:

        raise ValueError(
            f"Expected 92 cluster rows, got {len(clusters)}"
        )

    if len(latest) != 92:

        raise ValueError(
            f"Expected 92 latest ratio rows, got {len(latest)}"
        )

    # --------------------------------------------------------
    # CLUSTER PROFILE
    # --------------------------------------------------------

    logger.info(
        "Profiling clusters..."
    )

    # Existing cluster labels already contain the final
    # cluster assignments. We profile the available five
    # features from the clustering dataset where present.

    profile = profile_clusters(
        clusters,
        latest,
    )

    # --------------------------------------------------------
    # IMPORTANT:
    # Revenue/FCF CAGR are not stored in cluster_labels.csv.
    # Therefore use clustering output names and preserve
    # the statistical structure without inventing values.
    # --------------------------------------------------------

    # If feature columns aren't present, create explicit
    # placeholders rather than silently fabricating metrics.
    for feature in CLUSTER_FEATURES:

        mean_col = (
            f"{feature}_mean"
        )

        median_col = (
            f"{feature}_median"
        )

        if mean_col not in profile.columns:
            profile[mean_col] = np.nan

        if median_col not in profile.columns:
            profile[median_col] = np.nan

    # --------------------------------------------------------
    # CLUSTER NAMES
    # --------------------------------------------------------

    names = {}

    # Start with existing Day 36 names.
    if "cluster_name" in clusters.columns:

        existing = (
            clusters[
                [
                    "cluster_id",
                    "cluster_name",
                ]
            ]
            .drop_duplicates(
                subset=["cluster_id"]
            )
        )

        names = dict(
            zip(
                existing["cluster_id"].astype(int),
                existing["cluster_name"].astype(str),
            )
        )

    # Keep names deterministic and descriptive.
    fallback_names = [
        "High-Quality Compounders",
        "Defensive Quality",
        "Emerging Growth",
        "Leveraged / Turnaround",
        "Value / Cyclical",
    ]

    for cluster_id in sorted(
        clusters["cluster_id"].unique()
    ):

        cluster_id = int(cluster_id)

        if (
            cluster_id not in names
            or not names[cluster_id]
            or names[cluster_id].startswith(
                "Cluster "
            )
        ):

            names[
                cluster_id
            ] = fallback_names[
                cluster_id
                % len(fallback_names)
            ]

    # Add names to profile.
    profile["cluster_name"] = (
        profile["cluster_id"]
        .map(names)
    )

    # Reorder.
    cols = [
        "cluster_id",
        "cluster_name",
        "company_count",
    ]

    remaining_cols = [
        col
        for col in profile.columns
        if col not in cols
    ]

    profile = profile[
        cols + remaining_cols
    ]

    profile.to_csv(
        CLUSTER_PROFILE_FILE,
        index=False,
    )

    # Update cluster labels with names.
    clusters["cluster_name"] = (
        clusters["cluster_id"]
        .map(names)
    )

    clusters = clusters.sort_values(
        "company_id"
    ).reset_index(drop=True)

    clusters.to_csv(
        CLUSTER_FILE,
        index=False,
    )

    # --------------------------------------------------------
    # CORRELATION
    # --------------------------------------------------------

    correlation = (
        generate_correlation_heatmap(
            latest
        )
    )

    # --------------------------------------------------------
    # OUTLIERS
    # --------------------------------------------------------

    outliers = generate_outlier_report(
        latest
    )

    # --------------------------------------------------------
    # PORTFOLIO STATS
    # --------------------------------------------------------

    portfolio_stats = (
        generate_portfolio_stats(
            latest
        )
    )

    # --------------------------------------------------------
    # CLUSTER MEMBERS
    # --------------------------------------------------------

    members = (
        clusters
        .merge(
            sectors,
            on="company_id",
            how="left",
        )
        .sort_values(
            [
                "cluster_id",
                "company_id",
            ]
        )
    )

    print()
    print("=" * 70)
    print("DAY 37 — CLUSTER PROFILING & STATISTICS")
    print("=" * 70)

    print(
        f"Companies              : {len(clusters)}"
    )

    print(
        f"Clusters               : "
        f"{clusters['cluster_id'].nunique()}"
    )

    print()
    print("CLUSTER DISTRIBUTION")
    print("-" * 70)

    distribution = (
        clusters
        .groupby(
            [
                "cluster_id",
                "cluster_name",
            ]
        )
        .size()
        .reset_index(
            name="companies"
        )
    )

    print(
        distribution.to_string(
            index=False
        )
    )

    print()
    print("CLUSTER MEMBERS")
    print("-" * 70)

    for cluster_id in sorted(
        clusters["cluster_id"].unique()
    ):

        cluster_rows = members[
            members["cluster_id"]
            == cluster_id
        ]

        cluster_name = cluster_rows.iloc[0][
            "cluster_name"
        ]

        tickers = ", ".join(
            cluster_rows[
                "company_id"
            ].astype(str)
            .tolist()
        )

        print(
            f"{cluster_id} | "
            f"{cluster_name} | "
            f"{len(cluster_rows)} companies"
        )

        print(
            f"    {tickers}"
        )

    print()
    print("OUTPUT VALIDATION")
    print("-" * 70)

    print(
        f"Cluster profile CSV    : "
        f"{CLUSTER_PROFILE_FILE}"
    )

    print(
        f"Correlation heatmap    : "
        f"{CORRELATION_HEATMAP}"
    )

    print(
        f"Outlier report         : "
        f"{OUTLIER_FILE}"
    )

    print(
        f"Portfolio stats        : "
        f"{PORTFOLIO_STATS_FILE}"
    )

    print()
    print(
        f"Correlation matrix     : "
        f"{correlation.shape}"
    )

    print(
        f"Outlier rows           : "
        f"{len(outliers)}"
    )

    print(
        f"Portfolio KPI rows     : "
        f"{len(portfolio_stats)}"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # FINAL STATUS
    # --------------------------------------------------------

    status = (
        len(clusters) == 92
        and clusters["cluster_id"]
        .nunique() == 5
        and len(profile) == 5
        and correlation.shape == (10, 10)
        and CORRELATION_HEATMAP.exists()
        and OUTLIER_FILE.exists()
        and PORTFOLIO_STATS_FILE.exists()
        and len(portfolio_stats) == 10
    )

    print(
        "STATUS                : "
        + ("PASS" if status else "FAIL")
    )

    print("=" * 70)

    if not status:
        raise RuntimeError(
            "Day 37 validation failed."
        )


if __name__ == "__main__":
    main()