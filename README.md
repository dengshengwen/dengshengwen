# Projects

## US Stock Investment Analysis

A Python dashboard for historical performance, maximum drawdown, annualized volatility, correlation analysis, and long-term dollar-cost averaging (DCA) simulations for US stocks and ETFs.

**Project directory:** [us-stock-investment-analysis](./us-stock-investment-analysis/README.md)

### Run locally

```bash
cd us-stock-investment-analysis
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Market data is fetched from Yahoo Finance via `yfinance`. This is an educational research tool, not investment advice.
