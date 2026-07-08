"""
Utility functions for data normalization.
"""

import re
import pandas as pd


def normalize_ticker(ticker):
    """
    Normalize company ticker.

    Example:
        ' tcs ' -> 'TCS'
        'infy'  -> 'INFY'
    """

    if pd.isna(ticker):
        return None

    ticker = str(ticker).strip().upper()

    ticker = re.sub(r"\s+", "", ticker)

    return ticker


def normalize_year(year):
    """
    Convert year labels into YYYY-MM format.

    Examples:
        Mar-23   -> 2023-03
        Mar 23   -> 2023-03
        Dec-22   -> 2022-12
        2024     -> 2024
    """

    if pd.isna(year):
        return None

    year = str(year).strip()

    month_map = {
        "MAR": "03",
        "DEC": "12"
    }

    match = re.match(r"^(Mar|Dec)[-\s]?(\d{2})$", year, re.IGNORECASE)

    if match:
        month = month_map[match.group(1).upper()]
        yy = int(match.group(2))
        full_year = 2000 + yy
        return f"{full_year}-{month}"

    if re.match(r"^\d{4}$", year):
        return year

    return year
