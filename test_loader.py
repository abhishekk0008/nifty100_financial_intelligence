from src.etl.loader import ExcelLoader

loader = ExcelLoader()

datasets = loader.load_all()

print("\nLoaded datasets:\n")

for name, df in datasets.items():
    print(f"{name:20} {df.shape}")