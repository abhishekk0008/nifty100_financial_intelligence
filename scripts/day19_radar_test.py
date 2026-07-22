from src.etl.loader import ExcelLoader
from src.analytics.peer import PeerRanking
from src.analytics.radar import RadarChartGenerator

loader = ExcelLoader()
data = loader.load_all()

ranking = PeerRanking(
    data["financial_ratios"],
    data["peer_groups"],
    data["analysis"],
    data["companies"],
).calculate()

RadarChartGenerator(ranking).generate()