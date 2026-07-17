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