from src.etl.normalizer import normalize_ticker, normalize_year

print(normalize_ticker(" tcs "))
print(normalize_ticker("infy"))
print(normalize_year("Mar-23"))
print(normalize_year("Dec-22"))