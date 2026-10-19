# US Stock Investment Analysis

A Streamlit dashboard for exploring US-listed stocks and ETFs using historical market data.

## Features

- Historical price and cumulative-return charts
- Total-return-oriented historical metrics: cumulative return, CAGR, annualized volatility, and maximum drawdown
- Correlation matrix based on daily returns
- Long-term monthly DCA simulation for one or more tickers, with adjustable contribution, period, start date, and allocation weights
- CSV export for downloaded price data, metrics, and DCA results

## Supported examples

`VOO`, `QQQM`, `NVDA`, `AAPL`, `MSFT`, `GOOGL`, `BRK-B`, `SOXX`, `GLDM`, `TSLA`.

Yahoo Finance ticker conventions apply: for example, Berkshire Hathaway Class B is `BRK-B`.

## Install and run

Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

## Metric definitions

- **Daily return:** percentage change in adjusted closing price.
- **Cumulative return:** ending adjusted close / starting adjusted close − 1.
- **CAGR:** annualized growth rate over the observed date interval.
- **Annualized volatility:** standard deviation of daily returns × √252.
- **Maximum drawdown:** minimum of price / prior running peak − 1.
- **Correlation:** Pearson correlation between aligned daily returns.
- **DCA:** invests a fixed cash contribution on the first available trading day of each month. Fractional shares are allowed. Adjusted prices are used as a total-return proxy; this is not a broker-level execution ledger.

## Notes and limitations

- Data is provided by Yahoo Finance through `yfinance`; coverage, adjustments, and availability are not guaranteed.
- Historical performance does not predict future returns. Simulations do not model taxes, commissions, FX conversion, bid/ask spreads, slippage, or changes in contribution amount.
- Use consistent date ranges when comparing metrics. Recent periods can be incomplete.
- This project is for education and research, not personalized financial advice.

## Project structure

```
app.py                 Streamlit UI
analytics.py           Data retrieval and quantitative metrics
tests/test_analytics.py Unit tests for core metrics
requirements.txt       Python dependencies
```
