# Nifty 100 Financial Intelligence Platform

## How to Run

1. Create/activate virtual environment
2. Install dependencies
3. Run the dashboard:

streamlit run src/dashboard/app.py

## Dashboard Screens

### 1. Home
Overview of the Nifty 100 financial intelligence dashboard.

![Home Dashboard](screenshots/01_home.png)

### 2. Company Profile
Displays detailed financial information and key metrics for a selected company.

![Company Profile](screenshots/02_profile.png)

### 3. Screener
Allows filtering and comparison of companies using financial metrics.

![Screener](screenshots/03_screener.png)

### 4. Peer Analysis
Compares companies with their relevant peer groups.

![Peer Analysis](screenshots/04_peers.png)

### 5. Financial Trends
Visualizes historical financial metrics and trends.

![Financial Trends](screenshots/05_trends.png)

### 6. Sector Analysis
Provides sector-level financial and performance comparisons.

![Sector Analysis](screenshots/06_sectors.png)

### 7. Market Capitalization
Shows latest market capitalization across Nifty 100 companies.

![Market Capitalization](screenshots/07_capital.png)

### 8. Company Reports
Displays growth analysis, pros and cons, and company-level reports.

![Company Reports](screenshots/08_reports.png)

## Key Outputs

- output/valuation_summary.xlsx
- output/valuation_flags.csv

## Valuation Module

The valuation module calculates:
- P/E
- P/B
- EV/EBITDA
- FCF Yield
- 5-year medians
- Sector medians
- Valuation flags

Flags:
- Discount
- Neutral
- Caution