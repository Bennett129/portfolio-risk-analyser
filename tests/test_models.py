import pandas as pd
import pytest

from riskanalyser.models import (
    AnalysisSettings,
    Holding,
    Portfolio,
    PriceHistory,
)


def test_holding_rejects_blank_ticker() -> None:
    with pytest.raises(ValueError, match="ticker cannot be blank"):
        Holding("", 5)


def test_holding_rejects_negative_quantity() -> None:
    with pytest.raises(ValueError, match="quantity myst be positive"):
        Holding("AAPL", -5)


def make_holdings(count: int) -> tuple[Holding, ...]:
    """Create `count` holdings with unique tickers T0, T1, T2, ..."""
    return tuple(Holding(f"T{i}", 1) for i in range(count))


def test_portfolio_rejects_a_single_holding() -> None:
    holdings = (Holding("AAPL", 10),)

    with pytest.raises(ValueError, match="at least 2"):
        Portfolio(holdings)


def test_portfolio_accepts_two_holdings() -> None:
    holdings = (Holding("AAPL", 10), Holding("NVDA", 11))

    portfolio = Portfolio(holdings)

    assert portfolio.holdings == holdings


def test_portfolio_accepts_fifty_holdings() -> None:
    holdings = make_holdings(50)

    portfolio = Portfolio(holdings)

    assert len(portfolio.holdings) == 50


def test_portfolio_rejects_fifty_one_holdings() -> None:
    holdings = make_holdings(51)

    with pytest.raises(ValueError, match="only 50"):
        Portfolio(holdings)


def test_portfolio_rejects_duplicate_holdings() -> None:
    holdings = (Holding("AAPL", 10), Holding("AAPL", 11))

    with pytest.raises(ValueError, match="duplicate holdings"):
        Portfolio(holdings)


# --- PriceHistory ---


def make_prices(dates: list[str], tickers: list[str]) -> pd.DataFrame:
    """Create a price table with every price set to 100."""
    return pd.DataFrame(100.0, index=pd.DatetimeIndex(dates), columns=tickers)


DATES = ["2024-01-02", "2024-01-03", "2024-01-04"]


def test_price_history_accepts_matching_tables() -> None:
    adjusted_close = make_prices(DATES, ["AAPL", "NVDA"])
    close = make_prices(DATES, ["AAPL", "NVDA"])

    history = PriceHistory(adjusted_close, close)

    assert history.adjusted_close is adjusted_close
    assert history.close is close


def test_price_history_accepts_an_empty_date_range() -> None:
    empty = make_prices([], ["AAPL"])

    history = PriceHistory(empty, empty)

    assert history.adjusted_close.empty


def test_price_history_rejects_different_tickers() -> None:
    adjusted_close = make_prices(DATES, ["AAPL", "NVDA"])
    close = make_prices(DATES, ["AAPL", "MSFT"])

    with pytest.raises(ValueError, match="same tickers"):
        PriceHistory(adjusted_close, close)


def test_price_history_rejects_different_dates() -> None:
    adjusted_close = make_prices(DATES, ["AAPL"])
    close = make_prices(DATES[:2], ["AAPL"])

    with pytest.raises(ValueError, match="same dates"):
        PriceHistory(adjusted_close, close)


def test_price_history_rejects_dates_out_of_order() -> None:
    prices = make_prices(["2024-01-03", "2024-01-02"], ["AAPL"])

    with pytest.raises(ValueError, match="sorted"):
        PriceHistory(prices, prices)


def test_price_history_rejects_duplicate_dates() -> None:
    prices = make_prices(["2024-01-02", "2024-01-02"], ["AAPL"])

    with pytest.raises(ValueError, match="duplicate dates"):
        PriceHistory(prices, prices)


def test_price_history_rejects_duplicate_tickers() -> None:
    prices = make_prices(DATES, ["AAPL", "AAPL"])

    with pytest.raises(ValueError, match="duplicate tickers"):
        PriceHistory(prices, prices)


def test_price_history_rejects_an_index_that_is_not_dates() -> None:
    prices = pd.DataFrame({"AAPL": [100.0, 101.0]}, index=[0, 1])

    with pytest.raises(ValueError, match="indexed by date"):
        PriceHistory(prices, prices)


# --- AnalysisSettings ---


def test_analysis_settings_use_the_v1_defaults() -> None:
    settings = AnalysisSettings()

    assert settings.lookback_years == 5
    assert settings.confidence_levels == (0.95, 0.99)
    assert settings.base_currency == "USD"


def test_analysis_settings_accept_custom_values() -> None:
    settings = AnalysisSettings(lookback_years=3, confidence_levels=(0.9,))

    assert settings.lookback_years == 3
    assert settings.confidence_levels == (0.9,)


@pytest.mark.parametrize("lookback_years", [0, -1])
def test_analysis_settings_reject_a_lookback_below_one_year(lookback_years: int) -> None:
    with pytest.raises(ValueError, match="lookback_years"):
        AnalysisSettings(lookback_years=lookback_years)


@pytest.mark.parametrize("level", [0.0, 1.0, -0.5, 1.5, 95.0])
def test_analysis_settings_reject_confidence_levels_outside_zero_and_one(level: float) -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        AnalysisSettings(confidence_levels=(0.95, level))


def test_analysis_settings_require_a_confidence_level() -> None:
    with pytest.raises(ValueError, match="at least one confidence level"):
        AnalysisSettings(confidence_levels=())


def test_analysis_settings_reject_unsupported_currencies() -> None:
    with pytest.raises(ValueError, match="'EUR' is not supported"):
        AnalysisSettings(base_currency="EUR")
