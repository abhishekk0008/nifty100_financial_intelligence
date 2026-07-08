import pytest

from src.etl.normalizer import normalize_year, normalize_ticker


# -------------------------
# normalize_ticker()
# -------------------------

@pytest.mark.parametrize(
    "input_value, expected",
    [
        ("tcs", "TCS"),
        (" TCS ", "TCS"),
        ("infy", "INFY"),
        (" HDFCBANK ", "HDFCBANK"),
        ("reliance", "RELIANCE"),
        ("LT", "LT"),
        (" tata ", "TATA"),
        ("abc ltd", "ABCLTD"),
        ("", ""),
        (None, None),
        ("   ", ""),
        ("ITC", "ITC"),
        ("asian paint", "ASIANPAINT"),
        ("sbin", "SBIN"),
        ("wipro", "WIPRO"),
        ("maruti", "MARUTI"),
        ("axis bank", "AXISBANK"),
        ("nestle", "NESTLE"),
    ]
)
def test_normalize_ticker(input_value, expected):
    assert normalize_ticker(input_value) == expected


# -------------------------
# normalize_year()
# -------------------------

@pytest.mark.parametrize(
    "input_value, expected",
    [
        ("Mar-23", "2023-03"),
        ("Mar 23", "2023-03"),
        ("mar-23", "2023-03"),
        ("Dec-22", "2022-12"),
        ("Dec 22", "2022-12"),
        ("2024", "2024"),
        ("2023", "2023"),
        (None, None),
        ("", ""),
        ("Random", "Random"),
        ("Mar-20", "2020-03"),
        ("Mar-21", "2021-03"),
        ("Mar-22", "2022-03"),
        ("Mar-24", "2024-03"),
        ("Dec-20", "2020-12"),
        ("Dec-21", "2021-12"),
        ("Dec-24", "2024-12"),
        ("Dec-25", "2025-12"),
    ]
)
def test_normalize_year(input_value, expected):
    assert normalize_year(input_value) == expected