import pandas as pd
import numpy as np


class PeerRanking:

    REVERSED_METRICS = {
        "debt_to_equity",
        "total_debt_cr",
    }

    METRICS = [
        "asset_turnover",
        "book_value_per_share",
        "capex_cr",
        "cash_from_operations_cr",
        "compounded_profit_growth",
        "compounded_sales_growth",
        "debt_to_equity",
        "dividend_payout_ratio_pct",
        "earnings_per_share",
        "eps_cagr_5y",
        "free_cash_flow_cr",
        "interest_coverage",
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "roce_percentage",
        "roe",
        "stock_price_cagr",
        "total_debt_cr",
    ]

    def __init__(
        self,
        ratios_df,
        peer_df,
        analysis_df,
        companies_df,
    ):
        self.df = ratios_df.copy()
        self.peer_df = peer_df.copy()
        self.analysis_df = analysis_df.copy()
        self.companies_df = companies_df.copy()

    def _build_peer_mapping(self):

        return (
            self.peer_df[
                [
                    "company_id",
                    "peer_group_name",
                ]
            ]
            .drop_duplicates(subset="company_id")
        )

    def _build_companies(self):

        return (
            self.companies_df[
                [
                    "id",
                    "roce_percentage",
                ]
            ]
            .rename(
                columns={
                    "id": "company_id",
                }
            )
        )

    def _build_analysis(self):

        analysis = self.analysis_df.copy()

        analysis = analysis[
            analysis["roe"]
            .astype(str)
            .str.contains("10 Years", na=False)
        ].copy()

        for col in [
            "compounded_sales_growth",
            "compounded_profit_growth",
            "stock_price_cagr",
            "roe",
        ]:
            analysis[col] = (
                analysis[col]
                .astype(str)
                .str.extract(r"(-?\d+\.?\d*)%")[0]
                .astype(float)
            )

        analysis = analysis.drop_duplicates(subset="company_id")

        return analysis[
            [
                "company_id",
                "compounded_sales_growth",
                "compounded_profit_growth",
                "stock_price_cagr",
                "roe",
            ]
        ]

    def _calculate_eps_cagr(self, group):

        group = group.copy()

        group["year_num"] = (
            group["year"]
            .astype(str)
            .str.extract(r"(\d{4})")[0]
            .astype(int)
        )

        group = group.sort_values("year_num")

        group["eps_cagr_5y"] = np.nan

        for idx, row in group.iterrows():

            current_year = row["year_num"]
            current_eps = row["earnings_per_share"]

            previous = group[
                group["year_num"] == current_year - 5
            ]

            if previous.empty:
                continue

            old_eps = previous.iloc[0]["earnings_per_share"]

            if (
                pd.notna(current_eps)
                and pd.notna(old_eps)
                and current_eps > 0
                and old_eps > 0
            ):

                cagr = (
                    (current_eps / old_eps) ** (1 / 5) - 1
                ) * 100

                group.loc[idx, "eps_cagr_5y"] = round(cagr, 2)

        return group.drop(columns="year_num")

    def _merge_all(self):

        peer = self._build_peer_mapping()
        companies = self._build_companies()
        analysis = self._build_analysis()

        df = (
            self.df
            .merge(
                peer,
                on="company_id",
                how="left",
            )
            .merge(
                analysis,
                on="company_id",
                how="left",
            )
            .merge(
                companies,
                on="company_id",
                how="left",
            )
        )

        df["peer_group_name"] = df["peer_group_name"].fillna(
            "No peer group assigned"
        )

        return df

    def _rank_metric(self, df, metric):

        temp = df.dropna(
            subset=[
                metric,
                "peer_group_name",
                "year",
                "company_id",
            ]
        ).copy()

        if temp.empty:
            return None

        ranks = temp.groupby(
            [
                "peer_group_name",
                "year",
            ]
        )[metric].rank(
            pct=True,
            method="average",
        )

        if metric in self.REVERSED_METRICS:
            ranks = 1 - ranks

        temp["percentile_rank"] = ranks * 100
        temp["metric"] = metric
        temp["value"] = temp[metric]

        return temp[
            [
                "company_id",
                "peer_group_name",
                "year",
                "metric",
                "value",
                "percentile_rank",
            ]
        ]

    def calculate(self):

        df = self._merge_all()

        df = (
            df.groupby(
                "company_id",
                group_keys=False,
            )
            .apply(self._calculate_eps_cagr)
            .reset_index(drop=True)
        )

        if "company_id" not in df.columns:

            df = df.merge(
                self.df[
                    ["id", "company_id"]
                ].drop_duplicates("id"),
                on="id",
                how="left",
            )

        results = []

        for metric in self.METRICS:

            if metric not in df.columns:
                continue

            ranked = self._rank_metric(df, metric)

            if ranked is not None:
                results.append(ranked)

        if not results:

            return pd.DataFrame(
                columns=[
                    "company_id",
                    "peer_group_name",
                    "year",
                    "metric",
                    "value",
                    "percentile_rank",
                ]
            )

        final = pd.concat(
            results,
            ignore_index=True,
        )

        final["percentile_rank"] = (
            final["percentile_rank"]
            .fillna(0)
            .round(2)
        )

        final = (
            final
            .drop_duplicates(
                subset=[
                    "company_id",
                    "year",
                    "metric",
                    "peer_group_name",
                ]
            )
            .sort_values(
                [
                    "peer_group_name",
                    "company_id",
                    "year",
                    "metric",
                ]
            )
            .reset_index(drop=True)
        )

        final["year_num"] = (
            final["year"]
            .astype(str)
            .str.extract(r"(\d{4})")[0]
            .astype(int)
        )

        final = (
            final.sort_values(
                ["company_id", "metric", "year_num"]
            )
            .groupby(
                ["company_id", "metric"],
                group_keys=False,
            )
            .tail(1)
            .drop(columns="year_num")
            .reset_index(drop=True)
        )

        return final