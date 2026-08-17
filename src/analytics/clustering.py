"""
Day 36 — KMeans Clustering

Clusters 92 Nifty 100 companies into 5 financial archetypes.

Features:
- return_on_equity_pct
- debt_to_equity
- revenue_cagr_5yr
- fcf_cagr_5yr
- operating_profit_margin_pct

Processing:
1. Load financial ratios, sectors and analysis data
2. Calculate 5-year FCF CAGR from cashflow data
3. Get 5-year revenue CAGR from analysis.xlsx / analysis_parsed.csv
4. Impute missing values using sector medians
5. StandardScaler
6. KMeans(n_clusters=5, random_state=42)
7. Generate elbow plot for k=2..10
8. Generate cluster_labels.csv
"""

from pathlib import Path
import logging

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


# ============================================================
# CONFIG
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = ROOT / "data" / "raw"
OUTPUT_DIR = ROOT / "output"
REPORTS_DIR = ROOT / "reports"

RATIOS_FILE = RAW_DIR / "financial_ratios.xlsx"
SECTORS_FILE = RAW_DIR / "sectors.xlsx"
ANALYSIS_FILE = RAW_DIR / "analysis.xlsx"
CASHFLOW_FILE = RAW_DIR / "cashflow.xlsx"

ANALYSIS_PARSED_FILE = OUTPUT_DIR / "analysis_parsed.csv"

CLUSTER_OUTPUT = OUTPUT_DIR / "cluster_labels.csv"
ELBOW_OUTPUT = REPORTS_DIR / "elbow_plot.png"


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
    df = df.copy()

    df.columns = [
        str(col).strip().lower().replace(" ", "_").replace("-", "_")
        for col in df.columns
    ]

    return df


def numeric(series):
    return pd.to_numeric(series, errors="coerce")


def load_excel(path, header=0):
    logger.info("Loading %s", path.name)

    df = pd.read_excel(path, header=header)
    df = clean_columns(df)

    logger.info(
        "%s shape: %s",
        path.name,
        df.shape,
    )

    return df


# ============================================================
# FCF CAGR
# ============================================================

def calculate_fcf_cagr(cashflow):
    """
    Calculate approximately 5-year FCF CAGR per company.

    FCF = operating_activity + investing_activity

    Uses earliest and latest available positive FCF values
    within the historical data.
    """

    required = {
        "company_id",
        "year",
        "operating_activity",
        "investing_activity",
    }

    missing = required - set(cashflow.columns)

    if missing:
        raise ValueError(
            f"cashflow.xlsx missing columns: {sorted(missing)}"
        )

    cf = cashflow.copy()

    cf["operating_activity"] = numeric(
        cf["operating_activity"]
    )

    cf["investing_activity"] = numeric(
        cf["investing_activity"]
    )

    cf["fcf"] = (
        cf["operating_activity"]
        + cf["investing_activity"]
    )

    # Extract numeric year where possible.
    year_text = (
        cf["year"]
        .astype(str)
        .str.extract(r"(\d{4})", expand=False)
    )

    cf["year_num"] = pd.to_numeric(
        year_text,
        errors="coerce",
    )

    records = []

    for company_id, group in cf.groupby("company_id"):

        group = group.dropna(
            subset=["year_num", "fcf"]
        ).sort_values("year_num")

        if len(group) < 2:
            records.append(
                {
                    "company_id": company_id,
                    "fcf_cagr_5yr": np.nan,
                }
            )
            continue

        # Prefer approximately 5-year interval.
        latest = group.iloc[-1]

        candidates = group[
            group["year_num"]
            <= latest["year_num"] - 5
        ]

        if candidates.empty:
            # Not enough history.
            records.append(
                {
                    "company_id": company_id,
                    "fcf_cagr_5yr": np.nan,
                }
            )
            continue

        start = candidates.iloc[-1]

        start_fcf = float(start["fcf"])
        end_fcf = float(latest["fcf"])

        years = (
            float(latest["year_num"])
            - float(start["year_num"])
        )

        # CAGR is only mathematically meaningful
        # for positive start/end values.
        if (
            years <= 0
            or start_fcf <= 0
            or end_fcf <= 0
        ):
            cagr = np.nan

        else:
            cagr = (
                (end_fcf / start_fcf)
                ** (1 / years)
                - 1
            ) * 100

        records.append(
            {
                "company_id": company_id,
                "fcf_cagr_5yr": cagr,
            }
        )

    result = pd.DataFrame(records)

    logger.info(
        "FCF CAGR calculated for %d companies",
        result["company_id"].nunique(),
    )

    return result


