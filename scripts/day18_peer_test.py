from src.etl.loader import ExcelLoader
from src.analytics.peer import PeerRanking

loader = ExcelLoader()
data = loader.load_all()

result = PeerRanking(
    data["financial_ratios"],
    data["peer_groups"],
    data["analysis"],
    data["companies"],
).calculate()

print(result.head(20))
print("\nRows:", len(result))