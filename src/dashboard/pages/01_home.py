from pathlib import Path
import sys

import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[3]

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.dashboard.utils.data import (
    companies,
    ratios,
    sectors,
)

st.set_page_config(
    page_title="Home",
    layout="wide",
)

st.title("📊 Nifty 100 Financial Intelligence Platform")

# -----------------------------
# Load Data
# -----------------------------

companies_df = companies()
ratios_df = ratios()
sectors_df = sectors()

# -----------------------------
# Sidebar
# -----------------------------

years = sorted(ratios_df["year"].dropna().unique())

selected_year = st.sidebar.selectbox(
    "Financial Year",
    years,
    index=len(years)-1,
)

latest = ratios_df[
    ratios_df["year"] == selected_year
].copy()

# -----------------------------
# Merge Company Names
# -----------------------------

latest = latest.merge(
    companies_df[
        [
            "id",
            "company_name",
            "roe_percentage",
            "roce_percentage",
        ]
    ],
    left_on="company_id",
    right_on="id",
    how="left",
)

# -----------------------------
# KPI Cards
# -----------------------------

c1,c2,c3,c4,c5,c6 = st.columns(6)

avg_roe = latest["return_on_equity_pct"].mean()

median_de = latest["debt_to_equity"].median()

median_rev = latest["asset_turnover"].median()

debt_free = (
    latest["debt_to_equity"]
    .fillna(999)
    .lt(0.01)
    .sum()
)

avg_roce = latest["roce_percentage"].mean()

total = latest["company_id"].nunique()

c1.metric("Average ROE",f"{avg_roe:.2f}%")
c2.metric("Average ROCE",f"{avg_roce:.2f}%")
c3.metric("Median D/E",f"{median_de:.2f}")
c4.metric("Companies",total)
c5.metric("Median Asset Turnover",f"{median_rev:.2f}")
c6.metric("Debt Free",debt_free)

st.divider()

left,right = st.columns([2,1])

# -----------------------------
# Donut Chart
# -----------------------------

with left:

    sector_count = (
    sectors_df.groupby("broad_sector")
    .size()
    .reset_index(name="Companies")
)

    fig = px.pie(
    sector_count,
    names="broad_sector",
    values="Companies",
    hole=0.55,
    title="Sector Distribution",
)

    st.plotly_chart(
    fig,
    width="stretch",
)

# -----------------------------
# Top Quality Companies
# -----------------------------

with right:

    latest["quality_score"] = (
        latest["return_on_equity_pct"].fillna(0)
        + latest["roce_percentage"].fillna(0)
        + latest["net_profit_margin_pct"].fillna(0)
    )

    top5 = (
        latest.sort_values(
            by="quality_score",
            ascending=False,
        )[[
            "company_name",
            "quality_score",
        ]].head(5)
    )

    st.subheader("Top 5 Quality Companies")

    st.dataframe(
        top5,
        hide_index=True,
        width="stretch",
    )