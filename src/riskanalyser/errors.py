from collections.abc import Sequence


class RiskAnalyserError(Exception):
    """Base class for all errors raised by riskanalyser."""


class UnknownTickerError(RiskAnalyserError):
    """The price provider doesn't recognise one or more tickers."""

    def __init__(self, tickers: Sequence[str]) -> None:
        self.tickers = tuple(tickers)
        super().__init__(f"unknown tickers: {', '.join(self.tickers)}")


class InsufficientHistoryError(RiskAnalyserError):
    """The ticker doesn't have the minimum required daily returns"""

    def __init__(self, ticker: str, available: int, required: int) -> None:
        self.ticker = ticker
        self.available = available
        self.required = required
        super().__init__(
            f"{ticker} has {available} daily returns; at least {required} are required"
        )


class MissingDataError(RiskAnalyserError):
    """One or more tickers have gaps in their price data."""

    def __init__(self, tickers: Sequence[str]) -> None:
        self.tickers = tuple(tickers)
        super().__init__(f"missing price data for: {', '.join(self.tickers)}")


class ProviderError(RiskAnalyserError):
    """The provider isn't providing the necessary input"""

    def __init__(self, provider: str, reason: str) -> None:
        self.provider = provider
        self.reason = reason
        super().__init__(f"{provider} failed: {reason}")


class StaleDataWarning(UserWarning):
    """Cached prices older than today were used because a refresh failed."""
