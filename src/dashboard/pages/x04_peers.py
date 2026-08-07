from pathlib import Path
import sys

import streamlit as st
import pandas as pd
import plotly.graph_objects as go


# =====================================================
# Project Root
# =====================================================

ROOT = Path(__file__).resolve().parents[3]

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


from src.dashboard.utils.data import (
    companies,
    peer_groups,
    ratios,
)


# =====================================================
# Page Config
# =====================================================

st.set_page_config(
    page_title="Peer Comparison",
    layout="wide",
)

st.title("🤝 Peer Comparison")


# =====================================================
# Load Data
# =====================================================

companies_df = companies().copy()
peers_df = peer_groups().copy()
ratios_df = ratios().copy()


# =====================================================
# Standardize Company IDs
# =====================================================

companies_df["id"] = (
    companies_df["id"]
    .astype(str)
    .str.upper()
    .str.strip()
)

peers_df["company_id"] = (
    peers_df["company_id"]
    .astype(str)
    .str.upper()
    .str.strip()
)

ratios_df["company_id"] = (
    ratios_df["company_id"]
    .astype(str)
    .str.upper()
    .str.strip()
)


# =====================================================
# Latest Financial Year — Company Wise
# =====================================================

ratios_df["year_num"] = (
    ratios_df["year"]
    .astype(str)
    .str.extract(r"(\d{4})")[0]
)

ratios_df["year_num"] = pd.to_numeric(
    ratios_df["year_num"],
    errors="coerce",
)

ratios_df = ratios_df.dropna(
    subset=["company_id", "year_num"]
).copy()

ratios_df["year_num"] = ratios_df["year_num"].astype(int)

ratios_df = (
    ratios_df
    .sort_values(
        ["company_id", "year_num"]
    )
    .drop_duplicates(
        subset="company_id",
        keep="last",
    )
    .copy()
)


# =====================================================
# Add Company Names
# =====================================================

peers_df = peers_df.merge(
    companies_df[["id", "company_name"]],
    left_on="company_id",
    right_on="id",
    how="left",
)

peers_df.drop(
    columns=["id"],
    inplace=True,
    errors="ignore",
)


# =====================================================
# Peer Groups
# =====================================================

peer_group_list = sorted(
    peers_df["peer_group_name"]
    .dropna()
    .astype(str)
    .unique()
)

st.subheader("Peer Group")

selected_group = st.selectbox(
    "Select Peer Group",
    peer_group_list,
)


# =====================================================
# Selected Peer Group Data
# =====================================================

group_df = peers_df[
    peers_df["peer_group_name"] == selected_group
].copy()


if group_df.empty:
    st.warning("No companies found in this peer group.")
    st.stop()


group_ids = group_df["company_id"].unique()


# =====================================================
# Benchmark Company
# =====================================================

benchmark_rows = group_df[
    group_df["is_benchmark"] == True
]

if benchmark_rows.empty:
    st.warning(
        "No benchmark company is defined for this peer group."
    )
    st.stop()


benchmark_id = benchmark_rows.iloc[0]["company_id"]

benchmark_name = benchmark_rows.iloc[0]["company_name"]


# =====================================================
# Peer Financial Data
# =====================================================

peer_ratios = ratios_df[
    ratios_df["company_id"].isin(group_ids)
].copy()


peer_ratios = peer_ratios.merge(
    companies_df[
        ["id", "company_name"]
    ],
    left_on="company_id",
    right_on="id",
    how="left",
)

peer_ratios.drop(
    columns=["id"],
    inplace=True,
    errors="ignore",
)


# =====================================================
# Check Financial Data
# =====================================================

if peer_ratios.empty:
    st.warning(
        "No financial ratio data found for this peer group."
    )
    st.stop()


# =====================================================
# 8 Metrics
# =====================================================

metric_columns = {
    "ROE (%)": "return_on_equity_pct",
    "Net Profit Margin (%)": "net_profit_margin_pct",
    "Operating Profit Margin (%)": "operating_profit_margin_pct",
    "Debt / Equity": "debt_to_equity",
    "Interest Coverage": "interest_coverage",
    "Asset Turnover": "asset_turnover",
    "EPS": "earnings_per_share",
    "Free Cash Flow (Cr)": "free_cash_flow_cr",
}


