PRAGMA foreign_keys = ON;

-- =====================================================
-- Companies
-- =====================================================

CREATE TABLE IF NOT EXISTS companies (
    id TEXT PRIMARY KEY,
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

-- =====================================================
-- Profit & Loss
-- =====================================================

CREATE TABLE IF NOT EXISTS profit_loss (
    id INTEGER PRIMARY KEY,
    company_id TEXT,
    year TEXT,
    sales REAL,
    expenses REAL,
    operating_profit REAL,
    opm_percentage REAL,
    other_income REAL,
    interest REAL,
    depreciation REAL,
    profit_before_tax REAL,
    tax_percentage REAL,
    net_profit REAL,
    eps REAL,
    dividend_payout REAL
);

-- =====================================================
-- Balance Sheet
-- =====================================================

CREATE TABLE IF NOT EXISTS balance_sheet (
    id INTEGER PRIMARY KEY,
    company_id TEXT,
    year TEXT,
    equity_capital REAL,
    reserves REAL,
    borrowings REAL,
    other_liabilities REAL,
    total_liabilities REAL,
    fixed_assets REAL,
    cwip REAL,
    investments REAL,
    other_asset REAL,
    total_assets REAL
);

-- =====================================================
-- Cash Flow
-- =====================================================

CREATE TABLE IF NOT EXISTS cash_flow (
    id INTEGER PRIMARY KEY,
    company_id TEXT,
    year TEXT,
    operating_activity REAL,
    investing_activity REAL,
    financing_activity REAL,
    net_cash_flow REAL
);

-- =====================================================
-- Analysis
-- =====================================================

CREATE TABLE IF NOT EXISTS analysis (
    id INTEGER PRIMARY KEY,
    company_id TEXT,
    compounded_sales_growth TEXT,
    compounded_profit_growth TEXT,
    stock_price_cagr TEXT,
    roe TEXT
);

-- =====================================================
-- Documents
-- =====================================================

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    company_id TEXT,
    year TEXT,
    annual_report TEXT
);

-- =====================================================
-- Pros & Cons
-- =====================================================

CREATE TABLE IF NOT EXISTS pros_cons (
    id INTEGER PRIMARY KEY,
    company_id TEXT,
    pros TEXT,
    cons TEXT
);

-- =====================================================
-- Derived Tables
-- =====================================================

CREATE TABLE IF NOT EXISTS sectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sector_name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS stock_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT,
    trade_date TEXT,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER
);

CREATE TABLE IF NOT EXISTS financial_ratios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT,
    year TEXT,
    pe REAL,
    pb REAL,
    roe REAL,
    roce REAL,
    debt_to_equity REAL
);