import pandas as pd
import numpy as np


class CompositeScore:

    def __init__(self, df):
        self.df = df.copy()

    def calculate(self):
        df = self.df.copy()

        # Required columns
        required = [
            "return_on_equity_pct",
            "operating_profit_margin_pct",
            "net_profit_margin_pct",
            "free_cash_flow_cr",
            "cash_from_operations_cr",
            "asset_turnover",
            "debt_to_equity",
            "interest_coverage",
            "broad_sector",
        ]

        for col in required:
            if col not in df.columns:
                df[col] = np.nan

        # Min-Max Scoring Function
        def score(series):
            s = pd.to_numeric(series, errors="coerce").fillna(0)

            if s.max() == s.min():
                return pd.Series(
                    np.full(len(s), 50),
                    index=s.index,
                    dtype=float
                )

            return ((s - s.min()) / (s.max() - s.min())) * 100

        # ----------------------------
        # Profitability (35%)
        # ----------------------------

        profitability = (
            score(df["return_on_equity_pct"]) * 0.15
            + score(df["operating_profit_margin_pct"]) * 0.10
            + score(df["net_profit_margin_pct"]) * 0.10
        )

        # ----------------------------
        # Cash Quality (30%)
        # ----------------------------

        cash_quality = (
            score(df["free_cash_flow_cr"]) * 0.15
            + score(df["cash_from_operations_cr"]) * 0.15
        )

        # ----------------------------
        # Growth (20%)
        # ----------------------------

        growth = score(df["asset_turnover"]) * 0.20

        # ----------------------------
        # Leverage (15%)
        # ----------------------------

        leverage = (
            (100 - score(df["debt_to_equity"])) * 0.10
            + score(df["interest_coverage"]) * 0.05
        )

        # ----------------------------
        # Final Composite Score
        # ----------------------------

        df["composite_score"] = (
            profitability
            + cash_quality
            + growth
            + leverage
        ).round(2)

        # ----------------------------
        # Sector Relative Score
        # ----------------------------

        def sector_score(group):
            if group.max() == group.min():
                return pd.Series(
                    np.full(len(group), 50),
                    index=group.index,
                    dtype=float
                )

            return (
                (group - group.min())
                / (group.max() - group.min())
            ) * 100

        df["sector_relative_score"] = (
            df.groupby("broad_sector")["composite_score"]
            .transform(sector_score)
            .round(2)
        )

        return df.sort_values(
            "composite_score",
            ascending=False
        )