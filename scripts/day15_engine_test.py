from src.etl.loader import ExcelLoader
from src.screener.engine import ScreenerEngine

loader = ExcelLoader()
data = loader.load_all()

ratios = data["financial_ratios"]
sectors = data["sectors"]

df = ratios.merge(
    sectors[["company_id", "broad_sector"]],
    on="company_id",
    how="left"
)

engine = ScreenerEngine(df)

result = engine.apply_filters()

print(result.head(20))
print("\nRows:", len(result))