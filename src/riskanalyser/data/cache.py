"""A PriceProvider that keeps prices in local Parquet files.

It wraps another provider: prices come from the cache while they are fresh,
and from the wrapped provider when they are missing or stale.
"""

import warnings
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path

import pandas as pd

from riskanalyser.data.provider import PriceProvider
from riskanalyser.errors import ProviderError, StaleDataWarning
from riskanalyser.models import PriceHistory

DEFAULT_CACHE_DIR = Path("data/cache")


class CachedPriceProvider:
    """Caches each ticker's full price history in ``<cache_dir>/<TICKER>.parquet``."""

    def __init__(
        self,
        inner: PriceProvider,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        today: Callable[[], date] = date.today,
    ) -> None:
        self._inner = inner
        self._cache_dir = cache_dir
        self._today = today
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def get_prices(
        self,
        tickers: Sequence[str],
        start: str | None = None,
        end: str | None = None,
    ) -> PriceHistory:
        """Same contract as PriceProvider.get_prices.

        Warns:
            StaleDataWarning: If a refresh failed and older cached prices were used instead.
        """
        cached: dict[str, pd.DataFrame] = {}
        stale: list[str] = []
        to_fetch: list[str] = []
        for ticker in tickers:
            ticker_cache = _cache_path(self._cache_dir, ticker)
            try:
                if _is_fresh(ticker_cache, self._today()):
                    cached[ticker] = pd.read_parquet(ticker_cache)
                else:
                    to_fetch.append(ticker)
            except FileNotFoundError:
                to_fetch.append(ticker)

        if to_fetch:
            try:
                fetched = self._inner.get_prices(to_fetch)
            except ProviderError:
                for ticker in to_fetch:
                    path = _cache_path(self._cache_dir, ticker)
                    if not path.exists():  # no cached copy, so the failure can't be hidden
                        raise
                    cached[ticker] = pd.read_parquet(path)
                    stale.append(ticker)
            else:
                for ticker in to_fetch:
                    table = pd.DataFrame(
                        {
                            "adjusted_close": fetched.adjusted_close[ticker],
                            "close": fetched.close[ticker],
                        }
                    )
                    table.to_parquet(_cache_path(self._cache_dir, ticker))
                    cached[ticker] = table

        if stale:
            warnings.warn(
                f"using older cached prices for: {', '.join(stale)}",
                StaleDataWarning,
                stacklevel=2,
            )

        adjusted = pd.DataFrame({ticker: cached[ticker]["adjusted_close"] for ticker in tickers})
        close = pd.DataFrame({ticker: cached[ticker]["close"] for ticker in tickers})
        return PriceHistory(adjusted.loc[start:end], close.loc[start:end])


def _cache_path(cache_dir: Path, ticker: str) -> Path:
    """Where one ticker's prices are stored."""
    return cache_dir / f"{ticker}.parquet"


def _is_fresh(path: Path, today: date) -> bool:
    """True if the file was written today. Raises FileNotFoundError if it doesn't exist."""
    return date.fromtimestamp(path.stat().st_mtime) == today
