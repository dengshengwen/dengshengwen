"""Market data and portfolio analytics for the US Stock Investment Analysis app."""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
import yfinance as yf


TRADING_DAYS_PER_YEAR = 252


def normalize_tickers(tickers: Iterable[str]) -> list[str]:
    """Normalize a comma-separated or iterable ticker list, preserving order."""
    if isinstance(tickers, str):
        tickers = tickers.split(",")
    result: list[str] = []
    for ticker in tickers:
        value = str(ticker).strip().upper()
        if value and value not in result:
            result.append(value)
    if not result:
        raise ValueError("Please provide at least one ticker symbol.")
    return result


def download_adjusted_prices(
    tickers: Iterable[str], start: str | pd.Timestamp, end: str | pd.Timestamp
) -> pd.DataFrame:
    """Download auto-adjusted daily close prices from Yahoo Finance.

    yfinance's auto_adjust=True adjusts OHLC prices for corporate actions.
    Adjusted close is used as a practical total-return proxy.
    """
    symbols = normalize_tickers(tickers)
    data = yf.download(
        tickers=symbols,
        start=pd.Timestamp(start).strftime("%Y-%m-%d"),
        # yfinance's end parameter is exclusive; include the selected calendar end date.
        end=(pd.Timestamp(end) + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
        auto_adjust=True,
        progress=False,
        group_by="column",
        threads=True,
    )
    if data.empty:
        raise ValueError("No market data returned. Check the ticker symbols and date range.")

    if isinstance(data.columns, pd.MultiIndex):
        if "Close" in data.columns.get_level_values(0):
            prices = data["Close"].copy()
        elif "Close" in data.columns.get_level_values(-1):
            prices = data.xs("Close", axis=1, level=-1).copy()
        else:
            raise ValueError("The data provider did not return close prices.")
    else:
        if "Close" not in data.columns:
            raise ValueError("The data provider did not return close prices.")
        prices = data[["Close"]].copy()
        prices.columns = symbols[:1]

    if isinstance(prices, pd.Series):
        prices = prices.to_frame()
    prices.columns = [str(col).upper() for col in prices.columns]
    prices = prices.sort_index().apply(pd.to_numeric, errors="coerce")
    prices = prices.dropna(axis=1, how="all").ffill().dropna(how="all")
    if prices.empty:
        raise ValueError("No valid prices remain after cleaning the downloaded data.")
    return prices


def calculate_metrics(prices: pd.DataFrame) -> pd.DataFrame:
    """Calculate cumulative return, CAGR, annualized volatility, and max drawdown."""
    if prices.empty:
        raise ValueError("Price data is empty.")
    rows = []
    for ticker in prices.columns:
        series = prices[ticker].dropna().astype(float)
        if len(series) < 2 or series.iloc[0] <= 0:
            continue
        daily_returns = series.pct_change().dropna()
        elapsed_days = (series.index[-1] - series.index[0]).days
        years = elapsed_days / 365.25 if elapsed_days > 0 else np.nan
        cumulative_return = series.iloc[-1] / series.iloc[0] - 1
        cagr = (
            (series.iloc[-1] / series.iloc[0]) ** (1 / years) - 1
            if years and np.isfinite(years) and years > 0
            else np.nan
        )
        volatility = (
            daily_returns.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)
            if len(daily_returns) > 1
            else np.nan
        )
        drawdown = series / series.cummax() - 1
        rows.append(
            {
                "Ticker": ticker,
                "Start": series.index[0].date().isoformat(),
                "End": series.index[-1].date().isoformat(),
                "Observations": len(series),
                "Cumulative Return": cumulative_return,
                "CAGR": cagr,
                "Annualized Volatility": volatility,
                "Maximum Drawdown": drawdown.min(),
            }
        )
    return pd.DataFrame(rows).set_index("Ticker") if rows else pd.DataFrame()


def calculate_correlation(prices: pd.DataFrame) -> pd.DataFrame:
    """Calculate Pearson correlation from aligned daily returns."""
    returns = prices.sort_index().pct_change().dropna(how="all")
    return returns.corr(min_periods=2)


def simulate_dca(
    prices: pd.DataFrame,
    monthly_contribution: float = 1000.0,
    years: int = 20,
    weights: dict[str, float] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Simulate fixed monthly contributions on each month's first available trading day.

    Returns (portfolio_timeline, per_ticker_summary). When multiple tickers are selected,
    contribution weights are normalized to sum to 100%. Fractional shares are allowed.
    """
    if prices.empty:
        raise ValueError("Price data is empty.")
    if monthly_contribution <= 0:
        raise ValueError("Monthly contribution must be greater than zero.")
    if years < 1:
        raise ValueError("Simulation period must be at least one year.")

    clean = prices.sort_index().dropna(how="all").ffill()
    start_date = clean.index[-1] - pd.DateOffset(years=years)
    clean = clean.loc[clean.index >= start_date]
    if clean.empty or len(clean.index) < 2:
        raise ValueError("Not enough data for the selected simulation period.")

    tickers = list(clean.columns)
    if weights is None:
        allocation = {ticker: 1.0 / len(tickers) for ticker in tickers}
    else:
        allocation = {ticker: max(0.0, float(weights.get(ticker, 0.0))) for ticker in tickers}
        total_weight = sum(allocation.values())
        if total_weight <= 0:
            raise ValueError("At least one allocation weight must be positive.")
        allocation = {ticker: weight / total_weight for ticker, weight in allocation.items()}

    # Select the first trading observation available in each calendar month.
    month_keys = clean.index.to_period("M")
    contribution_dates = clean.loc[~month_keys.duplicated()].index
    shares = {ticker: 0.0 for ticker in tickers}
    invested = 0.0
    rows = []
    contributions = []

    for date in clean.index:
        if date in contribution_dates:
            for ticker in tickers:
                price = clean.at[date, ticker]
                if pd.notna(price) and price > 0:
                    cash = monthly_contribution * allocation[ticker]
                    shares[ticker] += cash / float(price)
                    invested += cash
            contributions.append((date, monthly_contribution))
        market_value = sum(
            shares[ticker] * float(clean.at[date, ticker])
            for ticker in tickers
            if pd.notna(clean.at[date, ticker])
        )
        rows.append(
            {
                "Date": date,
                "Contributions": invested,
                "Portfolio Value": market_value,
                "Profit / Loss": market_value - invested,
            }
        )

    timeline = pd.DataFrame(rows).set_index("Date")
    last_prices = clean.iloc[-1]
    summary_rows = []
    for ticker in tickers:
        ticker_invested = sum(
            amount * allocation[ticker]
            for _, amount in contributions
            if ticker in shares
        )
        market_value = shares[ticker] * float(last_prices[ticker])
        summary_rows.append(
            {
                "Ticker": ticker,
                "Allocation": allocation[ticker],
                "Contributed": ticker_invested,
                "Shares (fractional)": shares[ticker],
                "Ending Value": market_value,
                "Profit / Loss": market_value - ticker_invested,
                "Return on Contributions": market_value / ticker_invested - 1
                if ticker_invested > 0
                else np.nan,
            }
        )
    summary = pd.DataFrame(summary_rows).set_index("Ticker")
    return timeline, summary
