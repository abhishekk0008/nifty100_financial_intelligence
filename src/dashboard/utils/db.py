import streamlit as st


@st.cache_data(ttl=600)
def get_companies():
    pass


@st.cache_data(ttl=600)
def get_ratios(ticker, year=None):
    pass


@st.cache_data(ttl=600)
def get_pl(ticker):
    pass


@st.cache_data(ttl=600)
def get_bs(ticker):
    pass


@st.cache_data(ttl=600)
def get_cf(ticker):
    pass


@st.cache_data(ttl=600)
def get_sectors():
    pass


@st.cache_data(ttl=600)
def get_peers(group_name):
    pass


@st.cache_data(ttl=600)
def get_valuation(ticker):
    pass