"""
Schema Validator
"""

from pathlib import Path
import logging
import pandas as pd

from src.data_quality.rules import (
    dq01_pk_uniqueness,
    dq02_company_year_uniqueness
)

logger = logging.getLogger(__name__)


class SchemaValidator:

    def __init__(self):
        self.failures = []

    def add_failure(self, table, rule, severity, company, year, message):
        self.failures.append({
            "table": table,
            "rule": rule,
            "severity": severity,
            "company": company,
            "year": year,
            "message": message
        })

    def validate_pk(self, table_name, df, pk_column):

        duplicates = dq01_pk_uniqueness(df, pk_column)

        for _, row in duplicates.iterrows():
            self.add_failure(
                table=table_name,
                rule="DQ-01",
                severity="CRITICAL",
                company=row.get("company_name", ""),
                year=row.get("year", ""),
                message=f"Duplicate Primary Key: {pk_column}"
            )

    def validate_company_year(self, table_name, df):

        duplicates = dq02_company_year_uniqueness(df)

        for _, row in duplicates.iterrows():
            self.add_failure(
                table=table_name,
                rule="DQ-02",
                severity="CRITICAL",
                company=row.get("company_name", ""),
                year=row.get("year", ""),
                message="Duplicate company_id + year"
            )

    def get_failures(self):
        return pd.DataFrame(self.failures)

    def save_report(self, output_path="output/validation_failures.csv"):

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        self.get_failures().to_csv(output_path, index=False)

        logger.info(f"Validation report saved to {output_path}")