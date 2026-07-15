"""
Excel Loader Module
Nifty 100 Financial Intelligence Platform
"""

from pathlib import Path
import logging
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


class ExcelLoader:
    """
    Loads all Excel datasets from the raw data folder.
    """

    def __init__(self, data_folder="data/raw"):
        self.data_folder = Path(data_folder)

    def load_excel(self, filename, header=0):
        """
        Load a single Excel file.
        """

        filepath = self.data_folder / filename

        if not filepath.exists():
            raise FileNotFoundError(f"{filename} not found.")

        logger.info(f"Loading {filename}")

        df = pd.read_excel(filepath, header=header)

        logger.info(f"{filename} loaded successfully. Shape: {df.shape}")

        return df

    def load_all(self):
        """
        Load all project datasets.
        """

        files = {
            "companies": ("companies.xlsx", 1),
            "profit_loss": ("profitandloss.xlsx", 1),
            "balance_sheet": ("balancesheet.xlsx", 1),
            "cash_flow": ("cashflow.xlsx", 1),
            "analysis": ("analysis.xlsx", 1),
            "documents": ("documents.xlsx", 1),
            "pros_cons": ("prosandcons.xlsx", 1),

            "financial_ratios": ("financial_ratios.xlsx", 0),
            "market_cap": ("market_cap.xlsx", 0),
            "peer_groups": ("peer_groups.xlsx", 0),
            "sectors": ("sectors.xlsx", 0),
            "stock_prices": ("stock_prices.xlsx", 0),
        }

        datasets = {}

        for name, (file, header) in files.items():
            try:
                datasets[name] = self.load_excel(file, header=header)
            except Exception as e:
                logger.error(e)

        return datasets