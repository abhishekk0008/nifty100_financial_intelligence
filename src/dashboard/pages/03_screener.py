from pathlib import Path
import sys

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[3]

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.dashboard.utils.data import (
    companies,
    sectors,
    ratios,
    analysis,
    market_cap,
)

st.set_page_config(
    page_title="Stock Screener",
    layout="wide",
)

st.title("🔍 Nifty 100 Stock Screener")

# =====================================================
# Load Data
# =====================================================

companies_df = companies()
sector_df = sectors()
ratio_df = ratios()
analysis_df = analysis()
market_cap_df = market_cap()

# =====================================================
# Standardize Company IDs
# =====================================================

companies_df["id"] = companies_df["id"].astype(str).str.upper()

ratio_df["company_id"] = ratio_df["company_id"].astype(str).str.upper()

sector_df["company_id"] = sector_df["company_id"].astype(str).str.upper()

analysis_df["company_id"] = analysis_df["company_id"].astype(str).str.upper()

market_cap_df["company_id"] = market_cap_df["company_id"].astype(str).str.upper()


# =====================================================
# Latest Financial Year — Company-wise
# Handles Mar / Sep / other fiscal year endings
# =====================================================

ratio_df = ratio_df.copy()

# Extract financial year
ratio_df["year_num"] = (
    ratio_df["year"]
    .astype(str)
    .str.extract(r"(\d{4})")[0]
)

ratio_df["year_num"] = pd.to_numeric(
    ratio_df["year_num"],
    errors="coerce"
)

# Remove rows where year could not be identified
ratio_df = ratio_df.dropna(
    subset=["company_id", "year_num"]
).copy()

ratio_df["year_num"] = ratio_df["year_num"].astype(int)

# Keep latest available financial year for EACH company
ratio_df = (
    ratio_df
    .sort_values(
        ["company_id", "year_num"]
    )
    .drop_duplicates(
        subset="company_id",
        keep="last",
    )
    .copy()
)

print("=" * 60)
print("Latest financial year — company-wise")
print("Rows:", len(ratio_df))
print("Unique companies:", ratio_df["company_id"].nunique())
print("Duplicate rows remaining:",
      ratio_df.duplicated("company_id").sum())

print("=" * 60)

print(
    ratio_df[
        ["company_id", "year"]
    ]
    .sort_values("company_id")
    .to_string(index=False)
)

ratio_df.drop(
    columns=["year_num"],
    inplace=True
)

# =====================================================
# Debug
# =====================================================

print("=" * 60)
print("Latest financial year — company-wise")
print("Rows:", len(ratio_df))
print("Unique companies:", ratio_df["company_id"].nunique())
print(
    "Duplicate rows remaining:",
    ratio_df.duplicated("company_id").sum()
)
print("=" * 60)

print("Rows after latest year filter:", len(ratio_df))
print("Unique companies:", ratio_df["company_id"].nunique())

dup = ratio_df[
    ratio_df.duplicated(
        subset="company_id",
        keep=False,
    )
]

print("Duplicate rows remaining:", len(dup))

if len(dup):
    print(
        dup[
            [
                "company_id",
                "year",
            ]
        ]
    )

print("=" * 60)

# =====================================================
# Analysis Cleaning
# =====================================================

# Keep only latest (Last Year / 1 Year) record for each company
analysis_df = (
    analysis_df
    .assign(
        _order=analysis_df["compounded_sales_growth"].astype(str).str.extract(
            r"(10|5|3|1)\s*Year", expand=False
        ).map({"10": 1, "5": 2, "3": 3, "1": 4})
    )
    .sort_values(["company_id", "_order"])
    .drop_duplicates(subset="company_id", keep="last")
    .drop(columns="_order")
)

# Convert percentage strings to numeric
for col in [
    "compounded_sales_growth",
    "compounded_profit_growth",
]:
    analysis_df[col] = (
        analysis_df[col]
        .astype(str)
        .str.extract(r"(-?\d+\.?\d*)", expand=False)
        .astype(float)
    )
    
# =====================================================
# Market Cap Cleaning
# =====================================================

