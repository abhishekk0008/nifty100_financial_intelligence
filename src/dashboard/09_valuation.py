from pathlib import Path
import sys

import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[3]

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.analytics.valuation import build_valuation


st.set_page_config(
    page_title="Valuation",
    layout="wide",
)

st.title("💹 Valuation Analysis")

# Load valuation data
df = build_valuation()

# -----------------------------
# Summary
# -----------------------------

st.subheader("Valuation Summary")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("Companies", len(df))

with c2:
    st.metric(
        "Discount",
        int((df["flag"] == "Discount").sum())
    )

with c3:
    st.metric(
        "Neutral",
        int((df["flag"] == "Neutral").sum())
    )

with c4:
    st.metric(
        "Caution",
        int((df["flag"] == "Caution").sum())
    )


# -----------------------------
# Valuation Flag Distribution
# -----------------------------

st.subheader("Valuation Flags")

flag_counts = (
    df["flag"]
    .value_counts()
    .reset_index()
)

flag_counts.columns = ["flag", "count"]

fig = px.bar(
    flag_counts,
    x="flag",
    y="count",
    title="Valuation Flag Distribution",
    text="count",
)

st.plotly_chart(
    fig,
    width="stretch",
)


# -----------------------------
# EV/EBITDA Analysis
# -----------------------------

st.subheader("EV/EBITDA vs Sector")

ev_counts = (
    df["ev_ebitda_flag"]
    .value_counts()
    .reset_index()
)

ev_counts.columns = ["ev_ebitda_flag", "count"]

fig2 = px.bar(
    ev_counts,
    x="ev_ebitda_flag",
    y="count",
    title="EV/EBITDA Comparison with Sector",
    text="count",
)

st.plotly_chart(
    fig2,
    width="stretch",
)


# -----------------------------
# Company Filter
# -----------------------------

st.subheader("Company Valuation Details")

company = st.selectbox(
    "Select Company",
    sorted(df["company_name"].dropna().unique())
)

company_df = df[
    df["company_name"] == company
]

st.dataframe(
    company_df[
        [
            "company_id",
            "company_name",
            "broad_sector",
            "year",
            "market_cap_crore",
            "pe_ratio",
            "pe_5yr_median",
            "sector_pe_median",
            "pb_ratio",
            "pb_5yr_median",
            "sector_pb_median",
            "ev_ebitda",
            "sector_ev_ebitda_median",
            "fcf_yield_pct",
            "flag",
            "flag_rationale",
        ]
    ],
    hide_index=True,
    width="stretch",
)


# -----------------------------
# Discount Companies
# -----------------------------

st.subheader("Discount-Valued Companies")

discount_df = df[
    df["flag"] == "Discount"
].sort_values(
    "fcf_yield_pct",
    ascending=False
)

st.dataframe(
    discount_df[
        [
            "company_id",
            "company_name",
            "broad_sector",
            "pe_ratio",
            "sector_pe_median",
            "ev_ebitda",
            "fcf_yield_pct",
            "flag_rationale",
        ]
    ],
    hide_index=True,
    width="stretch",
)


# -----------------------------
# Caution Companies
# -----------------------------

st.subheader("Caution-Valued Companies")

caution_df = df[
    df["flag"] == "Caution"
].sort_values(
    "pe_ratio",
    ascending=False
)

st.dataframe(
    caution_df[
        [
            "company_id",
            "company_name",
            "broad_sector",
            "pe_ratio",
            "sector_pe_median",
            "ev_ebitda",
            "fcf_yield_pct",
            "flag_rationale",
        ]
    ],
    hide_index=True,
    width="stretch",
)