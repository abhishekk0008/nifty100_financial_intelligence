from src.etl.loader import ExcelLoader
from src.screener.presets.presets import PresetScreeners

loader = ExcelLoader()
data = loader.load_all()

# Merge financial ratios with sectors
df = data["financial_ratios"].merge(
    data["sectors"][["company_id", "broad_sector"]],
    on="company_id",
    how="left",
)

screeners = PresetScreeners(df)

results = {
    "Quality": screeners.quality_compounder(),
    "Value": screeners.value_pick(),
    "Growth": screeners.growth_accelerator(),
    "Dividend": screeners.dividend_champion(),
    "Debt Free": screeners.debt_free_bluechip(),
    "Turnaround": screeners.turnaround_watch(),
}

for name, result in results.items():
    print(f"\n===== {name} =====")
    print("Rows:", len(result))
    print(result.head())