market_cap_df["year"] = pd.to_numeric(
    market_cap_df["year"],
    errors="coerce",
)

market_cap_df = (
    market_cap_df
    .sort_values(
        by=["company_id", "year"],
        ascending=[True, False],
    )
    .drop_duplicates(
        subset="company_id",
        keep="first",
    )
)

print("Market Cap Rows:", len(market_cap_df))

# =====================================================
# Sidebar Filters
# =====================================================

st.sidebar.header("Filters")

roe = st.sidebar.slider(
    "Minimum ROE (%)",
    0,
    50,
    15,
)

de = st.sidebar.slider(
    "Maximum Debt / Equity",
    0.0,
    5.0,
    1.0,
)

fcf = st.sidebar.slider(
    "Minimum Free Cash Flow (Cr)",
    -1000,
    10000,
    0,
)

sales_growth = st.sidebar.slider(
    "Revenue CAGR (%)",
    0,
    50,
    10,
)

profit_growth = st.sidebar.slider(
    "PAT CAGR (%)",
    0,
    50,
    10,
)

opm = st.sidebar.slider(
    "Minimum OPM (%)",
    0,
    70,
    15,
)

pe = st.sidebar.slider(
    "Maximum PE",
    0,
    150,
    40,
)

pb = st.sidebar.slider(
    "Maximum PB",
    0,
    20,
    10,
)

# =====================================================
# Remaining Sidebar Filters
# =====================================================

dividend = st.sidebar.slider(
    "Dividend Yield (%)",
    0.0,
    10.0,
    0.0,
)

icr = st.sidebar.slider(
    "Minimum Interest Coverage",
    0,
    30,
    2,
)

st.sidebar.markdown("---")
st.sidebar.subheader("Quick Presets")

c1, c2 = st.sidebar.columns(2)
c3, c4 = st.sidebar.columns(2)
c5, c6 = st.sidebar.columns(2)

quality = c1.button("Quality")
value = c2.button("Value")
growth = c3.button("Growth")
dividend_stock = c4.button("Dividend")
debt_free = c5.button("Debt-Free")
turnaround = c6.button("Turnaround")

if quality:
    roe = 20
    de = 0.5
    opm = 20
    pe = 50

elif value:
    pe = 20
    pb = 2
    dividend = 2

elif growth:
    sales_growth = 20
    profit_growth = 20

elif dividend_stock:
    dividend = 3

elif debt_free:
    de = 0.2

elif turnaround:
    profit_growth = 15
    fcf = 0

# =====================================================
# Merge All Data
# =====================================================

# Companies
filtered = ratio_df.merge(
    companies_df,
    left_on="company_id",
    right_on="id",
    how="left",
    suffixes=("", "_company"),
)

print("Rows after companies merge:", len(filtered))

# Sectors
filtered = filtered.merge(
    sector_df,
    on="company_id",
    how="left",
)

print("Rows after sectors merge:", len(filtered))

# Analysis
filtered = filtered.merge(
    analysis_df[
        [
            "company_id",
            "compounded_sales_growth",
            "compounded_profit_growth",
        ]
    ],
    on="company_id",
    how="left",
)

print("Rows after analysis merge:", len(filtered))

# Market Cap
filtered = filtered.merge(
    market_cap_df[
        [
            "company_id",
            "pe_ratio",
            "pb_ratio",
            "dividend_yield_pct",
        ]
    ],
    on="company_id",
    how="left",
)

print("Rows after market cap merge:", len(filtered))

# =====================================================
# Default Columns
# =====================================================

if "company_name" not in filtered.columns:
    filtered["company_name"] = filtered["company_id"]

if "broad_sector" not in filtered.columns:
    filtered["broad_sector"] = "Unknown"

# =====================================================
# Numeric Conversion
# =====================================================

numeric_cols = [
    "return_on_equity_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "compounded_sales_growth",
    "compounded_profit_growth",
    "operating_profit_margin_pct",
    "interest_coverage",
    "pe_ratio",
    "pb_ratio",
    "dividend_yield_pct",
]

