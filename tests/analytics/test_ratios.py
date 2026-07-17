import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    check_opm,
    return_on_equity,
    return_on_capital_employed,
    return_on_assets,
    debt_to_equity,
    high_leverage_flag,
    interest_coverage_ratio,
    icr_label,
    net_debt,
    asset_turnover,
)


def test_net_profit_margin():
    assert net_profit_margin(200, 1000) == 20.00


def test_net_profit_margin_zero_sales():
    assert net_profit_margin(200, 0) is None


def test_operating_profit_margin():
    assert operating_profit_margin(300, 1000) == 30.00


def test_opm_cross_check():
    calculated = operating_profit_margin(300, 1000)
    assert check_opm(calculated, 30.5) is True
    assert check_opm(calculated, 32.5) is False


def test_return_on_equity():
    assert return_on_equity(100, 200, 300) == 20.00


def test_return_on_equity_negative_equity():
    assert return_on_equity(100, -100, 50) is None


def test_return_on_capital_employed():
    assert return_on_capital_employed(200, 200, 300, 500) == 20.00


def test_return_on_assets():
    assert return_on_assets(100, 1000) == 10.00


# ---------- Day 9 ----------

def test_debt_to_equity():
    assert debt_to_equity(500, 200, 300) == 1.0


def test_debt_to_equity_debt_free():
    assert debt_to_equity(0, 200, 300) == 0.0


def test_interest_coverage_ratio():
    assert interest_coverage_ratio(500, 100, 200) == 3.0


def test_interest_coverage_zero_interest():
    assert interest_coverage_ratio(500, 100, 0) is None


def test_icr_label():
    assert icr_label(None) == "Debt Free"
    assert icr_label(1.2) == "Risk"
    assert icr_label(3.5) == "Normal"


def test_high_leverage_flag():
    assert high_leverage_flag(6.0, False) is True
    assert high_leverage_flag(6.0, True) is False
    assert high_leverage_flag(2.5, False) is False


def test_net_debt():
    assert net_debt(1000, 300) == 700


def test_asset_turnover():
    assert asset_turnover(1000, 500) == 2.0
    assert asset_turnover(1000, 0) is None