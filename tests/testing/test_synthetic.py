from typing import Any

import numpy as np
import pandas as pd
import pytest

from riskanalyser.testing import SyntheticMarket, generate_market
from riskanalyser.testing.synthetic import TRADING_DAYS_PER_YEAR

TWO_ASSET_CORRELATION = [[1.0, 0.5], [0.5, 1.0]]


def generate_two_assets(**overrides: Any) -> SyntheticMarket:
    arguments: dict[str, Any] = {
        "tickers": ["AAA", "BBB"],
        "annual_means": [0.08, 0.03],
        "annual_vols": [0.2, 0.1],
        "correlation": TWO_ASSET_CORRELATION,
        "n_days": 500,
        "seed": 1,
    }
    return generate_market(**(arguments | overrides))


def test_matched_moments_equal_the_parameters(market: SyntheticMarket) -> None:
    returns = market.log_returns

    np.testing.assert_allclose(returns.mean() * TRADING_DAYS_PER_YEAR, market.annual_means)
    np.testing.assert_allclose(
        returns.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR), market.annual_vols
    )
    np.testing.assert_allclose(returns.corr(), market.correlation)


def test_matched_moments_support_a_single_asset() -> None:
    result = generate_market(["AAA"], [0.1], [0.2], [[1.0]], n_days=100, match_moments=True)

    annual_vol = result.log_returns["AAA"].std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)
    assert annual_vol == pytest.approx(0.2)


def test_random_samples_are_close_to_the_parameters() -> None:
    years = 200
    result = generate_two_assets(n_days=TRADING_DAYS_PER_YEAR * years)
    returns = result.log_returns

    # The annualised sample mean has a standard error of vol / sqrt(years).
    mean_error = (returns.mean() * TRADING_DAYS_PER_YEAR - result.annual_means).abs()
    assert (mean_error < 4 * result.annual_vols / np.sqrt(years)).all()
    np.testing.assert_allclose(
        returns.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR), result.annual_vols, rtol=0.02
    )
    assert returns.corr().loc["AAA", "BBB"] == pytest.approx(0.5, abs=0.02)


def test_the_same_seed_reproduces_the_data() -> None:
    pd.testing.assert_frame_equal(generate_two_assets().prices, generate_two_assets().prices)


def test_different_seeds_produce_different_data() -> None:
    assert not generate_two_assets(seed=1).prices.equals(generate_two_assets(seed=2).prices)


def test_prices_are_consistent_with_returns() -> None:
    result = generate_two_assets(initial_price=50.0)

    assert (result.prices.iloc[0] == 50.0).all()
    assert (result.prices > 0).all(axis=None)
    np.testing.assert_allclose(
        np.diff(np.log(result.prices.to_numpy()), axis=0), result.log_returns.to_numpy()
    )


def test_dates_are_business_days_with_an_opening_price() -> None:
    result = generate_two_assets(n_days=10, start="2024-01-01")

    assert len(result.prices) == 11
    assert len(result.log_returns) == 10
    assert result.prices.index[0] == pd.Timestamp("2024-01-01")
    assert (pd.DatetimeIndex(result.prices.index).day_of_week < 5).all()


def test_zero_volatility_gives_deterministic_growth() -> None:
    result = generate_two_assets(annual_vols=[0.0, 0.0], annual_means=[0.1, 0.0])

    expected = 100.0 * np.exp(0.1 * 500 / TRADING_DAYS_PER_YEAR)
    assert result.prices["AAA"].iloc[-1] == pytest.approx(expected)
    assert result.prices["BBB"].iloc[-1] == pytest.approx(100.0)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"tickers": []}, "at least one ticker"),
        ({"tickers": ["AAA", "AAA"]}, "unique"),
        ({"annual_means": [0.1]}, "one value per ticker"),
        ({"annual_vols": [0.1]}, "one value per ticker"),
        ({"annual_vols": [-0.1, 0.1]}, "negative"),
        ({"correlation": [[1.0]]}, "square matrix"),
        ({"correlation": [[1.0, 0.5], [0.4, 1.0]]}, "symmetric"),
        ({"correlation": [[2.0, 0.5], [0.5, 2.0]]}, "unit diagonal"),
        ({"correlation": [[1.0, 1.5], [1.5, 1.0]]}, "positive definite"),
        ({"n_days": 0}, "n_days"),
        ({"initial_price": 0.0}, "initial_price"),
        ({"n_days": 2, "match_moments": True}, "match_moments"),
    ],
)
def test_invalid_inputs_are_rejected(overrides: dict[str, Any], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        generate_two_assets(**overrides)
