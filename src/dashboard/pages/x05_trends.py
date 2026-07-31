from pathlib import Path
import sys

import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[3]

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.dashboard.utils.data import (
    companies,
    profit_loss,
)

st.set_page_config(
    page_title="Financial Trends",
    layout="wide",
)

st.title("📈 Financial Trends")

companies_df = companies()
pl_df = profit_loss()

company = st.selectbox(
    "Select Company",
    sorted(companies_df["company_name"].unique())
)

company_id = companies_df.loc[
    companies_df["company_name"] == company,
    "id"
].iloc[0]

df = (
    pl_df[
        pl_df["company_id"] == company_id
    ]
    .sort_values("year")
)

metric = st.selectbox(
    "Metric",
    [
        "sales",
        "operating_profit",
        "net_profit",
        "eps",
        "dividend_payout",
    ]
)

fig = px.line(
    df,
    x="year",
    y=metric,
    markers=True,
    title=f"{metric.replace('_',' ').title()} Trend"
)

st.plotly_chart(
    fig,
    width="stretch",
)

st.dataframe(
    df[
        [
            "year",
            "sales",
            "operating_profit",
            "net_profit",
            "eps",
            "dividend_payout",
        ]
    ],
    hide_index=True,
    width="stretch",
)