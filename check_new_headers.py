import pandas as pd

files = [
    "financial_ratios.xlsx",
    "market_cap.xlsx",
    "peer_groups.xlsx",
    "sectors.xlsx",
    "stock_prices.xlsx",
]

for file in files:
    print("\n" + "="*80)
    print(file)

    for h in [0, 1, 2]:
        print(f"\nHEADER = {h}")
        df = pd.read_excel("data/raw/" + file, header=h)
        print(df.head(3))