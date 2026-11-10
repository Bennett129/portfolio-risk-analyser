"""An in-memory price provider, so tests never need the network."""

from collections.abc import Sequence

import pandas as pd

from riskanalyser.errors import UnknownTickerError
from riskanalyser.models import PriceHistory


class FakePriceProvider:
    """Serves prices from supplied data frames.

    If ``close`` is omitted it equals ``adjusted_close``, meaning no splits or dividends. Supply
    both to test how corporate actions are handled.
    """

    def __init__(self, adjusted_close: pd.DataFrame, close: pd.DataFrame | None = None) -> None:
        self._prices = PriceHistory(adjusted_close, adjusted_close if close is None else close)

    def get_prices(
        self,
        tickers: Sequence[str],
        start: str | None = None,
        end: str | None = None,
    ) -> PriceHistory:
        """Return copies of the prices for ``tickers`` between two inclusive dates.

        Raises:
            UnknownTickerError: If any ticker is unknown.
        """
        names = list(tickers)
        unknown = [name for name in names if name not in self._prices.adjusted_close.columns]
        if unknown:
            raise UnknownTickerError(unknown)

        dates = self._prices.adjusted_close.index
        mask = pd.Series(True, index=dates)
        if start is not None:
            mask &= dates >= pd.Timestamp(start)
        if end is not None:
            mask &= dates <= pd.Timestamp(end)

        return PriceHistory(
            self._prices.adjusted_close.loc[mask, names].copy(),
            self._prices.close.loc[mask, names].copy(),
        )
