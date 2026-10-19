import numpy as np
import pandas as pd
import pytest

from analytics import calculate_correlation, calculate_metrics, normalize_tickers, simulate_dca


def sample_prices():
    dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-02-01", "2024-03-01"])
    return pd.DataFrame({"VOO": [100, 110, 105, 120], "QQQM": [50, 55, 52.5, 60]}, index=dates)


def test_normalize_tickers_deduplicates_and_uppercases():
    assert normalize_tickers(" voo, QQQM, voo, nvda ") == ["VOO", "QQQM", "NVDA"]


def test_normalize_tickers_rejects_empty_input():
    with pytest.raises(ValueError):
        normalize_tickers(" , ")


def test_metrics_cumulative_return_and_drawdown():
    metrics = calculate_metrics(sample_prices())
    assert metrics.loc["VOO", "Cumulative Return"] == pytest.approx(0.20)
    assert metrics.loc["VOO", "Maximum Drawdown"] == pytest.approx(105 / 110 - 1)


def test_correlation_of_proportional_series_is_one():
    corr = calculate_correlation(sample_prices())
    assert corr.loc["VOO", "QQQM"] == pytest.approx(1.0)


def test_dca_contribution_and_positive_value():
    prices = sample_prices()
    timeline, summary = simulate_dca(prices, monthly_contribution=100, years=1)
    assert timeline.iloc[-1]["Contributions"] == pytest.approx(300)
    assert timeline.iloc[-1]["Portfolio Value"] > 0
    assert summary["Allocation"].sum() == pytest.approx(1.0)


def test_dca_rejects_nonpositive_contribution():
    with pytest.raises(ValueError):
        simulate_dca(sample_prices(), monthly_contribution=0, years=1)
