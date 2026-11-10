"""Price data from Yahoo Finance via the yfinance library."""

from collections.abc import Sequence

import pandas as pd
import yfinance as yf

from riskanalyser.errors import ProviderError, UnknownTickerError
from riskanalyser.models import PriceHistory


class YFinanceProvider:
    """Fetches daily prices from Yahoo Finance."""

    def get_prices(
        self,
        tickers: Sequence[str],
        start: str | None = None,
        end: str | None = None,
    ) -> PriceHistory:
        """Same contract as PriceProvider.get_prices."""
        names = list(tickers)
        raw = _download(names, start, end)  # 1. fetch
        adjusted = _extract(raw, "Adj Close", names)  # 2. split into two tables
        close = _extract(raw, "Close", names)
        _check_known(adjusted, names)  # 3. find unknown tickers
        return PriceHistory(adjusted, close)  # 4. validate and return


def _exclusive_end(end: str | None) -> str | None:
    """Convert our inclusive end date to yfinance's exclusive one."""
    if end is None:
        return None
    return (pd.Timestamp(end) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")


def _download(tickers: list[str], start: str | None, end: str | None) -> pd.DataFrame:
    """Call yfinance and turn its failures into ProviderError."""
    try:
        raw = yf.download(
            tickers=tickers,
            start=start,
            end=_exclusive_end(end),
            auto_adjust=False,
            progress=False,
        )
    except Exception as error:
        raise ProviderError("yfinance", str(error)) from error
    if not isinstance(raw, pd.DataFrame) or raw.empty:
        raise ProviderError("yfinance", "no data returned")
    return _remove_timezone(raw)


def _remove_timezone(raw: pd.DataFrame) -> pd.DataFrame:
    """Drop any timezone from the dates, keeping each trading day's date unchanged."""
    if isinstance(raw.index, pd.DatetimeIndex) and raw.index.tz is not None:
        return raw.tz_localize(None)
    return raw


def _extract(raw: pd.DataFrame, field: str, tickers: list[str]) -> pd.DataFrame:
    """Return one price field as a table with columns in the requested order."""
    try:
        prices = raw.xs(field, axis=1, level=0)
    except (KeyError, TypeError) as error:
        raise ProviderError("yfinance", f"unexpected layout for {field} prices") from error
    if not isinstance(prices, pd.DataFrame):
        raise ProviderError("yfinance", f"unexpected layout for {field} prices")
    return prices.reindex(columns=tickers)


def _check_known(prices: pd.DataFrame, tickers: list[str]) -> None:
    """Raise UnknownTickerError for tickers with no price data at all."""
    unknown = [ticker for ticker in tickers if prices[ticker].isna().all()]
    if unknown:
        raise UnknownTickerError(unknown)