# ============================================================
# REVENUE CAGR
# ============================================================

def get_revenue_cagr(analysis_parsed):
    """
    Extract 5-year compounded sales growth
    from analysis_parsed.csv.
    """

    required = {
        "company_id",
        "metric_type",
        "period_years",
        "value_pct",
    }

    missing = required - set(analysis_parsed.columns)

    if missing:
        raise ValueError(
            "analysis_parsed.csv missing columns: "
            f"{sorted(missing)}"
        )

    df = analysis_parsed.copy()

    df["period_years"] = numeric(
        df["period_years"]
    )

    df["value_pct"] = numeric(
        df["value_pct"]
    )

    result = df[
        (
            df["metric_type"]
            .astype(str)
            .str.lower()
            .eq("compounded_sales_growth")
        )
        &
        (
            df["period_years"] == 5
        )
    ].copy()

    result = result[
        [
            "company_id",
            "value_pct",
        ]
    ].rename(
        columns={
            "value_pct": "revenue_cagr_5yr"
        }
    )

    # If duplicate company rows exist, keep latest occurrence.
    result = result.drop_duplicates(
        subset=["company_id"],
        keep="last",
    )

    logger.info(
        "Revenue CAGR available for %d companies",
        result["company_id"].nunique(),
    )

    return result


# ============================================================
# CLUSTER NAMES
# ============================================================

