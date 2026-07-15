from src.etl.loader import ExcelLoader

loader = ExcelLoader()
data = loader.load_all()

companies = data["companies"]
profit = data["profit_loss"]

company_ids = (
    companies["id"]
    .astype(str)
    .str.strip()
)

profit_ids = (
    profit["company_id"]
    .astype(str)
    .str.strip()
)

missing = sorted(set(profit_ids) - set(company_ids))

print("=" * 60)
print("Missing company ids:", len(missing))
print("=" * 60)

for x in missing:
    print(repr(x))