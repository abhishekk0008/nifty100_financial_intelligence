"""
Validation Report Generator
"""

from src.data_quality.validator import SchemaValidator


def generate_validation_report(validator):

    df = validator.get_failures()

    validator.save_report()

    return df