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
# Data
# =====================================================

from src.dashboard.utils.data import market_cap


# =====================================================
# Page Config
# =====================================================

st.set_page_config(
    page_title="Market Capitalization",
    layout="wide",
)

st.title("💰 Market Capitalization")
st.caption("Latest market capitalization across Nifty 100 companies.")


# =====================================================
# Load Data
# =====================================================

df = market_cap().copy()


# =====================================================
# Numeric Cleaning
# =====================================================

df["market_cap_crore"] = pd.to_numeric(
    df["market_cap_crore"],
    errors="coerce",
)


# =====================================================
# Latest Record for Each Company
# =====================================================

latest = (
    df.sort_values("year")
    .groupby("company_id", as_index=False)
    .tail(1)
    .copy()
)


latest = latest.dropna(
    subset=["market_cap_crore"]
)


# =====================================================
# KPIs
# =====================================================

col1, col2, col3 = st.columns(3)

col1.metric(
    "Companies",
    latest["company_id"].nunique(),
)

col2.metric(
    "Total Market Cap",
    f"₹{latest['market_cap_crore'].sum():,.0f} Cr",
)

col3.metric(
    "Median Market Cap",
    f"₹{latest['market_cap_crore'].median():,.0f} Cr",
)


# =====================================================
# Top Companies Chart
# =====================================================

st.subheader("Latest Market Capitalization")

chart_df = latest.sort_values(
    "market_cap_crore",
    ascending=False,
).head(20)


fig = px.bar(
    chart_df,
    x="company_id",
    y="market_cap_crore",
    title="Top 20 Companies by Market Capitalization",
    labels={
        "company_id": "Company",
        "market_cap_crore": "Market Cap (₹ Crore)",
    },
)

fig.update_layout(
    xaxis_tickangle=-45,
    height=600,
)

st.plotly_chart(
    fig,
    width="stretch",
)


# =====================================================
# Full Data
# =====================================================

st.subheader("Market Capitalization Details")

display_df = latest.sort_values(
    "market_cap_crore",
    ascending=False,
)


st.dataframe(
    display_df,
    hide_index=True,
    width="stretch",
)


# =====================================================
# CSV Download
# =====================================================

csv = display_df.to_csv(
    index=False
).encode("utf-8")


st.download_button(
    label="⬇ Download Market Cap CSV",
    data=csv,
    file_name="market_cap.csv",
    mime="text/csv",
)