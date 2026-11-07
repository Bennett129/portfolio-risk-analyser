import math
from collections import Counter
from dataclasses import dataclass

import pandas as pd

MIN_HOLDINGS = 2
MAX_HOLDINGS = 50
SUPPORTED_CURRENCIES = ("USD",)


@dataclass(frozen=True)
class Holding:
    ticker: str
    quantity: float

    def __post_init__(self) -> None:
        if not self.ticker.strip():
            raise ValueError("ticker cannot be blank")
        if not math.isfinite(self.quantity) or self.quantity <= 0:
            raise ValueError(f"quantity myst be positive, got {self.quantity}")


@dataclass(frozen=True)
class Portfolio:
    holdings: tuple[Holding, ...]

    def __post_init__(self) -> None:
        if len(self.holdings) > MAX_HOLDINGS:
            raise ValueError("only 50 holdings per Portfolio")
        if len(self.holdings) < MIN_HOLDINGS:
            raise ValueError("at least 2 holdings per Portfolio")
        tickers = Counter([Holding.ticker for Holding in self.holdings])
        if len(tickers) != len(self.holdings):
            duplicate = [ticker for ticker, count in tickers.items() if count > 1]

            raise ValueError(f"duplicate holdings in Portfolio, duplicates:{', '.join(duplicate)}")


@dataclass(frozen=True, eq=False)
class PriceHistory:
    """Daily prices with one row per date and one column per ticker.

    ``adjusted_close`` includes splits and dividends and is used for returns. ``close`` is the
    traded price and is used for market value.
    """

    adjusted_close: pd.DataFrame
    close: pd.DataFrame

    def __post_init__(self) -> None:
        for name, prices in (("adjusted_close", self.adjusted_close), ("close", self.close)):
            if not isinstance(prices.index, pd.DatetimeIndex):
                raise ValueError(f"{name} must be indexed by date")
            if not prices.index.is_unique:
                raise ValueError(f"{name} has duplicate dates")
            if not prices.index.is_monotonic_increasing:
                raise ValueError(f"{name} dates must be sorted from oldest to newest")
            if not prices.columns.is_unique:
                raise ValueError(f"{name} has duplicate tickers")
        if not self.adjusted_close.index.equals(self.close.index):
            raise ValueError("adjusted_close and close must have the same dates")
        if not self.adjusted_close.columns.equals(self.close.columns):
            raise ValueError("adjusted_close and close must have the same tickers")


@dataclass(frozen=True)
class AnalysisSettings:
    """User-adjustable settings, defaulting to the v1 values in the build plan."""

    lookback_years: int = 5
    confidence_levels: tuple[float, ...] = (0.95, 0.99)
    base_currency: str = "USD"

    def __post_init__(self) -> None:
        if self.lookback_years < 1:
            raise ValueError(f"lookback_years must be at least 1, got {self.lookback_years}")
        if not self.confidence_levels:
            raise ValueError("at least one confidence level is required")
        for level in self.confidence_levels:
            if not 0 < level < 1:
                raise ValueError(f"confidence levels must be between 0 and 1, got {level}")
        if self.base_currency not in SUPPORTED_CURRENCIES:
            supported = ", ".join(SUPPORTED_CURRENCIES)
            raise ValueError(
                f"base_currency {self.base_currency!r} is not supported; use one of: {supported}"
            )
