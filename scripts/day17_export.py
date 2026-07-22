from src.etl.loader import ExcelLoader
from src.analytics.composite_score import CompositeScore

loader = ExcelLoader()
data = loader.load_all()

df = data["financial_ratios"].merge(
    data["sectors"][["company_id", "broad_sector"]],
    on="company_id",
    how="left",
)

result = CompositeScore(df).calculate()

result.to_excel(
    "output/screener_output.xlsx",
    index=False
)

print("Export completed.")
print("Rows:", len(result))