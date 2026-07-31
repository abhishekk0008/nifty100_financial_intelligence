from pathlib import Path
import sys
import streamlit as st

ROOT = Path(__file__).resolve().parents[3]

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.etl.loader import ExcelLoader


@st.cache_data
def load_data():
    return ExcelLoader().load_all()


def companies():
    return load_data()["companies"]


def ratios():
    return load_data()["financial_ratios"]


def sectors():
    return load_data()["sectors"]


def peer_groups():
    return load_data()["peer_groups"]


def profit_loss():
    return load_data()["profit_loss"]


def balance_sheet():
    return load_data()["balance_sheet"]


def cashflow():
    return load_data()["cash_flow"]


def pros_cons():
    return load_data()["pros_cons"]


def analysis():
    return load_data()["analysis"]


def documents():
    return load_data()["documents"]


def market_cap():
    return load_data()["market_cap"]


def stock_prices():
    return load_data()["stock_prices"]