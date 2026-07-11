"""
Excel Loader Module
Nifty 100 Financial Intelligence Platform
"""

from pathlib import Path
import logging
import pandas as pd

# Configure logging
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

        Parameters
        ----------
        filename : str
            Excel filename
        header : int
            Header row

        Returns
        -------
        pandas.DataFrame
        """

        filepath = self.data_folder / filename

        if not filepath.exists():
            raise FileNotFoundError(f"{filename} not found.")

        logger.info(f"Loading {filename}")

        df = pd.read_excel(filepath, header=1)

        logger.info(f"{filename} loaded successfully. Shape: {df.shape}")

        return df

    def load_all(self):
        """
        Load all project datasets.
        """

        files = {
            "companies": "companies.xlsx",
            "profit_loss": "profitandloss.xlsx",
            "balance_sheet": "balancesheet.xlsx",
            "cash_flow": "cashflow.xlsx",
            "analysis": "analysis.xlsx",
            "documents": "documents.xlsx",
            "pros_cons": "prosandcons.xlsx",
        }

        datasets = {}

        for name, file in files.items():
            try:
                datasets[name] = self.load_excel(file)
            except Exception as e:
                logger.error(e)

        return datasets