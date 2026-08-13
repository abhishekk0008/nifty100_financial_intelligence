"""
Day 34 — Sector Report Generation

Generates one PDF report for every broad sector found in
data/raw/sectors.xlsx.

Each sector PDF contains:
    1. Sector summary
    2. Median KPIs
    3. All companies in the sector
    4. Eight financial metrics for every company

Output:
    reports/sector/<sector>_report.pdf
"""

from __future__ import annotations

import logging
import re
import sys
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

SECTOR_FILE = DATA_DIR / "sectors.xlsx"
RATIOS_FILE = DATA_DIR / "financial_ratios.xlsx"

REPORT_DIR = ROOT_DIR / "reports" / "sector"


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# METRICS
# ============================================================

METRICS = {
    "net_profit_margin_pct": "Net Profit Margin",
    "operating_profit_margin_pct": "Operating Profit Margin",
    "return_on_equity_pct": "ROE",
    "debt_to_equity": "Debt / Equity",
    "interest_coverage": "Interest Coverage",
    "asset_turnover": "Asset Turnover",
    "free_cash_flow_cr": "Free Cash Flow",
    "earnings_per_share": "EPS",
}


PERCENT_METRICS = {
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
    "return_on_equity_pct",
}


RUPEE_METRICS = {
    "free_cash_flow_cr",
    "earnings_per_share",
}


# ============================================================
# HELPERS
# ============================================================

def clean_sector_name(value: object) -> str:
    """Convert sector name into a safe filesystem name."""

    value = str(value).strip()

    value = re.sub(
        r"[^\w\s-]",
        "",
        value,
    )

    value = re.sub(
        r"\s+",
        "_",
        value,
    )

    return value


def format_value(
    value: object,
    column: str,
) -> str:
    """Format a financial metric for display."""

    if pd.isna(value):
        return "N/A"

    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)

    if column in PERCENT_METRICS:
        return f"{number:,.2f}%"

    if column == "free_cash_flow_cr":
        return f"{number:,.2f} Cr"

    if column == "earnings_per_share":
        return f"{number:,.2f}"

    if column in {
        "debt_to_equity",
        "interest_coverage",
        "asset_turnover",
    }:
        return f"{number:,.2f}"

    return f"{number:,.2f}"


def extract_year(value: object) -> float:
    """
    Extract the four-digit year from values such as:

        Dec 2024
        Mar 2025
        2024
    """

    match = re.search(
        r"(\d{4})",
        str(value),
    )

    if not match:
        return float("nan")

    return float(match.group(1))


# ============================================================
# DATA LOADING
# ============================================================

def load_sector_data() -> pd.DataFrame:
    """Load company-sector mapping."""

    logger.info(
        "Loading sectors.xlsx..."
    )

    df = pd.read_excel(
        SECTOR_FILE
    )

    required = {
        "company_id",
        "broad_sector",
    }

    missing = required.difference(
        df.columns
    )

    if missing:
        raise ValueError(
            "sectors.xlsx missing columns: "
            f"{sorted(missing)}"
        )

    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["broad_sector"] = (
        df["broad_sector"]
        .astype(str)
        .str.strip()
    )

    logger.info(
        "Sector rows loaded: %s",
        len(df),
    )

    return df


def load_ratio_data() -> pd.DataFrame:
    """Load financial ratios."""

    logger.info(
        "Loading financial_ratios.xlsx..."
    )

    df = pd.read_excel(
        RATIOS_FILE
    )

    required = {
        "company_id",
        "year",
        *METRICS.keys(),
    }

    missing = required.difference(
        df.columns
    )

    if missing:
        raise ValueError(
            "financial_ratios.xlsx missing columns: "
            f"{sorted(missing)}"
        )

    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["_year_num"] = (
        df["year"]
        .apply(extract_year)
    )

    logger.info(
        "Financial ratio rows loaded: %s",
        len(df),
    )

    return df


# ============================================================
# LATEST YEAR DATA
# ============================================================

