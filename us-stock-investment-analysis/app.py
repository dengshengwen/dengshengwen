"""Interactive dashboard for US stock and ETF analysis."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from analytics import (
    calculate_correlation,
    calculate_metrics,
    download_adjusted_prices,
    normalize_tickers,
    simulate_dca,
)

st.set_page_config(page_title="US Stock Investment Analysis", page_icon="📈", layout="wide")
st.title("📈 US Stock Investment Analysis")
st.caption("历史收益 · 最大回撤 · 波动率 · 相关性 · 长期定投模拟")

with st.sidebar:
    st.header("分析参数")
    ticker_input = st.text_input("标的代码（逗号分隔）", "VOO, QQQM, NVDA")
    end_date = st.date_input("数据截止日期", value=date.today())
    start_date = st.date_input("历史数据开始日期", value=end_date - timedelta(days=365 * 10))
    st.caption("示例：VOO、QQQM、NVDA、AAPL、MSFT、GOOGL、BRK-B、SOXX")
    st.divider()
    st.subheader("定投设置")
    monthly_contribution = st.number_input("每月投入（USD）", min_value=10.0, max_value=1_000_000.0, value=1000.0, step=100.0)
    dca_years = st.slider("定投年数", min_value=1, max_value=30, value=10)
    st.caption("多标的默认等权分配；下方可自定义权重。")

if start_date >= end_date:
    st.error("开始日期必须早于截止日期。")
    st.stop()

try:
    tickers = normalize_tickers(ticker_input)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

@st.cache_data(ttl=3600, show_spinner=False)
def get_prices(symbols: tuple[str, ...], start: date, end: date) -> pd.DataFrame:
    return download_adjusted_prices(symbols, start, end)

try:
    with st.spinner("正在获取 Yahoo Finance 历史行情…"):
        prices = get_prices(tuple(tickers), start_date, end_date)
except Exception as exc:
    st.error(f"行情获取失败：{exc}")
    st.info("请检查网络、代码和日期范围；Yahoo Finance 数据服务可能暂时不可用。")
    st.stop()

if prices.empty:
    st.warning("当前条件没有可用数据。")
    st.stop()

available_tickers = list(prices.columns)
if len(available_tickers) < len(tickers):
    missing = sorted(set(tickers) - set(available_tickers))
    st.warning(f"以下代码没有返回有效行情：{', '.join(missing)}")

metrics = calculate_metrics(prices)
tab1, tab2, tab3, tab4 = st.tabs(["📊 历史表现", "🔗 相关性", "💵 长期定投", "📥 数据导出"])

with tab1:
    st.subheader("历史调整收盘价")
    normalized = prices / prices.iloc[0] * 100
    chart_data = normalized.reset_index(names="Date").melt(id_vars="Date", var_name="Ticker", value_name="Growth of 100")
    fig = px.line(chart_data, x="Date", y="Growth of 100", color="Ticker", title="起始值归一化为 100")
    fig.update_layout(legend_title_text="标的", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("关键风险与收益指标")
    display_metrics = metrics.copy()
    for col in ["Cumulative Return", "CAGR", "Annualized Volatility", "Maximum Drawdown"]:
        if col in display_metrics:
            display_metrics[col] = display_metrics[col].map(lambda x: f"{x:.2%}" if pd.notna(x) else "—")
    st.dataframe(display_metrics, use_container_width=True)
    st.caption("波动率按日收益标准差 × √252 年化；最大回撤基于调整收盘价的历史峰值。")

    returns = prices.pct_change()
    cum_returns = (1 + returns.fillna(0)).cumprod()
    drawdowns = cum_returns / cum_returns.cummax() - 1
    dd_data = drawdowns.reset_index(names="Date").melt(id_vars="Date", var_name="Ticker", value_name="Drawdown")
    dd_fig = px.line(dd_data, x="Date", y="Drawdown", color="Ticker", title="历史回撤曲线")
    dd_fig.update_yaxes(tickformat=".0%")
    dd_fig.update_layout(hovermode="x unified")
    st.plotly_chart(dd_fig, use_container_width=True)

with tab2:
    st.subheader("日收益率相关性矩阵")
    corr = calculate_correlation(prices)
    corr_fig = px.imshow(corr, text_auto=".2f", zmin=-1, zmax=1, color_continuous_scale="RdBu_r", aspect="auto")
    st.plotly_chart(corr_fig, use_container_width=True)
    st.dataframe(corr.style.format("{:.3f}"), use_container_width=True)
    st.caption("相关性反映历史线性共同波动，不代表因果关系；结果会随观察区间变化。")

with tab3:
    st.subheader("长期定投模拟")
    max_available_years = max(1, min(30, int((prices.index[-1] - prices.index[0]).days / 365.25)))
    effective_years = min(dca_years, max_available_years)
    if effective_years != dca_years:
        st.info(f"当前数据不足 {dca_years} 年，模拟年数已调整为 {effective_years} 年。")

    st.write("设置各标的投入权重（系统会自动归一化为 100%）。")
    weight_cols = st.columns(min(3, len(available_tickers)))
    weights = {}
    for i, ticker in enumerate(available_tickers):
        with weight_cols[i % len(weight_cols)]:
            weights[ticker] = st.number_input(
                f"{ticker} 权重", min_value=0.0, max_value=100.0,
                value=100.0 / len(available_tickers), step=5.0, key=f"weight_{ticker}"
            )
    try:
        timeline, dca_summary = simulate_dca(
            prices, monthly_contribution=monthly_contribution,
            years=effective_years, weights=weights
        )
        last = timeline.iloc[-1]
        c1, c2, c3 = st.columns(3)
        c1.metric("累计投入", f"${last['Contributions']:,.0f}")
        c2.metric("期末市值", f"${last['Portfolio Value']:,.0f}")
        c3.metric("盈亏", f"${last['Profit / Loss']:,.0f}", f"{last['Profit / Loss'] / last['Contributions']:.2%}" if last['Contributions'] else "—")

        timeline_data = timeline.reset_index().melt(id_vars="Date", value_vars=["Contributions", "Portfolio Value"], var_name="Series", value_name="USD")
        timeline_fig = px.line(timeline_data, x="Date", y="USD", color="Series", title="累计投入与组合市值")
        st.plotly_chart(timeline_fig, use_container_width=True)
        summary_view = dca_summary.copy()
        for col in ["Allocation", "Return on Contributions"]:
            summary_view[col] = summary_view[col].map(lambda x: f"{x:.2%}" if pd.notna(x) else "—")
        for col in ["Contributed", "Ending Value", "Profit / Loss"]:
            summary_view[col] = summary_view[col].map(lambda x: f"${x:,.2f}")
        summary_view["Shares (fractional)"] = summary_view["Shares (fractional)"].map(lambda x: f"{x:,.6f}")
        st.dataframe(summary_view, use_container_width=True)
        st.caption("定投在每月首个可用交易日执行，允许碎股；调整价格用于近似总回报，不等同于券商真实成交记录。")
    except ValueError as exc:
        st.error(str(exc))

with tab4:
    st.subheader("下载结果")
    st.download_button("下载历史价格 CSV", prices.to_csv().encode("utf-8-sig"), "historical_prices.csv", "text/csv")
    st.download_button("下载指标 CSV", metrics.to_csv().encode("utf-8-sig"), "historical_metrics.csv", "text/csv")
    st.download_button("下载相关性 CSV", calculate_correlation(prices).to_csv().encode("utf-8-sig"), "correlation_matrix.csv", "text/csv")

st.divider()
st.caption("免责声明：本工具仅用于研究与教育，不构成投资建议。历史收益不代表未来表现。数据源为 Yahoo Finance，数据完整性与可用性不作保证。")
