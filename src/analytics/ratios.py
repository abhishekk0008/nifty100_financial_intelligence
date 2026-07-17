def net_profit_margin(net_profit, sales):
    if sales <= 0:
        return None
    return round((net_profit / sales) * 100, 2)


def operating_profit_margin(operating_profit, sales):
    if sales <= 0:
        return None
    return round((operating_profit / sales) * 100, 2)


def check_opm(calculated, reported, tolerance=2):
    return abs(calculated - reported) <= tolerance


def return_on_equity(net_profit, equity_capital, reserves):
    equity = equity_capital + reserves
    if equity <= 0:
        return None
    return round((net_profit / equity) * 100, 2)


def return_on_capital_employed(ebit, equity_capital, reserves, borrowings):
    capital = equity_capital + reserves + borrowings
    if capital <= 0:
        return None
    return round((ebit / capital) * 100, 2)


def return_on_assets(net_profit, total_assets):
    if total_assets <= 0:
        return None
    return round((net_profit / total_assets) * 100, 2)


def debt_to_equity(borrowings, equity_capital, reserves):
    if borrowings == 0:
        return 0.0

    equity = equity_capital + reserves

    if equity <= 0:
        return None

    return round(borrowings / equity, 2)


def high_leverage_flag(de_ratio, is_financial=False):
    if is_financial:
        return False
    return de_ratio > 5


def interest_coverage_ratio(operating_profit, other_income, interest):
    if interest <= 0:
        return None
    ebit = operating_profit + other_income
    return round(ebit / interest, 2)


def icr_label(icr):
    if icr is None:
        return "Debt Free"
    elif icr < 2:
        return "Risk"
    else:
        return "Normal"


def net_debt(borrowings, cash):
    return borrowings - cash


def asset_turnover(sales, total_assets):
    if total_assets <= 0:
        return None
    return round(sales / total_assets, 2)