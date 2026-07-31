from pathlib import Path
import sys

import streamlit as st
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.dashboard.utils.data import (
    companies,
    peer_groups,
    ratios,
)

st.set_page_config(page_title="Peer Comparison", layout="wide")

st.title("🤝 Peer Comparison")

companies_df = companies()
peers_df = peer_groups()
ratios_df = ratios()

company_list = sorted(companies_df["company_name"].dropna().unique())

selected_company = st.selectbox(
    "Select Company",
    company_list,
)

company_id = companies_df.loc[
    companies_df["company_name"] == selected_company,
    "id",
].iloc[0]

peer_row = peers_df[
    peers_df["company_id"] == company_id
]

if peer_row.empty:
    st.warning("No peer group found.")
    st.stop()

sector = peer_row.iloc[0]["sector"]

peer_ids = peers_df[
    peers_df["sector"] == sector
]["company_id"].unique()

latest_year = ratios_df["year"].max()

peer_ratios = ratios_df[
    (ratios_df["company_id"].isin(peer_ids))
    &
    (ratios_df["year"] == latest_year)
]

peer_ratios = peer_ratios.merge(
    companies_df[["id", "company_name"]],
    left_on="company_id",
    right_on="id",
    how="left",
)

cols = [
    "company_name",
    "return_on_equity_pct",
    "net_profit_margin_pct",
    "debt_to_equity",
    "asset_turnover",
    "earnings_per_share",
]

cols = [c for c in cols if c in peer_ratios.columns]

st.dataframe(
    peer_ratios[cols].sort_values(
        "return_on_equity_pct",
        ascending=False,
    ),
    hide_index=True,
    width="stretch",
)

csv = peer_ratios[cols].to_csv(index=False).encode("utf-8")

st.download_button(
    "⬇ Download Peer Comparison",
    csv,
    "peer_comparison.csv",
    "text/csv",
)