available_metrics = {
    label: column
    for label, column in metric_columns.items()
    if column in peer_ratios.columns
}


# =====================================================
# Numeric Conversion
# =====================================================

for column in available_metrics.values():

    peer_ratios[column] = pd.to_numeric(
        peer_ratios[column],
        errors="coerce",
    )


# =====================================================
# Benchmark Financial Data
# =====================================================

benchmark = peer_ratios[
    peer_ratios["company_id"] == benchmark_id
].copy()


if benchmark.empty:
    st.warning(
        f"No financial data found for benchmark company: "
        f"{benchmark_name}"
    )
    st.stop()


# =====================================================
# Peer Average
# =====================================================

peer_average = peer_ratios[
    list(available_metrics.values())
].mean()


# =====================================================
# Header KPIs
# =====================================================

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Peer Group",
        selected_group,
    )

with col2:
    st.metric(
        "Companies",
        len(group_df),
    )

with col3:
    st.metric(
        "Benchmark",
        benchmark_name,
    )


# =====================================================
# Radar Chart
# =====================================================

st.subheader("📊 Benchmark vs Peer Group Average")


radar_labels = list(
    available_metrics.keys()
)

benchmark_values = []
average_values = []


for label, column in available_metrics.items():

    values = peer_ratios[column].dropna()

    if values.empty:
        benchmark_values.append(0)
        average_values.append(0)
        continue

    min_value = values.min()
    max_value = values.max()

    benchmark_value = benchmark.iloc[0][column]
    average_value = peer_average[column]

    if pd.isna(benchmark_value):
        benchmark_score = 0
    elif max_value == min_value:
        benchmark_score = 100
    else:
        benchmark_score = (
            (benchmark_value - min_value)
            / (max_value - min_value)
            * 100
        )

    if pd.isna(average_value):
        average_score = 0
    elif max_value == min_value:
        average_score = 100
    else:
        average_score = (
            (average_value - min_value)
            / (max_value - min_value)
            * 100
        )

    benchmark_values.append(
        benchmark_score
    )

    average_values.append(
        average_score
    )


fig = go.Figure()


fig.add_trace(
    go.Scatterpolar(
        r=benchmark_values,
        theta=radar_labels,
        fill="toself",
        name=benchmark_name,
    )
)


fig.add_trace(
    go.Scatterpolar(
        r=average_values,
        theta=radar_labels,
        fill="toself",
        name="Peer Group Average",
    )
)


fig.update_layout(
    polar=dict(
        radialaxis=dict(
            visible=True,
            range=[0, 100],
        )
    ),
    showlegend=True,
    height=600,
)


st.plotly_chart(
    fig,
    width="stretch",
)


# =====================================================
# Side-by-Side KPI Table
# =====================================================

st.subheader("📋 Peer Company Comparison")


table_columns = [
    "company_id",
    "company_name",
]

table_columns.extend(
    available_metrics.values()
)


table = peer_ratios[
    table_columns
].copy()


# Rename metric columns

rename_map = {
    column: label
    for label, column in available_metrics.items()
}

table.rename(
    columns=rename_map,
    inplace=True,
)


# =====================================================
# Benchmark Flag
# =====================================================

table["Benchmark"] = (
    table["company_id"] == benchmark_id
)


# Benchmark first

table = table.sort_values(
    "Benchmark",
    ascending=False,
)


# =====================================================
# Highlight Benchmark Row
# =====================================================

def highlight_benchmark(row):

    if row["Benchmark"]:
        return [
            "font-weight: bold"
            for _ in row
        ]

    return [
        ""
        for _ in row
    ]


styled_table = table.style.apply(
    highlight_benchmark,
    axis=1,
)


st.dataframe(
    styled_table,
    hide_index=True,
    width="stretch",
)


# =====================================================
# CSV Download
# =====================================================

download_df = table.drop(
    columns=["Benchmark"]
)


csv = download_df.to_csv(
    index=False
).encode("utf-8")


st.download_button(
    label="⬇ Download Peer Comparison",
    data=csv,
    file_name="peer_comparison.csv",
    mime="text/csv",
)