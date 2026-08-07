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
    profit_loss,
)


# =====================================================
# Page Configuration
# =====================================================

st.set_page_config(
    page_title="Financial Trends",
    layout="wide",
)

st.title("📈 Financial Trends")


# =====================================================
# Load Data
# =====================================================

companies_df = companies()
pl_df = profit_loss()


# =====================================================
# Company Selection
# =====================================================

company_list = sorted(
    companies_df["company_name"]
    .dropna()
    .unique()
)

selected_company = st.selectbox(
    "Select Company",
    company_list,
)


company_id = companies_df.loc[
    companies_df["company_name"] == selected_company,
    "id",
].iloc[0]


# =====================================================
# Filter Company Data
# =====================================================

df = pl_df[
    pl_df["company_id"] == company_id
].copy()


if df.empty:
    st.warning("No financial data available for this company.")
    st.stop()


# =====================================================
# Clean / Sort Year
# =====================================================

df["year_label"] = df["year"].astype(str)

df["year_num"] = pd.to_numeric(
    df["year_label"].str.extract(r"(\d{4})")[0],
    errors="coerce",
)

df = (
    df
    .dropna(subset=["year_num"])
    .sort_values("year_num")
)


# Keep latest 10 financial years
latest_years = (
    df["year_num"]
    .drop_duplicates()
    .sort_values()
    .tail(10)
)

df = df[
    df["year_num"].isin(latest_years)
].copy()


# If duplicate rows exist for a year, keep latest occurrence
df = (
    df
    .drop_duplicates(subset=["year_num"], keep="last")
    .sort_values("year_num")
)


# =====================================================
# Metric Selection
# =====================================================

metric_options = {
    "Sales": "sales",
    "Operating Profit": "operating_profit",
    "Net Profit": "net_profit",
    "EPS": "eps",
    "Dividend Payout": "dividend_payout",
}

selected_metrics = st.multiselect(
    "Select Metrics (maximum 3)",
    options=list(metric_options.keys()),
    default=["Sales"],
    max_selections=3,
)


if not selected_metrics:
    st.info("Select at least one metric to display the trend.")
    st.stop()


# =====================================================
# Prepare Data
# =====================================================

fig = go.Figure()


for metric_label in selected_metrics:

    metric_column = metric_options[metric_label]

    if metric_column not in df.columns:
        st.warning(
            f"{metric_label} data is not available."
        )
        continue

    metric_df = df[
        [
            "year_num",
            "year_label",
            metric_column,
        ]
    ].copy()

    metric_df[metric_column] = pd.to_numeric(
        metric_df[metric_column],
        errors="coerce",
    )

    metric_df = metric_df.dropna(
        subset=[metric_column]
    )

    if metric_df.empty:
        continue

    # =================================================
    # YoY Percentage Change
    # =================================================

    metric_df["yoy_pct"] = (
        metric_df[metric_column]
        .pct_change()
        .mul(100)
    )

    # =================================================
    # Line
    # =================================================

    fig.add_trace(
        go.Scatter(
            x=metric_df["year_label"],
            y=metric_df[metric_column],
            mode="lines+markers",
            name=metric_label,
            customdata=metric_df[
                ["yoy_pct"]
            ],
            hovertemplate=(
                "<b>%{x}</b><br>"
                + metric_label
                + ": %{y:.2f}<br>"
                + "YoY: %{customdata[0]:.2f}%"
                + "<extra></extra>"
            ),
        )
    )

    # =================================================
    # YoY Annotation on Every Data Point
    # =================================================

    for _, row in metric_df.iterrows():

        if pd.isna(row["yoy_pct"]):
            annotation_text = "—"
        else:
            annotation_text = (
                f"{row['yoy_pct']:+.1f}%"
            )

        fig.add_annotation(
            x=row["year_label"],
            y=row[metric_column],
            text=annotation_text,
            showarrow=False,
            yshift=14,
            font=dict(size=10),
        )


# =====================================================
# Chart Layout
# =====================================================

fig.update_layout(
    title=(
        f"{selected_company} — "
        f"10-Year Financial Trend"
    ),
    xaxis_title="Financial Year",
    yaxis_title="Value",
    hovermode="x unified",
    legend_title="Metrics",
    height=600,
)


st.plotly_chart(
    fig,
    width="stretch",
)


# =====================================================
# Summary Table
# =====================================================

st.subheader("Financial Trend Data")

display_columns = [
    "year_label",
]

for metric_label in selected_metrics:
    display_columns.append(
        metric_options[metric_label]
    )

display_df = df[display_columns].copy()

display_df = display_df.rename(
    columns={
        "year_label": "Year",
        "sales": "Sales",
        "operating_profit": "Operating Profit",
        "net_profit": "Net Profit",
        "eps": "EPS",
        "dividend_payout": "Dividend Payout",
    }
)


st.dataframe(
    display_df,
    hide_index=True,
    width="stretch",
)