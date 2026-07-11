import pandas as pd


def dq01_pk_uniqueness(df: pd.DataFrame, pk_column: str):
    return df[df.duplicated(subset=[pk_column], keep=False)]


def dq02_company_year_uniqueness(df: pd.DataFrame):
    return df[df.duplicated(subset=["company_id", "year"], keep=False)]


def dq03_positive_sales(df: pd.DataFrame, sales_column: str):
    return df[df[sales_column] <= 0]


def dq04_null_values(df: pd.DataFrame):
    return df[df.isnull().any(axis=1)]