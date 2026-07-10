import pandas as pd

from src.data_quality.validator import SchemaValidator

validator = SchemaValidator()

validator.add_failure(
    table="companies",
    rule="DQ-01",
    severity="CRITICAL",
    company="TCS",
    year=2024,
    message="Duplicate Primary Key"
)

print(validator.get_failures())