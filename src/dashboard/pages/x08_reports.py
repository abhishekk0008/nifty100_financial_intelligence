from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[3]

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.dashboard.utils.data import (
    companies,
    analysis,
    pros_cons,
)

st.set_page_config(
    page_title="Company Reports",
    layout="wide",
)

st.title("📄 Company Reports")

companies_df = companies()

company = st.selectbox(
    "Company",
    sorted(companies_df["company_name"].unique())
)

company_id = companies_df.loc[
    companies_df["company_name"] == company,
    "id"
].iloc[0]

analysis_df = analysis()
pros_df = pros_cons()

st.subheader("Growth Analysis")

st.dataframe(
    analysis_df[
        analysis_df.company_id == company_id
    ],
    hide_index=True,
    width="stretch",
)

st.subheader("Pros & Cons")

pc = pros_df[
    pros_df.company_id == company_id
]

if pc.empty:
    st.info("No report available.")
else:

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### ✅ Pros")
        for p in pc["pros"]:
            st.success(p)

    with c2:
        st.markdown("### ❌ Cons")
        for c in pc["cons"]:
            st.error(c)