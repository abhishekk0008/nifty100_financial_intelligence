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