def cagr(start_value, end_value, years):
    """
    Returns:
        (cagr_value, flag)

    flag values:
    NORMAL
    DECLINE_TO_LOSS
    TURNAROUND
    BOTH_NEGATIVE
    ZERO_BASE
    INSUFFICIENT
    """

    if years <= 0:
        return None, "INSUFFICIENT"

    if start_value == 0:
        return None, "ZERO_BASE"

    if start_value > 0 and end_value > 0:
        value = (((end_value / start_value) ** (1 / years)) - 1) * 100
        return round(value, 2), "NORMAL"

    if start_value > 0 and end_value < 0:
        return None, "DECLINE_TO_LOSS"

    if start_value < 0 and end_value > 0:
        return None, "TURNAROUND"

    if start_value < 0 and end_value < 0:
        return None, "BOTH_NEGATIVE"

    return None, "INSUFFICIENT"