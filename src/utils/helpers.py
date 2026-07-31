import pandas as pd


def latest_year(df):
    return df["year"].max()


def latest_records(df):
    yr = latest_year(df)
    return df[df["year"] == yr]


def currency(x):
    if pd.isna(x):
        return "-"
    return f"₹ {x:,.2f} Cr"


def percent(x):
    if pd.isna(x):
        return "-"
    return f"{x:.2f}%"