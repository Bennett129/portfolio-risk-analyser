"""Tests for CachedPriceProvider.

``tmp_path`` is a built-in pytest fixture: an empty folder that is new for each test.
"""

import os
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from riskanalyser.data.cache import CachedPriceProvider
from riskanalyser.data.provider import PriceProvider
from riskanalyser.errors import ProviderError, StaleDataWarning, UnknownTickerError
from riskanalyser.models import PriceHistory
from riskanalyser.testing import FakePriceProvider

TODAY = date(2024, 6, 3)
YESTERDAY = TODAY - timedelta(days=1)


class RecordingProvider:
    """Passes calls on to another provider and records which tickers were requested."""

    def __init__(self, inner: PriceProvider) -> None:
        self.inner = inner
        self.calls: list[list[str]] = []

    def get_prices(
        self, tickers: Sequence[str], start: str | None = None, end: str | None = None
    ) -> PriceHistory:
        self.calls.append(list(tickers))
        return self.inner.get_prices(tickers, start, end)


class FailingProvider:
    """Always fails, like yfinance with no network."""

    def get_prices(
        self, tickers: Sequence[str], start: str | None = None, end: str | None = None
    ) -> PriceHistory:
        raise ProviderError("fake", "network down")


@pytest.fixture
def recorder(price_provider: FakePriceProvider) -> RecordingProvider:
    return RecordingProvider(price_provider)


def make_cache(tmp_path: Path, inner: PriceProvider) -> CachedPriceProvider:
    """A cache in a new folder, where "today" is always TODAY."""
    return CachedPriceProvider(inner, cache_dir=tmp_path / "cache", today=lambda: TODAY)


def set_written_on(tmp_path: Path, day: date) -> None:
    """Change every cached file's modified time to midday on ``day``."""
    timestamp = datetime(day.year, day.month, day.day, 12).timestamp()
    for path in (tmp_path / "cache").glob("*.parquet"):
        os.utime(path, (timestamp, timestamp))


def assert_same_prices(actual: PriceHistory, expected: PriceHistory) -> None:
    # Parquet doesn't store the index frequency, and the column headings' name isn't kept.
    for got, want in [
        (actual.adjusted_close, expected.adjusted_close),
        (actual.close, expected.close),
    ]:
        pd.testing.assert_frame_equal(got, want, check_freq=False, check_names=False)


def test_cached_provider_follows_the_interface(tmp_path: Path) -> None:
    # The type hint makes mypy check CachedPriceProvider against PriceProvider.
    provider: PriceProvider = make_cache(tmp_path, FailingProvider())
    assert isinstance(provider, CachedPriceProvider)


def test_cache_folder_is_created(tmp_path: Path) -> None:
    make_cache(tmp_path, FailingProvider())

    assert (tmp_path / "cache").is_dir()


# --- Fresh cache ---


def test_first_call_fetches_from_the_inner_provider(
    tmp_path: Path, recorder: RecordingProvider, price_provider: FakePriceProvider
) -> None:
    prices = make_cache(tmp_path, recorder).get_prices(["AAA", "BBB"])

    assert recorder.calls == [["AAA", "BBB"]]
    assert_same_prices(prices, price_provider.get_prices(["AAA", "BBB"]))


def test_first_call_writes_one_file_per_ticker(tmp_path: Path, recorder: RecordingProvider) -> None:
    make_cache(tmp_path, recorder).get_prices(["AAA", "BBB"])

    files = sorted(path.name for path in (tmp_path / "cache").iterdir())
    assert files == ["AAA.parquet", "BBB.parquet"]


def test_second_call_on_the_same_day_uses_the_cache(
    tmp_path: Path, recorder: RecordingProvider
) -> None:
    cache = make_cache(tmp_path, recorder)
    first = cache.get_prices(["AAA", "BBB"])
    set_written_on(tmp_path, TODAY)

    second = cache.get_prices(["AAA", "BBB"])

    assert recorder.calls == [["AAA", "BBB"]]
    assert_same_prices(second, first)


def test_only_uncached_tickers_are_fetched(tmp_path: Path, recorder: RecordingProvider) -> None:
    cache = make_cache(tmp_path, recorder)
    cache.get_prices(["AAA"])
    set_written_on(tmp_path, TODAY)

    cache.get_prices(["AAA", "BBB"])

    assert recorder.calls == [["AAA"], ["BBB"]]


def test_columns_follow_the_requested_order(tmp_path: Path, recorder: RecordingProvider) -> None:
    cache = make_cache(tmp_path, recorder)
    cache.get_prices(["BBB"])
    set_written_on(tmp_path, TODAY)

    # BBB comes from the cache, CCC and AAA from the inner provider.
    prices = cache.get_prices(["CCC", "BBB", "AAA"])

    assert list(prices.adjusted_close.columns) == ["CCC", "BBB", "AAA"]
    assert list(prices.close.columns) == ["CCC", "BBB", "AAA"]


# --- Stale cache ---


def test_file_from_yesterday_is_fetched_again(tmp_path: Path, recorder: RecordingProvider) -> None:
    cache = make_cache(tmp_path, recorder)
    cache.get_prices(["AAA", "BBB"])
    set_written_on(tmp_path, YESTERDAY)

    cache.get_prices(["AAA", "BBB"])

    assert recorder.calls == [["AAA", "BBB"], ["AAA", "BBB"]]


def test_stale_file_is_used_and_reported_when_the_refresh_fails(
    tmp_path: Path, recorder: RecordingProvider
) -> None:
    original = make_cache(tmp_path, recorder).get_prices(["AAA", "BBB"])
    set_written_on(tmp_path, YESTERDAY)

    with pytest.warns(StaleDataWarning, match="AAA, BBB"):
        prices = make_cache(tmp_path, FailingProvider()).get_prices(["AAA", "BBB"])

    assert_same_prices(prices, original)


def test_refresh_failure_without_a_cached_copy_raises(tmp_path: Path) -> None:
    with pytest.raises(ProviderError, match="network down"):
        make_cache(tmp_path, FailingProvider()).get_prices(["AAA"])


def test_refresh_failure_raises_if_any_ticker_has_no_cached_copy(
    tmp_path: Path, recorder: RecordingProvider
) -> None:
    make_cache(tmp_path, recorder).get_prices(["AAA"])
    set_written_on(tmp_path, YESTERDAY)

    with pytest.raises(ProviderError, match="network down"):
        make_cache(tmp_path, FailingProvider()).get_prices(["AAA", "BBB"])


# --- Other errors and results ---


def test_unknown_ticker_error_is_not_hidden(tmp_path: Path, recorder: RecordingProvider) -> None:
    cache = make_cache(tmp_path, recorder)

    with pytest.raises(UnknownTickerError):
        cache.get_prices(["AAA", "XYZ"])

    assert list((tmp_path / "cache").iterdir()) == []


@pytest.mark.parametrize("from_cache", [False, True], ids=["fetched", "cached"])
def test_start_and_end_match_the_inner_provider(
    tmp_path: Path,
    recorder: RecordingProvider,
    price_provider: FakePriceProvider,
    from_cache: bool,
) -> None:
    cache = make_cache(tmp_path, recorder)
    if from_cache:
        cache.get_prices(["AAA", "BBB"])
        set_written_on(tmp_path, TODAY)

    prices = cache.get_prices(["AAA", "BBB"], start="2021-03-01", end="2021-06-30")

    expected = price_provider.get_prices(["AAA", "BBB"], start="2021-03-01", end="2021-06-30")
    assert_same_prices(prices, expected)
    assert recorder.calls == [["AAA", "BBB"]]
