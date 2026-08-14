from pathlib import Path
import re

import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CAPITAL_ALLOCATION_FILE = (
    PROJECT_ROOT / "reports" / "capital_allocation.csv"
)

CASHFLOW_INTELLIGENCE_FILE = (
    PROJECT_ROOT / "output" / "cashflow_intelligence.xlsx"
)

PATTERN_DISTRIBUTION_FILE = (
    PROJECT_ROOT
    / "output"
    / "capital_allocation_distribution.csv"
)

PATTERN_CHANGES_FILE = (
    PROJECT_ROOT
    / "output"
    / "pattern_changes.csv"
)


# ============================================================
# CONSTANTS
# ============================================================

EXPECTED_PATTERNS = [
    "Reinvestor",
    "Growth Funded by Debt",
    "Distress Signal",
    "Liquidating Assets",
    "Mixed",
    "Cash Accumulator",
    "Pre-Revenue",
    "Shareholder Returns",
]


# ============================================================
# YEAR NORMALIZATION
# ============================================================

def normalize_year(value):
    """
    Normalize financial year labels.

    Examples
    --------
    Mar 2024 -> Mar 2024
    Mar-24   -> Mar 2024
    Mar/24   -> Mar 2024
    Mar2014  -> Mar 2014
    Mar-2014 -> Mar 2014
    Sep 2024 -> Sep 2024
    """

    if pd.isna(value):
        return pd.NA

    value = str(value).strip()

    if not value:
        return pd.NA

    # Normalize separators
    value = re.sub(r"[-_/]+", " ", value)

    # Normalize multiple spaces
    value = re.sub(r"\s+", " ", value)

    # --------------------------------------------------------
    # Two-digit year
    # --------------------------------------------------------

    match = re.fullmatch(
        r"(Mar|Jun|Sep|Dec)\s*(\d{2})",
        value,
        flags=re.IGNORECASE,
    )

    if match:

        month = match.group(1).title()
        year = 2000 + int(match.group(2))

        return f"{month} {year}"

    # --------------------------------------------------------
    # Four-digit year
    # --------------------------------------------------------

    match = re.fullmatch(
        r"(Mar|Jun|Sep|Dec)\s*(\d{4})",
        value,
        flags=re.IGNORECASE,
    )

    if match:

        month = match.group(1).title()
        year = int(match.group(2))

        return f"{month} {year}"

    # --------------------------------------------------------
    # Generic fallback
    # --------------------------------------------------------

    return value


# ============================================================
# YEAR SORT KEY
# ============================================================

def year_sort_key(value):
    """
    Convert normalized financial year into sortable tuple.

    Example:
        Mar 2024 -> (2024, 3)
        Sep 2024 -> (2024, 9)
    """

    if pd.isna(value):
        return (0, 0)

    value = str(value).strip()

    parts = value.split()

    if len(parts) != 2:
        return (0, 0)

    month_map = {
        "Mar": 3,
        "Jun": 6,
        "Sep": 9,
        "Dec": 12,
    }

    month = month_map.get(
        parts[0].title(),
        0,
    )

    try:
        year = int(parts[1])
    except ValueError:
        year = 0

    return (year, month)


# ============================================================
# LOAD CAPITAL ALLOCATION
# ============================================================

