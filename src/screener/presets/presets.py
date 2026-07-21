from src.screener.engine import ScreenerEngine


class PresetScreeners:

    def __init__(self, df):
        self.engine = ScreenerEngine(df)

    # 1. Quality Compounder
    def quality_compounder(self):
        return self.engine.apply_filters(
            roe_min=25,
            de_max=0.5,
            opm_min=15,
            icr_min=5,
            asset_turnover_min=1,
        )

    # 2. Value Pick
    def value_pick(self):
        return self.engine.apply_filters(
            roe_min=15,
            de_max=1,
            opm_min=10,
        )

    # 3. Growth Accelerator
    def growth_accelerator(self):
        return self.engine.apply_filters(
            roe_min=20,
            de_max=1,
            opm_min=15,
            asset_turnover_min=1,
        )

    # 4. Dividend Champion
    def dividend_champion(self):
        df = self.engine.df.copy()

        return df[
            (df["dividend_payout_ratio_pct"] > 20)
            & (df["dividend_payout_ratio_pct"] < 70)
            & (df["free_cash_flow_cr"] > 0)
            & (df["return_on_equity_pct"] > 15)
        ].sort_values(
            "return_on_equity_pct",
            ascending=False,
        )

    # 5. Debt Free Blue Chip
    def debt_free_bluechip(self):
        df = self.engine.df.copy()

        return df[
            (df["debt_to_equity"] == 0)
            & (df["return_on_equity_pct"] > 18)
            & (df["asset_turnover"] > 1)
        ].sort_values(
            "return_on_equity_pct",
            ascending=False,
        )

    # 6. Turnaround Watch
    def turnaround_watch(self):
        df = self.engine.df.copy()

        return df[
            (df["free_cash_flow_cr"] > 0)
            & (df["operating_profit_margin_pct"] > 10)
            & (df["interest_coverage"] > 3)
        ].sort_values(
            "free_cash_flow_cr",
            ascending=False,
        )