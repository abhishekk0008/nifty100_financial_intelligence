"""
Day 35 — Portfolio Summary PDF

Generates:
    reports/portfolio/portfolio_summary.pdf

Requirements:
- One page per company
- Alphabetical ticker order
- Company name + broad sector
- Top 6 KPIs
- Trend arrows:
    ↑ improved
    ↓ declined
    → flat within 2%
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ============================================================
# PATHS
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT_DIR / "data" / "raw"
REPORT_DIR = ROOT_DIR / "reports" / "portfolio"

COMPANIES_FILE = DATA_DIR / "companies.xlsx"
SECTORS_FILE = DATA_DIR / "sectors.xlsx"
RATIOS_FILE = DATA_DIR / "financial_ratios.xlsx"

OUTPUT_FILE = REPORT_DIR / "portfolio_summary.pdf"


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# LOADERS
# ============================================================


def normalize_company_id(value: object) -> str:
    """Normalize ticker/company identifier."""

    if pd.isna(value):
        return ""

    value = str(value).strip().upper()

    # Remove Excel-style .0 if present.
    if value.endswith(".0"):
        value = value[:-2]

    return value


def detect_header_row(
    file_path: Path,
    required_columns: set[str],
    max_rows: int = 10,
) -> int:
    """
    Detect the actual header row.

    Some source Excel files contain title rows before
    the actual table header.
    """

    preview = pd.read_excel(
        file_path,
        header=None,
        nrows=max_rows,
    )

    for index, row in preview.iterrows():

        values = {
            str(value).strip().lower()
            for value in row.tolist()
            if not pd.isna(value)
        }

        required = {
            column.lower()
            for column in required_columns
        }

        if required.issubset(values):
            return int(index)

    raise ValueError(
        f"Could not detect header row in {file_path}"
    )


def load_companies() -> pd.DataFrame:
    """Load company master data."""

    header_row = detect_header_row(
        COMPANIES_FILE,
        {
            "id",
            "company_name",
            "roe_percentage",
        },
    )

    logger.info(
        "companies.xlsx detected header row: %s",
        header_row,
    )

    df = pd.read_excel(
        COMPANIES_FILE,
        header=header_row,
    )

    df["company_id"] = (
        df["id"]
        .apply(normalize_company_id)
    )

    return df


def load_sectors() -> pd.DataFrame:
    """Load sector mapping."""

    df = pd.read_excel(
        SECTORS_FILE
    )

    df["company_id"] = (
        df["company_id"]
        .apply(normalize_company_id)
    )

    return df


def load_ratios() -> pd.DataFrame:
    """Load financial ratios."""

    df = pd.read_excel(
        RATIOS_FILE
    )

    df["company_id"] = (
        df["company_id"]
        .apply(normalize_company_id)
    )

    return df


# ============================================================
# YEAR HANDLING
# ============================================================


def year_sort_key(value: object) -> tuple[int, str]:
    """
    Convert strings such as:
        Dec 2012
        Mar 2024
        FY 2025

    into sortable year keys.
    """

    if pd.isna(value):
        return (0, "")

    text = str(value).strip()

    match = re.search(
        r"(19|20)\d{2}",
        text,
    )

    if match:
        return (
            int(match.group()),
            text,
        )

    return (0, text)


def prepare_latest_year_data(
    ratios: pd.DataFrame,
) -> pd.DataFrame:
    """
    Prepare one financial-ratio observation per
    company/year.

    Duplicate company-year rows are averaged.
    """

    numeric_columns = [
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "debt_to_equity",
        "interest_coverage",
        "asset_turnover",
        "free_cash_flow_cr",
        "earnings_per_share",
    ]

    available_numeric = [
        column
        for column in numeric_columns
        if column in ratios.columns
    ]

    # Convert numeric fields safely.
    for column in available_numeric:
        ratios[column] = pd.to_numeric(
            ratios[column],
            errors="coerce",
        )

    # Handle duplicate company/year observations.
    grouped = (
        ratios
        .groupby(
            ["company_id", "year"],
            as_index=False,
        )[available_numeric]
        .mean()
    )

    # Recover year sorting.
    grouped["_year_sort"] = (
        grouped["year"]
        .apply(year_sort_key)
    )

    grouped = grouped.sort_values(
        ["company_id", "_year_sort"]
    )

    # Latest observation.
    latest = (
        grouped
        .groupby(
            "company_id",
            as_index=False,
        )
        .tail(1)
        .copy()
    )

    # Previous observation.
    previous = (
        grouped
        .groupby(
            "company_id",
            as_index=False,
        )
        .nth(-2)
        .reset_index()
    )

    # If pandas does not preserve company_id correctly
    # in nth output, rebuild through explicit sorting.
    if "company_id" not in previous.columns:
        previous = (
            grouped
            .sort_values(
                ["company_id", "_year_sort"]
            )
            .groupby(
                "company_id",
                as_index=False,
            )
            .apply(
                lambda group: group.iloc[-2]
                if len(group) >= 2
                else pd.Series(dtype=object)
            )
            .reset_index(drop=True)
        )

    latest = latest.drop(
        columns=["_year_sort"],
        errors="ignore",
    )

    previous = previous.drop(
        columns=["_year_sort"],
        errors="ignore",
    )

    latest = latest.rename(
        columns={
            column: f"latest_{column}"
            for column in available_numeric
        }
    )

    previous = previous.rename(
        columns={
            column: f"previous_{column}"
            for column in available_numeric
        }
    )

    latest_columns = [
        "company_id",
        "year",
    ] + [
        f"latest_{column}"
        for column in available_numeric
    ]

    latest = latest[
        [
            column
            for column in latest_columns
            if column in latest.columns
        ]
    ]

    previous_columns = [
        "company_id"
    ] + [
        f"previous_{column}"
        for column in available_numeric
    ]

    previous = previous[
        [
            column
            for column in previous_columns
            if column in previous.columns
        ]
    ]

    result = latest.merge(
        previous,
        on="company_id",
        how="left",
    )

    return result


# ============================================================
# TREND LOGIC
# ============================================================


def trend_arrow(
    latest: object,
    previous: object,
) -> str:
    """
    Determine trend.

    Flat means change is within 2%.

    For values where previous is zero or unavailable:
        no reliable trend => →
    """

    try:

        latest_value = float(latest)
        previous_value = float(previous)

    except (TypeError, ValueError):

        return "→"

    if pd.isna(latest_value) or pd.isna(previous_value):
        return "→"

    if previous_value == 0:
        return "→"

    change = (
        (latest_value - previous_value)
        / abs(previous_value)
    )

    if abs(change) <= 0.02:
        return "→"

    if change > 0:
        return "↑"

    return "↓"


def format_value(
    value: object,
    suffix: str = "",
) -> str:
    """Format KPI value."""

    try:

        number = float(value)

    except (TypeError, ValueError):

        return "N/A"

    if pd.isna(number):
        return "N/A"

    if abs(number) >= 1000:
        text = f"{number:,.0f}"

    elif abs(number) >= 100:
        text = f"{number:,.1f}"

    else:
        text = f"{number:,.2f}"

    return f"{text}{suffix}"


# ============================================================
# PDF STYLES
# ============================================================


def create_styles():
    """Create ReportLab styles."""

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="PortfolioTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            alignment=TA_LEFT,
            spaceAfter=4 * mm,
        )
    )

    styles.add(
        ParagraphStyle(
            name="CompanyName",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#222222"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectorText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#666666"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="KPIHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=TA_LEFT,
        )
    )

    styles.add(
        ParagraphStyle(
            name="KPIValue",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=TA_RIGHT,
        )
    )

    styles.add(
        ParagraphStyle(
            name="Footer",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#777777"),
            alignment=TA_CENTER,
        )
    )

    return styles


# ============================================================
# PAGE HEADER / FOOTER
# ============================================================


def draw_page(canvas, doc):
    """Draw page number/footer."""

    canvas.saveState()

    width, height = A4

    canvas.setStrokeColor(
        colors.HexColor("#DDDDDD")
    )

    canvas.line(
        18 * mm,
        12 * mm,
        width - 18 * mm,
        12 * mm,
    )

    canvas.setFont(
        "Helvetica",
        7,
    )

    canvas.setFillColor(
        colors.HexColor("#777777")
    )

    canvas.drawCentredString(
        width / 2,
        7 * mm,
        f"Portfolio Summary | Page {doc.page}",
    )

    canvas.restoreState()


# ============================================================
# KPI CONFIGURATION
# ============================================================


KPI_CONFIG = [
    (
        "Net Profit Margin",
        "net_profit_margin_pct",
        "%",
    ),
    (
        "Operating Profit Margin",
        "operating_profit_margin_pct",
        "%",
    ),
    (
        "Return on Equity",
        "return_on_equity_pct",
        "%",
    ),
    (
        "Debt / Equity",
        "debt_to_equity",
        "",
    ),
    (
        "Interest Coverage",
        "interest_coverage",
        "x",
    ),
    (
        "Earnings Per Share",
        "earnings_per_share",
        "",
    ),
]


# ============================================================
# COMPANY PAGE
# ============================================================


def build_company_page(
    row: pd.Series,
    styles,
) -> list:

    story = []

    company_id = normalize_company_id(
        row.get("company_id", "")
    )

    company_name = (
        row.get("company_name")
        if pd.notna(
            row.get("company_name")
        )
        else company_id
    )

    sector = (
        row.get("broad_sector")
        if pd.notna(
            row.get("broad_sector")
        )
        else "N/A"
    )

    latest_year = row.get(
        "year",
        "N/A",
    )

    story.append(
        Paragraph(
            "Portfolio Summary",
            styles["PortfolioTitle"],
        )
    )

    story.append(
        Paragraph(
            str(company_id),
            styles["CompanyName"],
        )
    )

    story.append(
        Paragraph(
            str(company_name),
            styles["CompanyName"],
        )
    )

    story.append(
        Spacer(
            1,
            1.5 * mm,
        )
    )

    story.append(
        Paragraph(
            f"Sector: {sector}",
            styles["SectorText"],
        )
    )

    story.append(
        Paragraph(
            f"Latest financial year: {latest_year}",
            styles["SectorText"],
        )
    )

    story.append(
        Spacer(
            1,
            7 * mm,
        )
    )

    table_data = [
        [
            Paragraph(
                "KPI",
                styles["KPIHeader"],
            ),
            Paragraph(
                "Latest",
                styles["KPIHeader"],
            ),
            Paragraph(
                "Trend",
                styles["KPIHeader"],
            ),
        ]
    ]

    for label, column, suffix in KPI_CONFIG:

        latest_column = (
            f"latest_{column}"
        )

        previous_column = (
            f"previous_{column}"
        )

        latest_value = row.get(
            latest_column
        )

        previous_value = row.get(
            previous_column
        )

        arrow = trend_arrow(
            latest_value,
            previous_value,
        )

        formatted = format_value(
            latest_value,
            suffix,
        )

        table_data.append(
            [
                Paragraph(
                    label,
                    styles["KPIHeader"],
                ),
                Paragraph(
                    formatted,
                    styles["KPIValue"],
                ),
                Paragraph(
                    arrow,
                    ParagraphStyle(
                        f"Arrow_{column}",
                        parent=styles["KPIValue"],
                        alignment=TA_CENTER,
                        fontSize=15,
                    ),
                ),
            ]
        )

    table = Table(
        table_data,
        colWidths=[
            90 * mm,
            55 * mm,
            25 * mm,
        ],
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#EEEEEE"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#222222"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#DDDDDD"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
            ]
        )
    )

    story.append(table)

    story.append(
        Spacer(
            1,
            12 * mm,
        )
    )

    story.append(
        Paragraph(
            "Trend methodology: ↑ = improved, ↓ = declined, "
            "→ = flat within ±2% versus the previous available year.",
            styles["Footer"],
        )
    )

    return story


# ============================================================
# GENERATOR
# ============================================================


def generate_portfolio_summary() -> Path:
    """Generate complete portfolio PDF."""

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    logger.info(
        "Loading portfolio source datasets..."
    )

    companies = load_companies()
    sectors = load_sectors()
    ratios = load_ratios()

    logger.info(
        "Companies loaded: %s",
        len(companies),
    )

    logger.info(
        "Sectors loaded: %s",
        len(sectors),
    )

    logger.info(
        "Ratio rows loaded: %s",
        len(ratios),
    )

    latest_data = prepare_latest_year_data(
        ratios
    )

    # Merge company information.
    portfolio = companies.merge(
        sectors[
            [
                "company_id",
                "broad_sector",
            ]
        ],
        on="company_id",
        how="left",
        suffixes=("", "_sector"),
    )

    portfolio = portfolio.merge(
        latest_data,
        on="company_id",
        how="left",
    )

    # Alphabetical ticker order.
    portfolio = portfolio.sort_values(
        "company_id"
    ).reset_index(drop=True)

    logger.info(
        "Portfolio companies after merge: %s",
        len(portfolio),
    )

    if len(portfolio) != 92:

        raise ValueError(
            f"Expected 92 companies, "
            f"found {len(portfolio)}"
        )

    styles = create_styles()

    doc = BaseDocTemplate(
        str(OUTPUT_FILE),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title="Nifty 100 Portfolio Summary",
        author="Nifty 100 Financial Intelligence",
    )

    width, height = A4

    frame = Frame(
        18 * mm,
        18 * mm,
        width - 36 * mm,
        height - 34 * mm,
        id="portfolio",
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )

    template = PageTemplate(
        id="portfolio",
        frames=[frame],
        onPage=draw_page,
    )

    doc.addPageTemplates(
        [template]
    )

    story = []

    for index, row in portfolio.iterrows():

        ticker = row["company_id"]

        logger.info(
            "Building portfolio page %s/92: %s",
            index + 1,
            ticker,
        )

        story.extend(
            build_company_page(
                row,
                styles,
            )
        )

        if index < len(portfolio) - 1:
            story.append(PageBreak())

    doc.build(story)

    logger.info(
        "Portfolio summary saved: %s",
        OUTPUT_FILE,
    )

    return OUTPUT_FILE


# ============================================================
# MAIN
# ============================================================


def main() -> None:

    output = generate_portfolio_summary()

    print()
    print("=" * 70)
    print("DAY 35 — PORTFOLIO SUMMARY")
    print("=" * 70)
    print(
        f"Output : {output}"
    )
    print(
        f"Companies: 92"
    )
    print(
        "Pages: 92"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()