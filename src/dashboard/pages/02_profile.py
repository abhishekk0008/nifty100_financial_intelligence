from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[3]

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.dashboard.utils.data import (
    companies,
    ratios,
    analysis,
    pros_cons,
)

st.set_page_config(page_title="Company Profile", layout="wide")

st.title("👤 Company Profile")

companies_df = companies()
ratios_df = ratios()
analysis_df = analysis()
pros_df = pros_cons()

company = st.selectbox(
    "Select Company",
    companies_df["company_name"].sort_values().unique()
)

company_row = companies_df[
    companies_df["company_name"] == company
].iloc[0]

company_id = company_row["id"]

st.header(company_row["company_name"])

c1, c2, c3 = st.columns(3)

c1.metric("ROE", f"{company_row['roe_percentage']:.2f}%")
c2.metric("ROCE", f"{company_row['roce_percentage']:.2f}%")
c3.metric("Book Value", f"{company_row['book_value']:.2f}")

st.markdown("---")

st.subheader("About Company")
st.write(company_row["about_company"])

ratio = ratios_df[
    ratios_df["company_id"] == company_id
].sort_values("year", ascending=False)

if not ratio.empty:

    st.subheader("Financial Ratios")

    st.dataframe(
        ratio[
            [
                "year",
                "return_on_equity_pct",
                "net_profit_margin_pct",
                "debt_to_equity",
                "asset_turnover",
                "earnings_per_share",
            ]
        ],
        hide_index=True,
        width="stretch",
    )

growth = analysis_df[
    analysis_df["company_id"] == company_id
]

if not growth.empty:

    st.subheader("Growth Analysis")

    st.dataframe(
        growth,
        hide_index=True,
        width="stretch",
    )

pc = pros_df[
    pros_df["company_id"] == company_id
]

if not pc.empty:

    left, right = st.columns(2)

    with left:
        st.subheader("Pros")
        for p in pc["pros"].dropna():
            st.success(p)

    with right:
        st.subheader("Cons")
        for c in pc["cons"].dropna():
            st.error(c)