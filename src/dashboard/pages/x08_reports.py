from pathlib import Path
import sys
import re

import pandas as pd
import requests
import streamlit as st

ROOT = Path(__file__).resolve().parents[3]

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.dashboard.utils.data import companies, documents


st.set_page_config(
    page_title="Annual Reports",
    layout="wide",
)

st.title("📄 Annual Reports")

companies_df = companies()
documents_df = documents()


# ---------------------------------------------------------
# Company selection
# ---------------------------------------------------------

company = st.selectbox(
    "Select Company",
    sorted(companies_df["company_name"].dropna().unique()),
)

company_id = companies_df.loc[
    companies_df["company_name"] == company,
    "id",
].iloc[0]


# ---------------------------------------------------------
# Filter reports for selected company
# ---------------------------------------------------------

reports = documents_df[
    documents_df["company_id"] == company_id
].copy()


if reports.empty:
    st.warning("No annual reports available for this company.")
    st.stop()


# ---------------------------------------------------------
# Clean year
# ---------------------------------------------------------

reports["Year"] = pd.to_numeric(
    reports["Year"],
    errors="coerce",
)

reports = reports.dropna(subset=["Year"])

reports["Year"] = reports["Year"].astype(int)


# ---------------------------------------------------------
# Clean URL
# ---------------------------------------------------------

def clean_url(value):
    if pd.isna(value):
        return None

    value = str(value).strip()

    # If markdown link is present, extract actual URL
    match = re.search(r"https?://[^\s\]\)]+", value)

    if match:
        return match.group(0)

    return value


reports["url"] = reports["Annual_Report"].apply(clean_url)

reports = reports.dropna(subset=["url"])

reports = reports.sort_values(
    "Year",
    ascending=False,
)


# ---------------------------------------------------------
# Check PDF availability
# ---------------------------------------------------------

@st.cache_data(ttl=3600)
def check_url(url):

    try:
        response = requests.head(
            url,
            allow_redirects=True,
            timeout=8,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
        )

        # Some servers don't properly support HEAD
        if response.status_code == 405:
            response = requests.get(
                url,
                allow_redirects=True,
                timeout=8,
                headers={
                    "User-Agent": "Mozilla/5.0"
                },
                stream=True,
            )

        return response.status_code

    except requests.RequestException:
        return None


# ---------------------------------------------------------
# UI
# ---------------------------------------------------------

st.subheader(f"📚 Available Annual Reports — {company}")

st.caption(
    f"{len(reports)} annual report records found"
)


# ---------------------------------------------------------
# Report list
# ---------------------------------------------------------

for _, row in reports.iterrows():

    year = row["Year"]
    url = row["url"]

    status = check_url(url)

    col1, col2, col3 = st.columns([1, 3, 1])

    with col1:
        st.markdown(f"### {year}")

    with col2:

        if status == 404:
            st.markdown(
                "🔴 **Report unavailable**"
            )

        elif status is None:
            st.markdown(
                "🟡 **Unable to verify report**"
            )

        else:
            st.markdown(
                f"📄 [View Annual Report ({year})]({url})"
            )

    with col3:

        if status == 404:
            st.badge(
                "404",
                icon=":material/error:",
                color="red",
            )
        elif status is None:
            st.badge(
                "Unknown",
                icon=":material/help:",
                color="orange",
            )
        else:
            st.badge(
                "Available",
                icon=":material/check_circle:",
                color="green",
            )

    st.divider()