for col in numeric_cols:

    if col in filtered.columns:

        filtered[col] = pd.to_numeric(
            filtered[col],
            errors="coerce",
        )

print("=" * 60)
print("Null Values")
print(filtered[numeric_cols].isna().sum())
print("=" * 60)

print("=" * 60)
print(filtered[numeric_cols].describe())
print("=" * 60)

print(filtered.shape)

# =====================================================
# IMPORTANT
# Don't fill NaN with zero.
# Missing values should survive filtering.
# =====================================================

st.write(filtered.columns.tolist())

# =====================================================
# Apply Filters
# =====================================================

print("Before filters:", len(filtered))

filtered = filtered[
    filtered["return_on_equity_pct"].isna()
    |
    (filtered["return_on_equity_pct"] >= roe)
]
print("After ROE:", len(filtered))

filtered = filtered[
    filtered["debt_to_equity"].isna()
    |
    (filtered["debt_to_equity"] <= de)
]
print("After Debt:", len(filtered))

filtered = filtered[
    filtered["free_cash_flow_cr"].isna()
    |
    (filtered["free_cash_flow_cr"] >= fcf)
]
print("After FCF:", len(filtered))

filtered = filtered[
    filtered["compounded_sales_growth"].isna()
    |
    (filtered["compounded_sales_growth"] >= sales_growth)
]
print("After Sales CAGR:", len(filtered))

filtered = filtered[
    filtered["compounded_profit_growth"].isna()
    |
    (filtered["compounded_profit_growth"] >= profit_growth)
]
print("After PAT CAGR:", len(filtered))

filtered = filtered[
    filtered["operating_profit_margin_pct"].isna()
    |
    (filtered["operating_profit_margin_pct"] >= opm)
]
print("After OPM:", len(filtered))

filtered = filtered[
    filtered["pe_ratio"].isna()
    |
    (filtered["pe_ratio"] <= pe)
]
print("After PE:", len(filtered))

filtered = filtered[
    filtered["pb_ratio"].isna()
    |
    (filtered["pb_ratio"] <= pb)
]
print("After PB:", len(filtered))

filtered = filtered[
    filtered["dividend_yield_pct"].isna()
    |
    (filtered["dividend_yield_pct"] >= dividend)
]
print("After Dividend:", len(filtered))

filtered = filtered[
    filtered["interest_coverage"].isna()
    |
    (filtered["interest_coverage"] >= icr)
]
print("After Interest Coverage:", len(filtered))

print("=" * 60)
print("Companies after PE filter")
print(
    filtered[
        [
            "company_id",
            "company_name",
            "pe_ratio",
            "pb_ratio",
        ]
    ].sort_values("pb_ratio")
)
print("=" * 60)

filtered = filtered[
    filtered["pb_ratio"] <= pb
]

# =====================================================
# Composite Score
# =====================================================

score_cols = [
    "return_on_equity_pct",
    "operating_profit_margin_pct",
    "interest_coverage",
    "compounded_sales_growth",
    "compounded_profit_growth",
]

filtered[score_cols] = filtered[score_cols].fillna(0)

filtered["Composite Score"] = (
    filtered[score_cols]
    .sum(axis=1)
)

filtered = filtered.sort_values(
    "Composite Score",
    ascending=False,
)

# =====================================================
# Display
# =====================================================

st.subheader(
    f"{len(filtered)} companies match your filters"
)

display_cols = [
    "company_id",
    "company_name",
    "broad_sector",
    "return_on_equity_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "compounded_sales_growth",
    "compounded_profit_growth",
    "operating_profit_margin_pct",
    "interest_coverage",
    "pe_ratio",
    "pb_ratio",
    "dividend_yield_pct",
    "Composite Score",
]

display_cols = [
    c for c in display_cols
    if c in filtered.columns
]

display = filtered[display_cols]

st.dataframe(
    display,
    width="stretch",
    hide_index=True,
)

# =====================================================
# Download CSV
# =====================================================

csv = display.to_csv(
    index=False,
).encode("utf-8")

st.download_button(
    label="⬇ Download CSV",
    data=csv,
    file_name="screened_companies.csv",
    mime="text/csv",
)