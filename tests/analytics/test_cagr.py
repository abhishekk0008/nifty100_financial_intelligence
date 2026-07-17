import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.analytics.cagr import cagr


def test_normal_cagr():
    value, flag = cagr(100, 200, 5)
    assert flag == "NORMAL"
    assert round(value, 2) == 14.87


def test_decline_to_loss():
    value, flag = cagr(100, -50, 5)
    assert value is None
    assert flag == "DECLINE_TO_LOSS"


def test_turnaround():
    value, flag = cagr(-100, 50, 5)
    assert value is None
    assert flag == "TURNAROUND"


def test_both_negative():
    value, flag = cagr(-100, -50, 5)
    assert value is None
    assert flag == "BOTH_NEGATIVE"


def test_zero_base():
    value, flag = cagr(0, 100, 5)
    assert value is None
    assert flag == "ZERO_BASE"


def test_insufficient_years():
    value, flag = cagr(100, 200, 0)
    assert value is None
    assert flag == "INSUFFICIENT"


def test_positive_growth():
    value, flag = cagr(100, 150, 3)
    assert flag == "NORMAL"
    assert value > 0


def test_negative_growth():
    value, flag = cagr(200, 100, 5)
    assert flag == "NORMAL"
    assert value < 0


def test_same_value():
    value, flag = cagr(100, 100, 5)
    assert flag == "NORMAL"
    assert value == 0.0


def test_large_growth():
    value, flag = cagr(100, 1000, 10)
    assert flag == "NORMAL"
    assert value > 0