def load_capital_allocation():

    print("=" * 60)
    print("DAY 32 — CAPITAL ALLOCATION REPORT")
    print("=" * 60)

    print("\nLoading capital_allocation.csv...")

    if not CAPITAL_ALLOCATION_FILE.exists():

        raise FileNotFoundError(
            f"Capital allocation file not found:\n"
            f"{CAPITAL_ALLOCATION_FILE}"
        )

    df = pd.read_csv(
        CAPITAL_ALLOCATION_FILE
    )

    required_columns = {
        "company_id",
        "year",
        "pattern_label",
    }

    missing = (
        required_columns
        - set(df.columns)
    )

    if missing:

        raise ValueError(
            "Missing required columns: "
            f"{sorted(missing)}"
        )

    print(
        f"Rows loaded: {len(df)}"
    )

    # --------------------------------------------------------
    # Normalize company IDs
    # --------------------------------------------------------

    df["company_id"] = (
        df["company_id"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    # --------------------------------------------------------
    # Normalize years
    # --------------------------------------------------------

    df["year"] = (
        df["year"]
        .apply(normalize_year)
    )

    # --------------------------------------------------------
    # Normalize pattern labels
    # --------------------------------------------------------

    df["pattern_label"] = (
        df["pattern_label"]
        .astype("string")
        .str.strip()
    )

    print(
        f"Companies: "
        f"{df['company_id'].nunique()}"
    )

    return df


# ============================================================
# DEDUPLICATE COMPANY-YEAR
# ============================================================

def deduplicate_company_year(df):

    print("\nChecking duplicate company-year rows...")

    duplicates = df.duplicated(
        subset=[
            "company_id",
            "year",
        ],
        keep=False,
    )

    duplicate_rows = int(
        duplicates.sum()
    )

    duplicate_combinations = (
        df.loc[
            duplicates,
            [
                "company_id",
                "year",
            ],
        ]
        .drop_duplicates()
        .sort_values(
            [
                "company_id",
                "year",
            ]
        )
    )

    if duplicate_rows == 0:

        print(
            "PASS: No duplicate company-year "
            "rows found."
        )

        return df

    print(
        f"WARNING: {duplicate_rows} duplicate "
        "company-year rows found."
    )

    print(
        "Duplicate company-year combinations: "
        f"{len(duplicate_combinations)}"
    )

    print("\nDuplicate combinations:")

    print(
        duplicate_combinations
        .to_string(index=False)
    )

    # --------------------------------------------------------
    # Important:
    #
    # TCS has:
    #
    # Mar 2013
    # Mar-13
    #
    # After normalization both become:
    #
    # Mar 2013
    #
    # Therefore they are duplicate rows.
    #
    # We keep the row with the most complete data.
    # --------------------------------------------------------

    completeness_columns = [
        "free_cash_flow",
        "cfo_quality",
        "cfo_quality_label",
        "capex_intensity",
        "capex_label",
        "fcf_conversion",
        "cfo_sign",
        "cfi_sign",
        "cff_sign",
        "pattern_label",
    ]

    completeness_columns = [
        col
        for col in completeness_columns
        if col in df.columns
    ]

    df = df.copy()

    df["_completeness"] = (
        df[
            completeness_columns
        ]
        .notna()
        .sum(axis=1)
    )

    # Stable ordering ensures deterministic output.
    df = (
        df
        .sort_values(
            [
                "company_id",
                "year",
                "_completeness",
            ],
            ascending=[
                True,
                True,
                False,
            ],
            kind="stable",
        )
        .drop_duplicates(
            subset=[
                "company_id",
                "year",
            ],
            keep="first",
        )
        .drop(
            columns=[
                "_completeness"
            ]
        )
        .reset_index(drop=True)
    )

    remaining_duplicates = int(
        df.duplicated(
            [
                "company_id",
                "year",
            ]
        ).sum()
    )

    if remaining_duplicates:

        raise ValueError(
            "Duplicate removal failed. "
            f"Remaining duplicates: "
            f"{remaining_duplicates}"
        )

    print(
        "PASS: Duplicate company-year rows "
        "removed successfully."
    )

    return df


# ============================================================
# VERIFY CAPITAL ALLOCATION
# ============================================================

def verify_capital_allocation(df):

    print("\n" + "=" * 60)
    print("1. CAPITAL ALLOCATION VALIDATION")
    print("=" * 60)

    # --------------------------------------------------------
    # Duplicate check
    # --------------------------------------------------------

    duplicate_count = int(
        df.duplicated(
            [
                "company_id",
                "year",
            ]
        ).sum()
    )

    if duplicate_count:

        print(
            f"FAIL: {duplicate_count} duplicate "
            "company-year rows found."
        )

        raise ValueError(
            "Capital allocation data contains "
            "duplicate company-year rows."
        )

    print(
        "PASS: No duplicate company-year rows."
    )

    # --------------------------------------------------------
    # Company count
    # --------------------------------------------------------

    company_count = (
        df["company_id"]
        .nunique()
    )

    print(
        f"Companies: {company_count}"
    )

    print(
        f"Rows: {len(df)}"
    )

    # --------------------------------------------------------
    # Rows per company
    # --------------------------------------------------------

    print("\nRows per company:")

    rows_per_company = (
        df.groupby("company_id")
        .size()
        .sort_values()
    )

    print(
        rows_per_company
        .value_counts()
        .sort_index()
        .to_string()
    )

    # --------------------------------------------------------
    # Missing values
    # --------------------------------------------------------

    print("\nMissing values:")

    print(
        df[
            [
                "company_id",
                "year",
                "pattern_label",
            ]
        ]
        .isna()
        .sum()
        .to_string()
    )

    # --------------------------------------------------------
    # Missing key fields
    # --------------------------------------------------------

    missing_company_ids = int(
        df["company_id"].isna().sum()
    )

    missing_years = int(
        df["year"].isna().sum()
    )

    missing_patterns = int(
        df["pattern_label"].isna().sum()
    )

    if (
        missing_company_ids
        or missing_years
        or missing_patterns
    ):

        raise ValueError(
            "Critical missing values detected "
            "in company_id, year, or pattern_label."
        )

    # --------------------------------------------------------
    # Pattern validation
    # --------------------------------------------------------

    unexpected_patterns = sorted(
        set(
            df["pattern_label"]
            .dropna()
            .unique()
        )
        - set(EXPECTED_PATTERNS)
    )

    if unexpected_patterns:

        print(
            "FAIL: Unexpected pattern labels:"
        )

        print(
            unexpected_patterns
        )

        raise ValueError(
            "Unexpected pattern labels found."
        )

    print(
        "\nPASS: All pattern labels are expected."
    )

    print(
        f"\nCompanies included: "
        f"{company_count}"
    )

    return True


# ============================================================
# GET LATEST YEAR
# ============================================================

def get_latest_year(df):

    years = (
        df["year"]
        .dropna()
        .unique()
    )

    if len(years) == 0:

        raise ValueError(
            "No valid financial years found."
        )

    latest_year = max(
        years,
        key=year_sort_key,
    )

    print("\n" + "=" * 60)
    print("2. LATEST YEAR")
    print("=" * 60)

    print(
        f"Latest year: {latest_year}"
    )

    return latest_year


# ============================================================
# LATEST-YEAR COVERAGE
# ============================================================

def show_latest_year_coverage(df):

    latest_years = (
        df.groupby("company_id")["year"]
        .max(
            key=lambda x: x.map(year_sort_key)
        )
    )

    # pandas groupby max with custom key can be problematic
    # for object values, therefore calculate explicitly.

    records = []

    for company_id, group in df.groupby(
        "company_id"
    ):

        years = group["year"].dropna()

        if years.empty:
            continue

        latest = max(
            years,
            key=year_sort_key,
        )

        records.append(
            {
                "company_id": company_id,
                "latest_year": latest,
            }
        )

    coverage = pd.DataFrame(records)

    coverage_summary = (
        coverage["latest_year"]
        .value_counts()
        .rename_axis("year")
        .reset_index(
            name="company_count"
        )
    )

    coverage_summary["_sort"] = (
        coverage_summary["year"]
        .map(year_sort_key)
    )

    coverage_summary = (
        coverage_summary
        .sort_values("_sort")
        .drop(columns="_sort")
    )

    print("\nLatest-year coverage:")

    print(
        coverage_summary
        .to_string(index=False)
    )

    return coverage_summary


# ============================================================
# GET LATEST ROW PER COMPANY
# ============================================================

def get_latest_company_rows(df):

    data = df.copy()

    data["_year_sort"] = (
        data["year"]
        .map(year_sort_key)
    )

    data = (
        data
        .sort_values(
            [
                "company_id",
                "_year_sort",
            ],
            kind="stable",
        )
        .drop_duplicates(
            subset=[
                "company_id"
            ],
            keep="last",
        )
        .drop(
            columns=[
                "_year_sort"
            ]
        )
        .reset_index(drop=True)
    )

    return data


# ============================================================
# PATTERN DISTRIBUTION
# ============================================================

def generate_pattern_distribution(
    df,
    latest_year,
):

    print("\nPattern distribution:")

    latest = df[
        df["year"] == latest_year
    ].copy()

    # --------------------------------------------------------
    # There should be one row per company after
    # company-year deduplication.
    # --------------------------------------------------------

    latest = (
        latest
        .sort_values(
            "company_id"
        )
        .drop_duplicates(
            subset=[
                "company_id"
            ],
            keep="last",
        )
    )

    company_count = (
        latest["company_id"]
        .nunique()
    )

    if company_count == 0:

        raise ValueError(
            "No companies found for latest year."
        )

    distribution = (
        latest["pattern_label"]
        .value_counts()
        .rename_axis(
            "pattern_label"
        )
        .reset_index(
            name="company_count"
        )
    )

    # --------------------------------------------------------
    # Keep all expected patterns
    # --------------------------------------------------------

    distribution = (
        pd.DataFrame(
            {
                "pattern_label":
                    EXPECTED_PATTERNS
            }
        )
        .merge(
            distribution,
            on="pattern_label",
            how="left",
        )
    )

    distribution["company_count"] = (
        distribution[
            "company_count"
        ]
        .fillna(0)
        .astype(int)
    )

    distribution["latest_year"] = (
        latest_year
    )

    distribution["percentage"] = (
        distribution["company_count"]
        / company_count
        * 100
    ).round(2)

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    total_distribution = int(
        distribution[
            "company_count"
        ].sum()
    )

    if total_distribution != company_count:

        raise ValueError(
            "Pattern distribution does not "
            "sum to total latest-year companies."
        )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    PATTERN_DISTRIBUTION_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    distribution.to_csv(
        PATTERN_DISTRIBUTION_FILE,
        index=False,
    )

    print(
        distribution[
            [
                "pattern_label",
                "company_count",
                "percentage",
            ]
        ]
        .to_string(index=False)
    )

    print(
        f"\nSaved: "
        f"{PATTERN_DISTRIBUTION_FILE}"
    )

    return distribution


# ============================================================
# UPDATE CASHFLOW INTELLIGENCE
# ============================================================

def update_cashflow_intelligence(
    capital_allocation,
):

    print("\n" + "=" * 60)
    print("4. UPDATE CASH FLOW INTELLIGENCE")
    print("=" * 60)

    print(
        "Loading cashflow_intelligence.xlsx..."
    )

    if not CASHFLOW_INTELLIGENCE_FILE.exists():

        raise FileNotFoundError(
            "cashflow_intelligence.xlsx "
            "not found:\n"
            f"{CASHFLOW_INTELLIGENCE_FILE}"
        )

    cashflow = pd.read_excel(
        CASHFLOW_INTELLIGENCE_FILE
    )

    print(
        f"Existing rows: "
        f"{len(cashflow)}"
    )

    if "company_id" not in cashflow.columns:

        raise ValueError(
            "cashflow_intelligence.xlsx "
            "does not contain company_id."
        )

    cashflow["company_id"] = (
        cashflow["company_id"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    # --------------------------------------------------------
    # Get latest capital allocation per company
    # --------------------------------------------------------

    allocation_latest = (
        get_latest_company_rows(
            capital_allocation
        )
        [
            [
                "company_id",
                "pattern_label",
            ]
        ]
        .rename(
            columns={
                "pattern_label":
                    "capital_allocation"
            }
        )
    )

    # --------------------------------------------------------
    # Remove previous generated column
    # --------------------------------------------------------

    if "capital_allocation" in cashflow.columns:

        cashflow = cashflow.drop(
            columns=[
                "capital_allocation"
            ]
        )

    # --------------------------------------------------------
    # Merge
    # --------------------------------------------------------

    cashflow = cashflow.merge(
        allocation_latest,
        on="company_id",
        how="left",
        validate="one_to_one",
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    missing = int(
        cashflow[
            "capital_allocation"
        ]
        .isna()
        .sum()
    )

    print(
        f"Missing capital allocation: "
        f"{missing}"
    )

    if missing:

        missing_companies = sorted(
            cashflow.loc[
                cashflow[
                    "capital_allocation"
                ].isna(),
                "company_id",
            ]
            .dropna()
            .unique()
        )

        print(
            "Companies without allocation:"
        )

        print(
            missing_companies
        )

        raise ValueError(
            "Some companies are missing "
            "capital allocation."
        )

    # --------------------------------------------------------
    # Company validation
    # --------------------------------------------------------

    allocation_companies = set(
        allocation_latest[
            "company_id"
        ]
    )

    cashflow_companies = set(
        cashflow[
            "company_id"
        ]
    )

    missing_from_cashflow = (
        allocation_companies
        - cashflow_companies
    )

    if missing_from_cashflow:

        raise ValueError(
            "Companies from capital allocation "
            "are missing in cashflow intelligence: "
            f"{sorted(missing_from_cashflow)}"
        )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    cashflow.to_excel(
        CASHFLOW_INTELLIGENCE_FILE,
        index=False,
    )

    print(
        "PASS: cashflow_intelligence.xlsx "
        "updated."
    )

    print(
        f"Rows after update: "
        f"{len(cashflow)}"
    )

    return cashflow


# ============================================================
# YEAR-OVER-YEAR PATTERN CHANGES
# ============================================================

def generate_pattern_changes(df):

    print("\n" + "=" * 60)
    print("5. YEAR-OVER-YEAR PATTERN CHANGES")
    print("=" * 60)

    data = df[
        [
            "company_id",
            "year",
            "pattern_label",
        ]
    ].copy()

    # --------------------------------------------------------
    # Normalize again defensively
    # --------------------------------------------------------

    data["year"] = (
        data["year"]
        .apply(normalize_year)
    )

    data["company_id"] = (
        data["company_id"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    # --------------------------------------------------------
    # Safety deduplication
    # --------------------------------------------------------

    data = (
        data
        .sort_values(
            [
                "company_id",
                "year",
            ],
            key=lambda col: (
                col.map(year_sort_key)
                if col.name == "year"
                else col
            ),
            kind="stable",
        )
        .drop_duplicates(
            subset=[
                "company_id",
                "year",
            ],
            keep="last",
        )
        .reset_index(drop=True)
    )

    changes = []

    # --------------------------------------------------------
    # Compare consecutive financial years
    # --------------------------------------------------------

    for company_id, group in data.groupby(
        "company_id"
    ):

        group = group.copy()

        group["_sort_key"] = (
            group["year"]
            .map(year_sort_key)
        )

        group = (
            group
            .sort_values(
                "_sort_key"
            )
            .drop(
                columns=[
                    "_sort_key"
                ]
            )
        )

        rows = group[
            [
                "year",
                "pattern_label",
            ]
        ].to_dict(
            "records"
        )

        for previous, current in zip(
            rows,
            rows[1:],
        ):

            previous_pattern = (
                previous[
                    "pattern_label"
                ]
            )

            current_pattern = (
                current[
                    "pattern_label"
                ]
            )

            # Ignore missing labels
            if (
                pd.isna(previous_pattern)
                or pd.isna(current_pattern)
            ):
                continue

            if (
                previous_pattern
                != current_pattern
            ):

                changes.append(
                    {
                        "company_id":
                            company_id,

                        "previous_year":
                            previous[
                                "year"
                            ],

                        "previous_pattern":
                            previous_pattern,

                        "current_year":
                            current[
                                "year"
                            ],

                        "current_pattern":
                            current_pattern,

                        "pattern_change": (
                            f"{previous_pattern}"
                            " -> "
                            f"{current_pattern}"
                        ),
                    }
                )

    # --------------------------------------------------------
    # DataFrame
    # --------------------------------------------------------

    changes_df = pd.DataFrame(
        changes,
        columns=[
            "company_id",
            "previous_year",
            "previous_pattern",
            "current_year",
            "current_pattern",
            "pattern_change",
        ],
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    PATTERN_CHANGES_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    changes_df.to_csv(
        PATTERN_CHANGES_FILE,
        index=False,
    )

    print(
        f"Pattern changes found: "
        f"{len(changes_df)}"
    )

    if not changes_df.empty:

        print("\nSample changes:")

        print(
            changes_df
            .head(20)
            .to_string(index=False)
        )

    else:

        print(
            "No year-over-year pattern "
            "changes found."
        )

    print(
        f"\nSaved: "
        f"{PATTERN_CHANGES_FILE}"
    )

    return changes_df


# ============================================================
# FINAL OUTPUT VALIDATION
# ============================================================

def final_validation(df):

    print("\n" + "=" * 60)
    print("6. FINAL OUTPUT VALIDATION")
    print("=" * 60)

    # --------------------------------------------------------
    # Duplicate company-year check
    # --------------------------------------------------------

    duplicates = int(
        df.duplicated(
            [
                "company_id",
                "year",
            ]
        ).sum()
    )

    print(
        f"Duplicate company-year rows: "
        f"{duplicates}"
    )

    if duplicates != 0:

        raise ValueError(
            "Final output contains duplicate "
            "company-year rows."
        )

    print(
        "PASS: No duplicate company-year rows."
    )

    # --------------------------------------------------------
    # Company count
    # --------------------------------------------------------

    companies = (
        df["company_id"]
        .nunique()
    )

    print(
        f"Companies: {companies}"
    )

    # --------------------------------------------------------
    # Missing critical fields
    # --------------------------------------------------------

    critical_missing = (
        df[
            [
                "company_id",
                "year",
                "pattern_label",
            ]
        ]
        .isna()
        .sum()
    )

    print("\nCritical missing values:")

    print(
        critical_missing
        .to_string()
    )

    if critical_missing.sum() != 0:

        raise ValueError(
            "Critical missing values "
            "remain in final output."
        )

    print(
        "PASS: Critical fields complete."
    )

    # --------------------------------------------------------
    # TCS-specific regression test
    # --------------------------------------------------------

    if "TCS" in set(
        df["company_id"]
    ):

        tcs = df[
            df["company_id"] == "TCS"
        ]

        tcs_years = (
            tcs["year"]
            .tolist()
        )

        expected_tcs_years = [
            f"Mar {year}"
            for year in range(
                2013,
                2025,
            )
        ]

        if set(tcs_years) == set(
            expected_tcs_years
        ):

            print(
                "PASS: TCS financial years "
                "normalized correctly."
            )

        else:

            print(
                "WARNING: TCS year coverage "
                "differs from expected 2013-2024."
            )

            print(
                sorted(
                    tcs_years,
                    key=year_sort_key,
                )
            )

    # --------------------------------------------------------
    # Final row count
    # --------------------------------------------------------

    print(
        f"\nFinal rows: {len(df)}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    df = load_capital_allocation()

    # --------------------------------------------------------
    # Normalize + remove duplicate company-year rows
    # --------------------------------------------------------

    df = deduplicate_company_year(
        df
    )

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    verify_capital_allocation(
        df
    )

    # --------------------------------------------------------
    # Latest year
    # --------------------------------------------------------

    latest_year = get_latest_year(
        df
    )

    # --------------------------------------------------------
    # Latest-year coverage
    # --------------------------------------------------------

    show_latest_year_coverage(
        df
    )

    # --------------------------------------------------------
    # Pattern distribution
    # --------------------------------------------------------

    generate_pattern_distribution(
        df,
        latest_year,
    )

    # --------------------------------------------------------
    # Update cashflow intelligence
    # --------------------------------------------------------

    update_cashflow_intelligence(
        df
    )

    # --------------------------------------------------------
    # Pattern changes
    # --------------------------------------------------------

    generate_pattern_changes(
        df
    )

    # --------------------------------------------------------
    # Final validation
    # --------------------------------------------------------

    final_validation(
        df
    )

    # --------------------------------------------------------
    # Complete
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("DAY 32 REPORT COMPLETE")
    print("=" * 60)

    print(
        f"\n1. "
        f"{PATTERN_DISTRIBUTION_FILE}"
    )

    print(
        f"2. "
        f"{CASHFLOW_INTELLIGENCE_FILE}"
    )

    print(
        f"3. "
        f"{PATTERN_CHANGES_FILE}"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()