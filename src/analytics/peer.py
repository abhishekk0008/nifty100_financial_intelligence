import pandas as pd
import numpy as np


class PeerRanking:

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

    def calculate(self):

        # -----------------------------
        # Peer group mapping
        # -----------------------------
        peer = (
            self.peer_df[
                [
                    "company_id",
                    "peer_group_name",
                ]
            ]
            .drop_duplicates(subset="company_id")
        )

        # -----------------------------
        # ROCE from companies sheet
        # -----------------------------
        companies = (
            self.companies_df[
                [
                    "id",
                    "roce_percentage",
                ]
            ]
            .rename(columns={"id": "company_id"})
        )

        # -----------------------------
        # Merge datasets
        # -----------------------------
        df = (
            self.df
            .merge(
                peer,
                on="company_id",
                how="left",
            )
            .merge(
                self.analysis_df[
                    [
                        "company_id",
                        "compounded_sales_growth",
                        "compounded_profit_growth",
                    ]
                ],
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

        # -------------------------------------------------
        # EPS CAGR 5 Years
        # -------------------------------------------------

        def calculate_eps_cagr(group):

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
                        (
                            current_eps / old_eps
                        ) ** (1 / 5)
                        - 1
                    ) * 100

                    group.loc[idx, "eps_cagr_5y"] = round(
                        cagr,
                        2,
                    )

            return group.drop(columns="year_num")

        df = (
            df.groupby(
                "company_id",
                group_keys=False,
            )
            .apply(calculate_eps_cagr)
            .reset_index(drop=True)
        )

              # Restore company_id after groupby/apply
        if "company_id" not in df.columns:

            df = df.merge(
                self.df[["id", "company_id"]],
                on="id",
                how="left"
            )

        
        # -------------------------------------------------

        metrics = [
            "return_on_equity_pct",
            "roce_percentage",
            "net_profit_margin_pct",
            "debt_to_equity",
            "free_cash_flow_cr",
            "compounded_profit_growth",
            "compounded_sales_growth",
            "eps_cagr_5y",
            "interest_coverage",
            "asset_turnover",
        ]

        results = []

        for metric in metrics:

            temp = df.copy()

            # Skip if metric doesn't exist
            if metric not in temp.columns:
                continue

            # Remove rows where metric is missing
            temp = temp.dropna(
                subset=[
                    metric,
                    "peer_group_name",
                    "year",
                    "company_id",
                ]
            )

            if temp.empty:
                continue

            if metric == "debt_to_equity":

                temp["percentile_rank"] = (
                    1
                    - temp.groupby(
                        [
                            "peer_group_name",
                            "year",
                        ]
                    )[metric].rank(
                        pct=True,
                        method="average",
                    )
                ) * 100

            else:

                temp["percentile_rank"] = (
                    temp.groupby(
                        [
                            "peer_group_name",
                            "year",
                        ]
                    )[metric].rank(
                        pct=True,
                        method="average",
                    )
                ) * 100

            temp["metric"] = metric
            temp["value"] = temp[metric]

            results.append(

                temp[
                    [
                        "company_id",
                        "peer_group_name",
                        "year",
                        "metric",
                        "value",
                        "percentile_rank",
                    ]
                ]

            )

        if len(results) == 0:

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
            .drop_duplicates()
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

        return final