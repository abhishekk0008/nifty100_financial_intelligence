def free_cash_flow(operating_activity, investing_activity):
    """
    FCF = CFO + CFI
    Investing activity is normally negative.
    """
    return operating_activity + investing_activity


def cfo_quality_score(cfo, pat):
    """
    CFO/PAT
    Returns None if PAT is zero.
    """
    if pat == 0:
        return None

    return round(cfo / pat, 2)


def cfo_quality_label(score):
    if score is None:
        return "NA"

    if score >= 1:
        return "High Quality"

    if score >= 0.5:
        return "Moderate"

    return "Accrual Risk"


def capex_intensity(investing_activity, sales):
    """
    abs(CFI)/Sales *100
    """
    if sales <= 0:
        return None

    return round(abs(investing_activity) / sales * 100, 2)


def capex_label(value):
    if value is None:
        return "NA"

    if value < 3:
        return "Asset Light"

    if value <= 8:
        return "Moderate"

    return "Capital Intensive"


def fcf_conversion(fcf, operating_profit):
    """
    FCF/Operating Profit
    """
    if operating_profit == 0:
        return None

    return round((fcf / operating_profit) * 100, 2)


def capital_allocation_pattern(cfo, cfi, cff):

    cfo_sign = "+" if cfo >= 0 else "-"
    cfi_sign = "+" if cfi >= 0 else "-"
    cff_sign = "+" if cff >= 0 else "-"

    pattern = (cfo_sign, cfi_sign, cff_sign)

    mapping = {
        ("+", "-", "-"): "Reinvestor",
        ("+", "-", "+"): "Growth Funded by Debt",
        ("+", "+", "-"): "Liquidating Assets",
        ("-", "+", "+"): "Distress Signal",
        ("+", "+", "+"): "Cash Accumulator",
        ("-", "-", "-"): "Pre-Revenue",
    }

    return (
        cfo_sign,
        cfi_sign,
        cff_sign,
        mapping.get(pattern, "Mixed")
    )