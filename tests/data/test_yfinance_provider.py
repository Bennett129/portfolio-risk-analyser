import pandas as pd
import pytest
import yfinance as yf

from riskanalyser.data.provider import PriceProvider
from riskanalyser.data.yfinance_provider import YFinanceProvider, _exclusive_end
from riskanalyser.errors import ProviderError, UnknownTickerError

DATES = pd.DatetimeIndex(["2024-01-02", "2024-01-03"], name="Date")


def make_raw(index: pd.DatetimeIndex = DATES) -> pd.DataFrame:
    """Build a table shaped like yf.download's output for AAPL and NVDA.

    Adjusted and unadjusted prices differ on purpose, so a test fails if they get swapped.
    """
    columns = pd.MultiIndex.from_product(
        [["Adj Close", "Close"], ["AAPL", "NVDA"]], names=["Price", "Ticker"]
    )
    return pd.DataFrame(
        [[184.0, 480.0, 185.0, 481.0], [183.0, 475.0, 184.0, 476.0]],
        index=index,
        columns=columns,
    )


def patch_download(monkeypatch: pytest.MonkeyPatch, result: object) -> list[dict[str, object]]:
    """Replace yf.download with a fake that returns ``result``.

    Returns a list that records the keyword arguments of each call.
    """
    calls: list[dict[str, object]] = []

    def fake_download(*args: object, **kwargs: object) -> object:
        calls.append(kwargs)
        return result

    monkeypatch.setattr(yf, "download", fake_download)
    return calls


def test_yfinance_provider_follows_the_interface() -> None:
    # The type hint makes mypy check YFinanceProvider against PriceProvider.
    provider: PriceProvider = YFinanceProvider()
    assert isinstance(provider, YFinanceProvider)


# --- Converting yfinance's output ---


def test_get_prices_returns_requested_tickers(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_download(monkeypatch, make_raw())

    prices = YFinanceProvider().get_prices(["NVDA", "AAPL"])

    assert list(prices.adjusted_close.columns) == ["NVDA", "AAPL"]
    assert list(prices.close.columns) == ["NVDA", "AAPL"]
    assert prices.adjusted_close["NVDA"].iloc[0] == 480.0
    assert prices.close["NVDA"].iloc[0] == 481.0


def test_unknown_ticker_raises_unknown_ticker_error(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_download(monkeypatch, make_raw())

    with pytest.raises(UnknownTickerError, match="unknown tickers: AAP"):
        YFinanceProvider().get_prices(["NVDA", "AAP"])


def test_timezones_are_removed_without_changing_dates(monkeypatch: pytest.MonkeyPatch) -> None:
    eastern = pd.DatetimeIndex(["2024-01-02", "2024-01-03"], tz="America/New_York")
    patch_download(monkeypatch, make_raw(index=eastern))

    prices = YFinanceProvider().get_prices(["AAPL", "NVDA"])

    index = prices.adjusted_close.index
    assert isinstance(index, pd.DatetimeIndex)
    assert index.tz is None
    assert list(index) == [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03")]


# --- Turning failures into ProviderError ---


@pytest.mark.parametrize("result", [None, pd.DataFrame()])
def test_missing_result_raises_provider_error(
    monkeypatch: pytest.MonkeyPatch, result: pd.DataFrame | None
) -> None:
    patch_download(monkeypatch, result)

    with pytest.raises(ProviderError, match="no data returned"):
        YFinanceProvider().get_prices(["AAPL", "NVDA"])


@pytest.mark.parametrize(
    "raw",
    [
        # Two levels of headings, but no "Adj Close", as with auto_adjust=True
        pd.DataFrame(
            [[185.0, 481.0]],
            index=DATES[:1],
            columns=pd.MultiIndex.from_product([["Close"], ["AAPL", "NVDA"]]),
        ),
        # One level of headings, as with multi_level_index=False
        pd.DataFrame({"Adj Close": [184.0], "Close": [185.0]}, index=DATES[:1]),
    ],
    ids=["no-adj-close", "one-level-headings"],
)
def test_unexpected_layout_raises_provider_error(
    monkeypatch: pytest.MonkeyPatch, raw: pd.DataFrame
) -> None:
    patch_download(monkeypatch, raw)

    with pytest.raises(ProviderError, match="unexpected layout"):
        YFinanceProvider().get_prices(["AAPL", "NVDA"])


def test_download_exception_becomes_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing_download(*args: object, **kwargs: object) -> pd.DataFrame:
        raise ConnectionError("network down")

    monkeypatch.setattr(yf, "download", failing_download)

    with pytest.raises(ProviderError, match="network down") as exc_info:
        YFinanceProvider().get_prices(["AAPL", "NVDA"])

    assert isinstance(exc_info.value.__cause__, ConnectionError)


# --- What gets sent to yfinance ---


def test_end_date_is_made_exclusive_for_yfinance(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = patch_download(monkeypatch, make_raw())

    YFinanceProvider().get_prices(["AAPL", "NVDA"], start="2024-01-02", end="2024-01-05")

    assert calls[0]["start"] == "2024-01-02"
    assert calls[0]["end"] == "2024-01-06"


def test_no_end_date_is_passed_on_as_none(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = patch_download(monkeypatch, make_raw())

    YFinanceProvider().get_prices(["AAPL", "NVDA"])

    assert calls[0]["end"] is None


def test_unadjusted_prices_are_requested(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = patch_download(monkeypatch, make_raw())

    YFinanceProvider().get_prices(["AAPL", "NVDA"])

    # Without auto_adjust=False, yfinance drops the unadjusted Close prices.
    assert calls[0]["auto_adjust"] is False
    assert calls[0]["tickers"] == ["AAPL", "NVDA"]


# --- _exclusive_end ---


def test_exclusive_end_adds_one_day() -> None:
    assert _exclusive_end("2024-01-05") == "2024-01-06"


def test_exclusive_end_rolls_over_the_year() -> None:
    assert _exclusive_end("2024-12-31") == "2025-01-01"


def test_exclusive_end_keeps_none() -> None:
    assert _exclusive_end(None) is None
