"""An in-memory price provider, so tests never need the network."""

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class PriceData:
    """Prices indexed by date, with one column per ticker.

    ``adjusted_close`` includes splits and dividends and is used for returns. ``close`` is the
    traded price and is used for market value.
    """

    adjusted_close: pd.DataFrame
    close: pd.DataFrame


class FakePriceProvider:
    """Serves prices from supplied data frames.

    If ``close`` is omitted it equals ``adjusted_close``, meaning no splits or dividends. Supply
    both to test how corporate actions are handled.
    """

    def __init__(self, adjusted_close: pd.DataFrame, close: pd.DataFrame | None = None) -> None:
        close = adjusted_close if close is None else close
        if not adjusted_close.index.equals(close.index) or not adjusted_close.columns.equals(
            close.columns
        ):
            raise ValueError("adjusted_close and close must have matching dates and tickers")
        self._adjusted_close = adjusted_close
        self._close = close

    def get_prices(
        self,
        tickers: Sequence[str],
        start: str | None = None,
        end: str | None = None,
    ) -> PriceData:
        """Return copies of the prices for ``tickers`` between two inclusive dates.

        Raises:
            KeyError: If any ticker is unknown.
        """
        names = list(tickers)
        unknown = [name for name in names if name not in self._adjusted_close.columns]
        if unknown:
            raise KeyError(f"unknown tickers: {unknown}")

        dates = self._adjusted_close.index
        mask = pd.Series(True, index=dates)
        if start is not None:
            mask &= dates >= pd.Timestamp(start)
        if end is not None:
            mask &= dates <= pd.Timestamp(end)

        return PriceData(
            adjusted_close=self._adjusted_close.loc[mask, names].copy(),
            close=self._close.loc[mask, names].copy(),
        )