def assign_cluster_names(cluster_summary):
    """
    Assign human-readable archetype names based on
    standardized cluster characteristics.

    Names are deterministic because clusters are ranked
    by financial characteristics rather than raw KMeans IDs.
    """

    summary = cluster_summary.copy()

    # Higher quality score:
    # high ROE + high revenue growth + high OPM
    # and low debt.
    summary["quality_score"] = (
        summary["return_on_equity_pct_z"]
        + summary["revenue_cagr_5yr_z"]
        + summary["operating_profit_margin_pct_z"]
        - summary["debt_to_equity_z"]
    )

    summary = summary.sort_values(
        "quality_score",
        ascending=False,
    )

    names = [
        "High Growth Leaders",
        "Quality Compounders",
        "Balanced Performers",
        "Leveraged Growth",
        "Value / Recovery",
    ]

    mapping = {}

    for cluster_id, name in zip(
        summary["cluster_id"],
        names,
    ):
        mapping[int(cluster_id)] = name

    return mapping


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
        "Starting Day 36 KMeans clustering..."
    )

    # --------------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------------

    ratios = load_excel(
        RATIOS_FILE,
        header=0,
    )

    sectors = load_excel(
        SECTORS_FILE,
        header=0,
    )

    cashflow = load_excel(
        CASHFLOW_FILE,
        header=1,
    )

    if ANALYSIS_PARSED_FILE.exists():

        analysis_parsed = pd.read_csv(
            ANALYSIS_PARSED_FILE
        )

    else:

        raise FileNotFoundError(
            "output/analysis_parsed.csv not found"
        )

    # --------------------------------------------------------
    # PREPARE RATIOS
    # --------------------------------------------------------

    ratio_features = [
        "return_on_equity_pct",
        "debt_to_equity",
        "operating_profit_margin_pct",
    ]

    missing_ratio_features = [
        col
        for col in ratio_features
        if col not in ratios.columns
    ]

    if missing_ratio_features:

        raise ValueError(
            "financial_ratios.xlsx missing columns: "
            f"{missing_ratio_features}"
        )

    ratios = ratios.copy()

    for col in ratio_features:
        ratios[col] = numeric(
            ratios[col]
        )

    # Latest available observation per company.
    ratios["year_sort"] = (
        ratios["year"]
        .astype(str)
        .str.extract(
            r"(\d{4})",
            expand=False,
        )
    )

    ratios["year_sort"] = pd.to_numeric(
        ratios["year_sort"],
        errors="coerce",
    )

    ratios = ratios.sort_values(
        [
            "company_id",
            "year_sort",
        ]
    )

    latest_ratios = (
        ratios
        .groupby(
            "company_id",
            as_index=False,
        )
        .tail(1)
        .copy()
    )

    latest_ratios = latest_ratios[
        [
            "company_id",
            *ratio_features,
        ]
    ]

    # --------------------------------------------------------
    # SECTOR DATA
    # --------------------------------------------------------

    sector_required = {
        "company_id",
        "broad_sector",
    }

    missing_sector = (
        sector_required
        - set(sectors.columns)
    )

    if missing_sector:

        raise ValueError(
            "sectors.xlsx missing columns: "
            f"{sorted(missing_sector)}"
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
    # REVENUE CAGR
    # --------------------------------------------------------

    revenue_cagr = get_revenue_cagr(
        analysis_parsed
    )

    # --------------------------------------------------------
    # FCF CAGR
    # --------------------------------------------------------

    fcf_cagr = calculate_fcf_cagr(
        cashflow
    )

    # --------------------------------------------------------
    # MERGE
    # --------------------------------------------------------

    df = sectors.merge(
        latest_ratios,
        on="company_id",
        how="left",
    )

    df = df.merge(
        revenue_cagr,
        on="company_id",
        how="left",
    )

    df = df.merge(
        fcf_cagr,
        on="company_id",
        how="left",
    )

    logger.info(
        "Companies after merge: %d",
        len(df),
    )

    if len(df) != 92:

        raise ValueError(
            f"Expected 92 companies, got {len(df)}"
        )

    # --------------------------------------------------------
    # FEATURES
    # --------------------------------------------------------

    feature_cols = [
        "return_on_equity_pct",
        "debt_to_equity",
        "revenue_cagr_5yr",
        "fcf_cagr_5yr",
        "operating_profit_margin_pct",
    ]

    # --------------------------------------------------------
    # SECTOR MEDIAN IMPUTATION
    # --------------------------------------------------------

    logger.info(
        "Applying sector-median imputation..."
    )

    for col in feature_cols:

        df[col] = numeric(
            df[col]
        )

        sector_median = (
            df.groupby(
                "broad_sector"
            )[col]
            .transform("median")
        )

        df[col] = df[col].fillna(
            sector_median
        )

        # Fallback only if entire sector metric is missing.
        global_median = df[col].median()

        df[col] = df[col].fillna(
            global_median
        )

    remaining_missing = (
        df[feature_cols]
        .isna()
        .sum()
    )

    if remaining_missing.sum() > 0:

        raise ValueError(
            "Missing values remain after imputation:\n"
            f"{remaining_missing}"
        )

    # --------------------------------------------------------
    # STANDARD SCALER
    # --------------------------------------------------------

    X = df[feature_cols].copy()

    scaler = StandardScaler()

    X_scaled = scaler.fit_transform(X)

    scaled_df = pd.DataFrame(
        X_scaled,
        columns=feature_cols,
        index=df.index,
    )

    # --------------------------------------------------------
    # ELBOW PLOT
    # --------------------------------------------------------

    logger.info(
        "Generating elbow plot..."
    )

    inertias = []

    k_values = range(2, 11)

    for k in k_values:

        model = KMeans(
            n_clusters=k,
            random_state=42,
            n_init=20,
        )

        model.fit(X_scaled)

        inertias.append(
            model.inertia_
        )

    plt.figure(
        figsize=(9, 6)
    )

    plt.plot(
        list(k_values),
        inertias,
        marker="o",
    )

    plt.axvline(
        5,
        linestyle="--",
        label="Selected k = 5",
    )

    plt.xlabel(
        "Number of clusters (k)"
    )

    plt.ylabel(
        "Inertia"
    )

    plt.title(
        "KMeans Elbow Plot — Nifty 100"
    )

    plt.xticks(
        list(k_values)
    )

    plt.grid(
        alpha=0.3
    )

    plt.legend()

    plt.tight_layout()

    plt.savefig(
        ELBOW_OUTPUT,
        dpi=160,
        bbox_inches="tight",
    )

    plt.close()

    logger.info(
        "Elbow plot saved: %s",
        ELBOW_OUTPUT,
    )

    # --------------------------------------------------------
    # FINAL KMEANS
    # --------------------------------------------------------

    logger.info(
        "Running final KMeans with k=5..."
    )

    kmeans = KMeans(
        n_clusters=5,
        random_state=42,
        n_init=20,
    )

    labels = kmeans.fit_predict(
        X_scaled
    )

    df["cluster_id"] = labels

    # --------------------------------------------------------
    # DISTANCE FROM CENTROID
    # --------------------------------------------------------

    centroids = kmeans.cluster_centers_

    distances = []

    for idx, cluster_id in enumerate(labels):

        centroid = centroids[
            cluster_id
        ]

        distance = np.linalg.norm(
            X_scaled[idx] - centroid
        )

        distances.append(
            distance
        )

    df["distance_from_centroid"] = distances

    # --------------------------------------------------------
    # CLUSTER SUMMARY
    # --------------------------------------------------------

    summary_rows = []

    for cluster_id in range(5):

        mask = (
            df["cluster_id"]
            == cluster_id
        )

        if not mask.any():
            continue

        row = {
            "cluster_id": cluster_id,
        }

        for col in feature_cols:

            mean_value = (
                scaled_df.loc[
                    mask,
                    col,
                ].mean()
            )

            row[
                f"{col}_z"
            ] = mean_value

        summary_rows.append(
            row
        )

    cluster_summary = pd.DataFrame(
        summary_rows
    )

    cluster_names = assign_cluster_names(
        cluster_summary
    )

    df["cluster_name"] = (
        df["cluster_id"]
        .map(cluster_names)
    )

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    result = df[
        [
            "company_id",
            "cluster_id",
            "cluster_name",
            "distance_from_centroid",
        ]
    ].copy()

    result["cluster_id"] = (
        result["cluster_id"]
        .astype(int)
    )

    result[
        "distance_from_centroid"
    ] = result[
        "distance_from_centroid"
    ].round(6)

    result = result.sort_values(
        "company_id"
    ).reset_index(
        drop=True
    )

    result.to_csv(
        CLUSTER_OUTPUT,
        index=False,
    )

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    logger.info(
        "Cluster labels saved: %s",
        CLUSTER_OUTPUT,
    )

    print()
    print("=" * 70)
    print("DAY 36 — KMEANS CLUSTERING")
    print("=" * 70)
    print(
        f"Companies             : {len(result)}"
    )
    print(
        f"Clusters              : {result['cluster_id'].nunique()}"
    )
    print(
        f"Cluster IDs            : "
        f"{sorted(result['cluster_id'].unique().tolist())}"
    )
    print()
    print("Cluster distribution:")
    print(
        result["cluster_name"]
        .value_counts()
        .sort_index()
        .to_string()
    )
    print()
    print(
        f"Elbow plot            : {ELBOW_OUTPUT}"
    )
    print(
        f"Cluster output        : {CLUSTER_OUTPUT}"
    )
    print("=" * 70)

    if len(result) != 92:
        raise ValueError(
            "Validation failed: expected 92 companies"
        )

    if result["cluster_id"].nunique() != 5:
        raise ValueError(
            "Validation failed: expected 5 clusters"
        )

    if result["cluster_id"].min() != 0:
        raise ValueError(
            "Validation failed: cluster IDs must start at 0"
        )

    if result["cluster_id"].max() != 4:
        raise ValueError(
            "Validation failed: cluster IDs must end at 4"
        )

    if result[
        "distance_from_centroid"
    ].isna().any():

        raise ValueError(
            "Validation failed: missing centroid distances"
        )

    if not ELBOW_OUTPUT.exists():
        raise ValueError(
            "Validation failed: elbow plot missing"
        )

    print(
        "STATUS                : PASS"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()