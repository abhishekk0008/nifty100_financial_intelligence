CREATE TABLE IF NOT EXISTS financial_ratios (
    id INTEGER PRIMARY KEY,
    company_id TEXT,
    year TEXT,

    net_profit_margin_pct REAL,
    operating_profit_margin_pct REAL,
    return_on_equity_pct REAL,
    debt_to_equity REAL,
    interest_coverage REAL,
    asset_turnover REAL,
    free_cash_flow_cr REAL,
    capex_cr REAL,
    earnings_per_share REAL,
    book_value_per_share REAL,
    dividend_payout_ratio_pct REAL,
    total_debt_cr REAL,
    cash_from_operations_cr REAL,

    FOREIGN KEY(company_id) REFERENCES companies(id)
);
CREATE TABLE IF NOT EXISTS companies (
    id TEXT NOT NULL PRIMARY KEY,

    company_logo TEXT,
    company_name TEXT,
    chart_link TEXT,
    about_company TEXT,
    website TEXT,
    nse_profile TEXT,
    bse_profile TEXT,

    face_value REAL,
    book_value REAL,
    roce_percentage REAL,
    roe_percentage REAL
);