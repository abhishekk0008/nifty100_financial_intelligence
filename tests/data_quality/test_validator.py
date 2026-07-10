import pandas as pd

from src.data_quality.rules import (
    dq01_pk_uniqueness,
    dq02_company_year_uniqueness,
)


def test_dq01_pk():
    df = pd.DataFrame({"company_id": [1, 2, 2, 4]})
    result = dq01_pk_uniqueness(df, "company_id")
    assert len(result) == 2


def test_dq02_company_year():
    df = pd.DataFrame({
        "company_id": [1, 1, 2],
        "year": [2024, 2024, 2025]
    })
    result = dq02_company_year_uniqueness(df)
    assert len(result) == 2