from pathlib import Path
import sys

import streamlit as st
import pandas as pd
import plotly.express as px


# =====================================================
# Project Path
# =====================================================

ROOT = Path(__file__).resolve().parents[3]

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


# =====================================================
# Data Imports
# =====================================================

from src.dashboard.utils.data import (
    sectors,
    profit_loss,
    ratios,
    market_cap,
)


# =====================================================
# Page Config
# =====================================================

st.set_page_config(
    page_title="Sector Analysis",
    layout="wide",
)

st.title("🏭 Sector Analysis")
st.caption("Explore sector-level financial performance and company positioning.")


# =====================================================
# Load Data
# =====================================================

sector_df = sectors()
pl_df = profit_loss()
ratio_df = ratios()
market_cap_df = market_cap()


# =====================================================
# Latest Year Data
# =====================================================

latest_pl_year = pl_df["year"].max()
latest_ratio_year = ratio_df["year"].max()
latest_market_cap_year = market_cap_df["year"].max()


pl_latest = pl_df[
    pl_df["year"] == latest_pl_year
].copy()

ratio_latest = ratio_df[
    ratio_df["year"] == latest_ratio_year
].copy()

market_cap_latest = market_cap_df[
    market_cap_df["year"] == latest_market_cap_year
].copy()


# =====================================================
# Build Company-Level Dataset
# =====================================================

df = sector_df[
    [
        "company_id",
        "broad_sector",
        "sub_sector",
        "index_weight_pct",
    ]
].copy()


df = df.merge(
    pl_latest[
        [
            "company_id",
            "sales",
        ]
    ],
    on="company_id",
    how="left",
)


df = df.merge(
    ratio_latest[
        [
            "company_id",
            "return_on_equity_pct",
        ]
    ],
    on="company_id",
    how="left",
)


df = df.merge(
    market_cap_latest[
        [
            "company_id",
            "market_cap_crore",
        ]
    ],
    on="company_id",
    how="left",
)


# =====================================================
# Numeric Cleaning
# =====================================================

numeric_cols = [
    "sales",
    "return_on_equity_pct",
    "market_cap_crore",
    "index_weight_pct",
]

for col in numeric_cols:
    df[col] = pd.to_numeric(
        df[col],
        errors="coerce",
    )


# =====================================================
# Sector Selector
# =====================================================

sector_options = ["All Sectors"] + sorted(
    df["broad_sector"]
    .dropna()
    .unique()
    .tolist()
)

selected_sector = st.selectbox(
    "Select Sector",
    sector_options,
)


if selected_sector == "All Sectors":
    filtered_df = df.copy()
else:
    filtered_df = df[
        df["broad_sector"] == selected_sector
    ].copy()


# =====================================================
# KPI Summary
# =====================================================

st.subheader("Sector Overview")

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

kpi1.metric(
    "Companies",
    len(filtered_df),
)

kpi2.metric(
    "Avg ROE",
    f"{filtered_df['return_on_equity_pct'].mean():.2f}%",
)

kpi3.metric(
    "Total Sales",
    f"₹{filtered_df['sales'].sum():,.0f}",
)

kpi4.metric(
    "Total Market Cap",
    f"₹{filtered_df['market_cap_crore'].sum():,.0f} Cr",
)


# =====================================================
# Bubble Chart
# Revenue vs ROE
# =====================================================

st.subheader("Revenue vs ROE")

bubble_df = filtered_df.dropna(
    subset=[
        "sales",
        "return_on_equity_pct",
        "market_cap_crore",
        "sub_sector",
    ]
).copy()


if bubble_df.empty:

    st.warning(
        "Not enough data available to create the sector bubble chart."
    )

else:

    fig = px.scatter(
        bubble_df,
        x="sales",
        y="return_on_equity_pct",
        size="market_cap_crore",
        color="sub_sector",
        hover_name="company_id",
        hover_data={
            "sales": ":,.0f",
            "return_on_equity_pct": ":.2f",
            "market_cap_crore": ":,.0f",
            "sub_sector": True,
        },
        title="Revenue vs ROE by Company",
        labels={
            "sales": "Revenue / Sales",
            "return_on_equity_pct": "ROE (%)",
            "market_cap_crore": "Market Cap (₹ Cr)",
            "sub_sector": "Sub-sector",
        },
        size_max=45,
    )

    fig.update_layout(
        height=600,
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )


# =====================================================
# Sector KPI Bar Chart
# =====================================================

st.subheader("Sector KPI Comparison")


sector_kpi = (
    df.groupby("broad_sector")
    .agg(
        Companies=("company_id", "nunique"),
        Avg_ROE=("return_on_equity_pct", "mean"),
        Avg_Index_Weight=("index_weight_pct", "mean"),
    )
    .reset_index()
)


fig_kpi = px.bar(
    sector_kpi,
    x="broad_sector",
    y="Avg_ROE",
    text="Companies",
    title="Average ROE by Sector",
    labels={
        "broad_sector": "Sector",
        "Avg_ROE": "Average ROE (%)",
    },
)


fig_kpi.update_traces(
    textposition="outside",
)


fig_kpi.update_layout(
    height=500,
)


st.plotly_chart(
    fig_kpi,
    width="stretch",
)


# =====================================================
# Sector Details
# =====================================================

st.subheader("Sector Details")


display_df = filtered_df[
    [
        "company_id",
        "broad_sector",
        "sub_sector",
        "sales",
        "return_on_equity_pct",
        "market_cap_crore",
        "index_weight_pct",
    ]
].sort_values(
    "market_cap_crore",
    ascending=False,
)


st.dataframe(
    display_df,
    hide_index=True,
    width="stretch",
)