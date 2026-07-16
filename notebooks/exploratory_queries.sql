-- 1. Total companies
SELECT COUNT(*) AS total_companies
FROM companies;

-- 2. Top 10 companies by latest market cap
SELECT company_id, market_cap_crore
FROM market_cap
ORDER BY year DESC, market_cap_crore DESC
LIMIT 10;

-- 3. Companies with highest ROE
SELECT company_id, year, return_on_equity_pct
FROM financial_ratios
ORDER BY return_on_equity_pct DESC
LIMIT 10;

-- 4. Companies with highest debt
SELECT company_id, year, total_debt_cr
FROM financial_ratios
ORDER BY total_debt_cr DESC
LIMIT 10;

-- 5. Companies with highest revenue
SELECT company_id, year, sales
FROM profit_loss
ORDER BY sales DESC
LIMIT 10;

-- 6. Latest stock prices
SELECT company_id, date, close_price
FROM stock_prices
ORDER BY date DESC
LIMIT 20;

-- 7. Companies with highest operating profit margin
SELECT company_id, year, operating_profit_margin_pct
FROM financial_ratios
ORDER BY operating_profit_margin_pct DESC
LIMIT 10;

-- 8. Companies by sector
SELECT broad_sector, COUNT(*) AS total_companies
FROM sectors
GROUP BY broad_sector
ORDER BY total_companies DESC;

-- 9. Companies with positive free cash flow
SELECT company_id, year, free_cash_flow_cr
FROM financial_ratios
WHERE free_cash_flow_cr > 0
ORDER BY free_cash_flow_cr DESC
LIMIT 10;

-- 10. Average ROE
SELECT AVG(return_on_equity_pct) AS avg_roe
FROM financial_ratios;