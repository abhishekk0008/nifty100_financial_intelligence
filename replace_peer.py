from pathlib import Path

path = Path("src/analytics/peer.py")

text = path.read_text(encoding="utf-8")

old = """return final"""

new = """
# Keep only latest year for each company + metric
final["year_num"] = (
    final["year"]
    .astype(str)
    .str.extract(r"(\\d{4})")[0]
    .astype(int)
)

final = (
    final.sort_values(
        ["company_id", "metric", "year_num"]
    )
    .groupby(
        ["company_id", "metric"],
        group_keys=False,
    )
    .tail(1)
    .drop(columns="year_num")
    .reset_index(drop=True)
)

return final
"""

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")

print("peer.py updated successfully.")