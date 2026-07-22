from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


class RadarChartGenerator:

    def __init__(self, ranking_df):
        self.df = ranking_df.copy()

    def generate(self):

        output_dir = Path("reports/radar_charts")
        output_dir.mkdir(parents=True, exist_ok=True)

        # -----------------------------
        # Latest year data for each company
        # -----------------------------
        temp = self.df.copy()

        temp["year_num"] = (
            temp["year"]
            .astype(str)
            .str.extract(r"(\d{4})")[0]
            .astype(int)
        )

        latest = temp[
            temp["year_num"]
            == temp.groupby("company_id")["year_num"].transform("max")
        ].copy()

        latest = latest.drop(columns="year_num")

        metrics_order = [
            "return_on_equity_pct",
            "roce_percentage",
            "net_profit_margin_pct",
            "debt_to_equity",
            "free_cash_flow_cr",
            "compounded_profit_growth",
            "compounded_sales_growth",
            "eps_cagr_5y",
        ]

        latest = latest[
            latest["metric"].isin(metrics_order)
        ]

        peer_avg = (
            latest.groupby(
                ["peer_group_name", "metric"]
            )["percentile_rank"]
            .mean()
            .reset_index()
        )

        companies = sorted(latest["company_id"].unique())

        for company in companies:

            company_df = latest[
                latest["company_id"] == company
            ]

            if company_df.empty:
                continue

            peer = company_df.iloc[0]["peer_group_name"]

            company_values = []
            peer_values = []
            labels = []

            for metric in metrics_order:

                labels.append(metric)

                c = company_df[
                    company_df["metric"] == metric
                ]

                p = peer_avg[
                    (peer_avg["peer_group_name"] == peer)
                    &
                    (peer_avg["metric"] == metric)
                ]

                company_values.append(
                    c.iloc[0]["percentile_rank"]
                    if not c.empty
                    else 0
                )

                peer_values.append(
                    p.iloc[0]["percentile_rank"]
                    if not p.empty
                    else 0
                )

            angles = np.linspace(
                0,
                2 * np.pi,
                len(labels),
                endpoint=False,
            )

            company_values += company_values[:1]
            peer_values += peer_values[:1]
            angles = np.concatenate(
                (angles, [angles[0]])
            )

            fig = plt.figure(figsize=(8, 8))
            ax = plt.subplot(111, polar=True)

            ax.plot(
                angles,
                company_values,
                linewidth=2,
                label=company,
            )

            ax.fill(
                angles,
                company_values,
                alpha=0.25,
            )

            ax.plot(
                angles,
                peer_values,
                "--",
                linewidth=2,
                label="Peer Avg",
            )

            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(
                labels,
                fontsize=8,
            )

            ax.set_ylim(0, 100)

            plt.title(company)
            plt.legend(loc="upper right")
            plt.tight_layout()

            plt.savefig(
                output_dir / f"{company}_radar.png",
                dpi=200,
            )

            plt.close()

        print(f"Saved {len(companies)} radar charts.")