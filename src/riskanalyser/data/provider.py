from collections.abc import Sequence
from typing import Protocol

from riskanalyser.models import PriceHistory


class PriceProvider(Protocol):
    """A source of daily price history for a set of tickers."""

    def get_prices(
        self,
        tickers: Sequence[str],
        start: str | None = None,
        end: str | None = None,
    ) -> PriceHistory:
        """Return prices for ``tickers`` between ``start`` and ``end``, inclusive.

        Columns appear in the same order as ``tickers``. ``None`` for ``start`` or
        ``end`` means no limit in that direction.

        Raises:
            UnknownTickerError: If the provider doesn't recognise any of the tickers.
            ProviderError: If fetching the prices fails.
        """
        ...
