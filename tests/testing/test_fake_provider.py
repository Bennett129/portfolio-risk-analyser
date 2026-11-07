import pandas as pd
import pytest

from riskanalyser.data.provider import PriceProvider
from riskanalyser.errors import UnknownTickerError
from riskanalyser.testing import FakePriceProvider, SyntheticMarket


def test_fake_provider_follows_the_interface(price_provider: FakePriceProvider) -> None:
    # The type hint makes mypy check FakePriceProvider against PriceProvider.
    provider: PriceProvider = price_provider
    assert provider is price_provider


def test_returns_requested_tickers_in_requested_order(
    price_provider: FakePriceProvider, market: SyntheticMarket
) -> None:
    result = price_provider.get_prices(["CCC", "AAA"])

    assert list(result.adjusted_close.columns) == ["CCC", "AAA"]
    pd.testing.assert_frame_equal(result.adjusted_close, market.prices[["CCC", "AAA"]])


def test_date_bounds_are_inclusive(price_provider: FakePriceProvider) -> None:
    result = price_provider.get_prices(["AAA"], start="2020-01-02", end="2020-01-07")

    assert result.adjusted_close.index[0] == pd.Timestamp("2020-01-02")
    assert result.adjusted_close.index[-1] == pd.Timestamp("2020-01-07")
    assert len(result.adjusted_close) == 4


def test_a_window_without_data_returns_empty_frames(price_provider: FakePriceProvider) -> None:
    result = price_provider.get_prices(["AAA"], start="1990-01-01", end="1990-12-31")

    assert result.adjusted_close.empty
    assert result.close.empty


def test_unknown_tickers_are_named_in_the_error(price_provider: FakePriceProvider) -> None:
    with pytest.raises(UnknownTickerError, match="ZZZ"):
        price_provider.get_prices(["AAA", "ZZZ"])


def test_close_defaults_to_adjusted_close(price_provider: FakePriceProvider) -> None:
    result = price_provider.get_prices(["AAA"])

    pd.testing.assert_frame_equal(result.close, result.adjusted_close)


def test_close_can_differ_from_adjusted_close() -> None:
    dates = pd.bdate_range("2024-01-01", periods=2)
    adjusted = pd.DataFrame({"AAA": [50.0, 51.0]}, index=dates)
    close = pd.DataFrame({"AAA": [100.0, 51.0]}, index=dates)

    result = FakePriceProvider(adjusted, close).get_prices(["AAA"])

    assert result.adjusted_close["AAA"].iloc[0] == 50.0
    assert result.close["AAA"].iloc[0] == 100.0


def test_mismatched_frames_are_rejected() -> None:
    dates = pd.bdate_range("2024-01-01", periods=2)
    adjusted = pd.DataFrame({"AAA": [1.0, 2.0]}, index=dates)
    close = pd.DataFrame({"BBB": [1.0, 2.0]}, index=dates)

    with pytest.raises(ValueError, match="same tickers"):
        FakePriceProvider(adjusted, close)


def test_callers_cannot_alter_the_stored_prices(price_provider: FakePriceProvider) -> None:
    returned = price_provider.get_prices(["AAA"]).adjusted_close
    original = returned.copy()
    returned.iloc[0, 0] = -1.0

    pd.testing.assert_frame_equal(price_provider.get_prices(["AAA"]).adjusted_close, original)
