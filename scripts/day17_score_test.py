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

# Fill missing sector scores before converting to int
result["sector_relative_score"] = (
    result["sector_relative_score"]
    .fillna(0)
    .round(0)
    .astype(int)
)

result["composite_score"] = (
    result["composite_score"]
    .fillna(0)
    .round(2)
)

print(
    result[
        [
            "company_id",
            "broad_sector",
            "year",
            "composite_score",
            "sector_relative_score",
        ]
    ].head(20)
)

print("\nRows:", len(result))