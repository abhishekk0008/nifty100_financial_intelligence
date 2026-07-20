import yaml
import pandas as pd


class ScreenerEngine:
    def __init__(self, df, config_path="config/screener_config.yaml"):
        self.df = df.copy()

        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

    def apply_filters(
        self,
        roe_min=None,
        de_max=None,
        opm_min=None,
        icr_min=None,
        asset_turnover_min=None,
    ):
        cfg = self.config["filters"]

        if roe_min is None:
            roe_min = cfg.get("roe_min")

        if de_max is None:
            de_max = cfg.get("de_max")

        if opm_min is None:
            opm_min = cfg.get("opm_min")

        if icr_min is None:
            icr_min = cfg.get("icr_min")

        if asset_turnover_min is None:
            asset_turnover_min = cfg.get("asset_turnover_min")

        df = self.df.copy()

        if roe_min is not None:
            df = df[df["return_on_equity_pct"] >= roe_min]

        if de_max is not None:
            financials = df["broad_sector"] == "Financials"
            df = pd.concat([
                df[financials],
                df[~financials & (df["debt_to_equity"] <= de_max)]
            ])

        if opm_min is not None:
            df = df[df["operating_profit_margin_pct"] >= opm_min]

        if icr_min is not None:
            df = df[
                df["interest_coverage"].isna() |
                (df["interest_coverage"] >= icr_min)
            ]

        if asset_turnover_min is not None:
            df = df[df["asset_turnover"] >= asset_turnover_min]

        df["composite_quality_score"] = (
            df["return_on_equity_pct"].fillna(0)
            + df["operating_profit_margin_pct"].fillna(0)
            + df["asset_turnover"].fillna(0)
        )

        return df.sort_values(
            "composite_quality_score",
            ascending=False,
        )