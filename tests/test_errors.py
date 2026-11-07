import pytest

from riskanalyser.errors import (
    InsufficientHistoryError,
    MissingDataError,
    ProviderError,
    RiskAnalyserError,
    UnknownTickerError,
)


@pytest.mark.parametrize(
    "error_class",
    [UnknownTickerError, InsufficientHistoryError, MissingDataError, ProviderError],
)
def test_every_error_inherits_from_the_base_class(error_class: type[Exception]) -> None:
    assert issubclass(error_class, RiskAnalyserError)


def test_unknown_ticker_error_names_the_tickers() -> None:
    with pytest.raises(UnknownTickerError) as exc_info:
        raise UnknownTickerError(["ZZZ", "QQQ"])

    assert exc_info.value.tickers == ("ZZZ", "QQQ")
    assert "ZZZ, QQQ" in str(exc_info.value)


def test_insufficient_history_error_names_the_ticker() -> None:
    with pytest.raises(InsufficientHistoryError) as exc_info:
        raise InsufficientHistoryError("AAPL", 200, 256)

    assert exc_info.value.ticker == "AAPL"
    assert exc_info.value.available == 200
    assert exc_info.value.required == 256
    assert "AAPL has 200 daily returns; at least 256 are required" in str(exc_info.value)


def test_missing_data_error_names_the_tickers() -> None:
    with pytest.raises(MissingDataError) as exc_info:
        raise MissingDataError(["AAPL", "NVDA"])

    assert exc_info.value.tickers == ("AAPL", "NVDA")
    assert str(exc_info.value) == "missing price data for: AAPL, NVDA"


def test_provider_error_names_the_provider_and_reason() -> None:
    with pytest.raises(ProviderError) as exc_info:
        raise ProviderError("yfinance", "rate limited")

    assert exc_info.value.provider == "yfinance"
    assert exc_info.value.reason == "rate limited"
    assert "yfinance" in str(exc_info.value)
    assert "rate limited" in str(exc_info.value)


def test_errors_can_be_caught_with_the_base_class() -> None:
    with pytest.raises(RiskAnalyserError):
        raise UnknownTickerError(["ZZZ"])
