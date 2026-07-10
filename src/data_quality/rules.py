import pandas as pd


def dq01_pk_uniqueness(df: pd.DataFrame, pk_column: str):
    """
    DQ-01: Primary Key must be unique.
    Returns duplicate records.
    """

    duplicates = df[df.duplicated(subset=[pk_column], keep=False)]

    return duplicates

def dq02_company_year_uniqueness(df: pd.DataFrame):
    """
    DQ-02:
    (company_id, year) should be unique.
    """

    duplicates = df[df.duplicated(
        subset=["company_id", "year"],
        keep=False
    )]

    return duplicates