def get_latest_company_ratios(
    ratios: pd.DataFrame,
) -> pd.DataFrame:
    """
    Select the latest available financial-ratio row
    for each company.
    """

    data = ratios.copy()

    data = data.sort_values(
        [
            "company_id",
            "_year_num",
        ]
    )

    latest = (
        data
        .groupby(
            "company_id",
            as_index=False,
        )
        .tail(1)
        .copy()
    )

    latest = latest.drop_duplicates(
        subset=["company_id"],
        keep="last",
    )

    logger.info(
        "Latest company ratio rows: %s",
        len(latest),
    )

    return latest


# ============================================================
# SECTOR SUMMARY
# ============================================================

def calculate_sector_medians(
    sector_companies: pd.DataFrame,
    latest_ratios: pd.DataFrame,
) -> pd.Series:
    """Calculate median value of each metric for a sector."""

    merged = sector_companies[
        [
            "company_id",
        ]
    ].merge(
        latest_ratios[
            [
                "company_id",
                *METRICS.keys(),
            ]
        ],
        on="company_id",
        how="left",
    )

    return merged[
        list(METRICS.keys())
    ].median(
        numeric_only=True
    )


# ============================================================
# PAGE HEADER / FOOTER
# ============================================================

def draw_page_header_footer(
    canvas,
    doc,
):
    """Draw report header and page number."""

    canvas.saveState()

    width, height = A4

    canvas.setFont(
        "Helvetica-Bold",
        8,
    )

    canvas.setFillColor(
        colors.HexColor("#666666")
    )

    canvas.drawString(
        15 * mm,
        height - 10 * mm,
        "NIFTY 100 FINANCIAL INTELLIGENCE",
    )

    canvas.setFont(
        "Helvetica",
        8,
    )

    canvas.drawRightString(
        width - 15 * mm,
        8 * mm,
        f"Page {doc.page}",
    )

    canvas.restoreState()


# ============================================================
# STYLES
# ============================================================

def create_styles():
    """Create ReportLab styles."""

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="SectorTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            alignment=TA_LEFT,
            spaceAfter=8 * mm,
        )
    )

    styles.add(
        ParagraphStyle(
            name="Subtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#666666"),
            spaceAfter=5 * mm,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#222222"),
            spaceBefore=4 * mm,
            spaceAfter=3 * mm,
        )
    )

    styles.add(
        ParagraphStyle(
            name="Small",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SmallCenter",
            parent=styles["Small"],
            alignment=TA_CENTER,
        )
    )

    return styles


# ============================================================
# SUMMARY TABLE
# ============================================================

