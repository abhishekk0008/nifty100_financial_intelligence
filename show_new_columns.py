import pandas as pd

files = [
    "financial_ratios.xlsx",
    "market_cap.xlsx",
    "peer_groups.xlsx",
    "sectors.xlsx",
    "stock_prices.xlsx",
]

for file in files:
    print("\n" + "=" * 80)
    print(file)
    df = pd.read_excel("data/raw/" + file, header=1)
    print(df.columns.tolist())