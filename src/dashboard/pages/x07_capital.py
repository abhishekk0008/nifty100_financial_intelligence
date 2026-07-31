from pathlib import Path
import sys

import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[3]

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.dashboard.utils.data import market_cap

st.set_page_config(
    page_title="Market Capitalization",
    layout="wide",
)

st.title("💰 Market Capitalization")

df = market_cap()

latest = (
    df.sort_values("year")
      .groupby("company_id")
      .tail(1)
)

fig = px.bar(
    latest.sort_values(
        "market_cap_crore",
        ascending=False
    ),
    x="company_id",
    y="market_cap_crore",
    title="Latest Market Capitalization (₹ Crore)"
)

st.plotly_chart(
    fig,
    width="stretch",
)

st.dataframe(
    latest,
    hide_index=True,
    width="stretch",
)