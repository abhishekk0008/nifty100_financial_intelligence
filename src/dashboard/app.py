import streamlit as st

st.set_page_config(
    page_title="Nifty 100 Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 Nifty 100 Financial Intelligence Platform")

st.success("Dashboard initialized successfully.")

st.write(
    """
Welcome to the Nifty 100 Financial Intelligence Platform.

Use the sidebar to navigate through all dashboard pages.
"""
)