def build_summary_table(
    medians: pd.Series,
    styles,
):
    """Build median KPI table."""

    data = [
        [
            Paragraph(
                "<b>Median KPI</b>",
                styles["SmallCenter"],
            ),
            Paragraph(
                "<b>Sector Median</b>",
                styles["SmallCenter"],
            ),
        ]
    ]

    for column, label in METRICS.items():

        value = format_value(
            medians.get(column),
            column,
        )

        data.append(
            [
                Paragraph(
                    label,
                    styles["Small"],
                ),
                Paragraph(
                    value,
                    styles["SmallCenter"],
                ),
            ]
        )

    table = Table(
        data,
        colWidths=[
            90 * mm,
            70 * mm,
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
                    colors.HexColor("#1F2937"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor("#D1D5DB"),
                ),
                (
                    "BACKGROUND",
                    (0, 1),
                    (-1, -1),
                    colors.HexColor("#F9FAFB"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "ALIGN",
                    (1, 1),
                    (1, -1),
                    "RIGHT",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    return table


# ============================================================
# COMPANY TABLE
# ============================================================

def build_company_table(
    sector_companies: pd.DataFrame,
    latest_ratios: pd.DataFrame,
    styles,
):
    """
    Build company-level table containing all companies
    and eight required financial metrics.
    """

    merged = sector_companies[
        [
            "company_id",
        ]
    ].merge(
        latest_ratios[
            [
                "company_id",
                "year",
                *METRICS.keys(),
            ]
        ],
        on="company_id",
        how="left",
    )

    merged = merged.sort_values(
        "company_id"
    )

    headers = [
        "Company",
        "Year",
        "NPM",
        "OPM",
        "ROE",
        "D/E",
        "Interest<br/>Coverage",
        "Asset<br/>Turnover",
        "FCF<br/>(Cr)",
        "EPS",
    ]

    data = [
        [
            Paragraph(
                f"<b>{header}</b>",
                styles["SmallCenter"],
            )
            for header in headers
        ]
    ]

    for _, row in merged.iterrows():

        data.append(
            [
                Paragraph(
                    str(row["company_id"]),
                    styles["Small"],
                ),

                Paragraph(
                    str(row["year"])
                    if not pd.isna(row["year"])
                    else "N/A",
                    styles["SmallCenter"],
                ),

                Paragraph(
                    format_value(
                        row["net_profit_margin_pct"],
                        "net_profit_margin_pct",
                    ),
                    styles["SmallCenter"],
                ),

                Paragraph(
                    format_value(
                        row["operating_profit_margin_pct"],
                        "operating_profit_margin_pct",
                    ),
                    styles["SmallCenter"],
                ),

                Paragraph(
                    format_value(
                        row["return_on_equity_pct"],
                        "return_on_equity_pct",
                    ),
                    styles["SmallCenter"],
                ),

                Paragraph(
                    format_value(
                        row["debt_to_equity"],
                        "debt_to_equity",
                    ),
                    styles["SmallCenter"],
                ),

                Paragraph(
                    format_value(
                        row["interest_coverage"],
                        "interest_coverage",
                    ),
                    styles["SmallCenter"],
                ),

                Paragraph(
                    format_value(
                        row["asset_turnover"],
                        "asset_turnover",
                    ),
                    styles["SmallCenter"],
                ),

                Paragraph(
                    format_value(
                        row["free_cash_flow_cr"],
                        "free_cash_flow_cr",
                    ),
                    styles["SmallCenter"],
                ),

                Paragraph(
                    format_value(
                        row["earnings_per_share"],
                        "earnings_per_share",
                    ),
                    styles["SmallCenter"],
                ),
            ]
        )

    col_widths = [
        24 * mm,
        18 * mm,
        16 * mm,
        16 * mm,
        16 * mm,
        14 * mm,
        21 * mm,
        20 * mm,
        21 * mm,
        16 * mm,
    ]

    table = Table(
        data,
        colWidths=col_widths,
        repeatRows=1,
        splitByRow=1,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#1F2937"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    colors.HexColor("#D1D5DB"),
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#F8FAFC"),
                    ],
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
                    3,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
            ]
        )
    )

    return table


# ============================================================
# SINGLE SECTOR REPORT
# ============================================================

def generate_sector_report(
    sector: str,
    sector_data: pd.DataFrame,
    latest_ratios: pd.DataFrame,
    styles,
) -> Path:
    """Generate one sector PDF."""

    safe_name = clean_sector_name(
        sector
    )

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = (
        REPORT_DIR
        / f"{safe_name}_report.pdf"
    )

    logger.info(
        "Generating sector report: %s",
        sector,
    )

    sector_companies = sector_data[
        sector_data["broad_sector"]
        .eq(sector)
    ].copy()

    medians = calculate_sector_medians(
        sector_companies,
        latest_ratios,
    )

    doc = BaseDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=16 * mm,
        bottomMargin=14 * mm,
        title=f"{sector} Sector Report",
        author="NIFTY 100 Financial Intelligence",
    )

    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id="normal",
    )

    template = PageTemplate(
        id="sector",
        frames=[frame],
        onPage=draw_page_header_footer,
    )

    doc.addPageTemplates(
        [template]
    )

    story = []

    # --------------------------------------------------------
    # PAGE 1 — SECTOR SUMMARY
    # --------------------------------------------------------

    story.append(
        Paragraph(
            f"{sector}",
            styles["SectorTitle"],
        )
    )

    story.append(
        Paragraph(
            "Sector Financial Intelligence Report",
            styles["Subtitle"],
        )
    )

    story.append(
        Paragraph(
            f"<b>Companies:</b> "
            f"{len(sector_companies)}",
            styles["Normal"],
        )
    )

    story.append(
        Spacer(
            1,
            6 * mm,
        )
    )

    story.append(
        Paragraph(
            "Sector Median KPIs",
            styles["SectionTitle"],
        )
    )

    story.append(
        build_summary_table(
            medians,
            styles,
        )
    )

    story.append(
        Spacer(
            1,
            8 * mm,
        )
    )

    story.append(
        Paragraph(
            "Methodology",
            styles["SectionTitle"],
        )
    )

    story.append(
        Paragraph(
            (
                "Sector medians are calculated from the latest "
                "available financial-ratio observation for each "
                "company in the sector. Missing metric values "
                "are excluded from the corresponding median."
            ),
            styles["Normal"],
        )
    )

    story.append(
        Spacer(
            1,
            5 * mm,
        )
    )

    story.append(
        Paragraph(
            (
                "The company table contains the eight selected "
                "financial metrics used for sector-level comparison."
            ),
            styles["Normal"],
        )
    )

    # --------------------------------------------------------
    # PAGE 2+ — COMPANY DETAILS
    # --------------------------------------------------------

    story.append(
        PageBreak()
    )

    story.append(
        Paragraph(
            f"{sector} — Company Comparison",
            styles["SectionTitle"],
        )
    )

    story.append(
        Paragraph(
            (
                f"{len(sector_companies)} companies "
                "with latest available financial metrics."
            ),
            styles["Subtitle"],
        )
    )

    story.append(
        build_company_table(
            sector_companies,
            latest_ratios,
            styles,
        )
    )

    doc.build(
        story
    )

    logger.info(
        "Sector report saved: %s",
        output,
    )

    return output


