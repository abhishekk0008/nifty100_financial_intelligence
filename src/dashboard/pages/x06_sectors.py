from pathlib import Path
import sys

import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[3]

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.dashboard.utils.data import (
    sectors,
)

st.set_page_config(
    page_title="Sector Analysis",
    layout="wide",
)

st.title("🏭 Sector Analysis")

sector_df = sectors()

sector_summary = (
    sector_df.groupby("broad_sector")
    .agg(
        Companies=("company_id", "count"),
        Avg_Weight=("index_weight_pct", "mean"),
    )
    .reset_index()
)

fig = px.bar(
    sector_summary,
    x="broad_sector",
    y="Companies",
    title="Companies by Sector",
)

st.plotly_chart(
    fig,
    width="stretch",
)

fig2 = px.pie(
    sector_summary,
    names="broad_sector",
    values="Avg_Weight",
    hole=0.5,
    title="Average Index Weight"
)

st.plotly_chart(
    fig2,
    width="stretch",
)

st.subheader("Sector Details")

st.dataframe(
    sector_df,
    hide_index=True,
    width="stretch",
)