# ============================================================
# VALIDATION
# ============================================================

def validate_pdf(
    path: Path,
) -> bool:
    """Basic PDF validation."""

    if not path.exists():
        logger.error(
            "Missing PDF: %s",
            path,
        )
        return False

    if path.stat().st_size <= 0:
        logger.error(
            "Empty PDF: %s",
            path,
        )
        return False

    try:

        from pypdf import PdfReader

        reader = PdfReader(
            str(path)
        )

        page_count = len(
            reader.pages
        )

        if page_count < 1:
            logger.error(
                "PDF has no pages: %s",
                path,
            )
            return False

        logger.info(
            "%s: %s-page validation PASS",
            path.name,
            page_count,
        )

        return True

    except ImportError:

        logger.warning(
            "pypdf not installed; "
            "performing file-size validation only."
        )

        return True

    except Exception as exc:

        logger.error(
            "PDF validation failed for %s: %s",
            path,
            exc,
        )

        return False


# ============================================================
# BATCH GENERATION
# ============================================================

def run() -> None:
    """Generate reports for every broad sector."""

    logger.info(
        "Starting Day-34 sector report generation..."
    )

    sector_data = load_sector_data()

    ratios = load_ratio_data()

    latest_ratios = get_latest_company_ratios(
        ratios
    )

    styles = create_styles()

    sectors = (
        sector_data["broad_sector"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    sectors = sorted(
        sectors
    )

    logger.info(
        "Sectors detected: %s",
        len(sectors),
    )

    successful = 0
    failed = 0

    for index, sector in enumerate(
        sectors,
        start=1,
    ):

        logger.info(
            "[%s/%s] Generating %s",
            index,
            len(sectors),
            sector,
        )

        try:

            output = generate_sector_report(
                sector,
                sector_data,
                latest_ratios,
                styles,
            )

            if validate_pdf(output):

                successful += 1

            else:

                failed += 1

        except Exception as exc:

            failed += 1

            logger.exception(
                "Failed to generate sector %s: %s",
                sector,
                exc,
            )

    print()
    print("=" * 70)
    print("DAY 34 — SECTOR REPORT GENERATION")
    print("=" * 70)
    print(
        f"Sectors detected : {len(sectors)}"
    )
    print(
        f"Successful       : {successful}"
    )
    print(
        f"Failed           : {failed}"
    )
    print(
        f"Output           : {REPORT_DIR}"
    )
    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    """CLI entry point."""

    run()


if __name__ == "__main__":
    main()