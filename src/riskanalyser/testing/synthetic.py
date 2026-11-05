"""Reproducible synthetic prices with known statistical properties.

Daily log returns are drawn from a multivariate normal distribution, so tests can compare
calculated metrics against the parameters that generated the data.
"""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
import pandas as pd

TRADING_DAYS_PER_YEAR = 252

FloatArray = npt.NDArray[np.float64]


@dataclass(frozen=True)
class SyntheticMarket:
    """Generated data, together with the parameters used to generate it.

    Means and volatilities are annualised and describe log returns, not simple returns.
    """

    prices: pd.DataFrame
    log_returns: pd.DataFrame
    annual_means: pd.Series
    annual_vols: pd.Series
    correlation: pd.DataFrame


def generate_market(
    tickers: Sequence[str],
    annual_means: Sequence[float],
    annual_vols: Sequence[float],
    correlation: Sequence[Sequence[float]],
    *,
    n_days: int = 1260,
    start: str = "2020-01-01",
    initial_price: float = 100.0,
    seed: int = 0,
    match_moments: bool = False,
) -> SyntheticMarket:
    """Generate daily prices for correlated assets.

    With ``match_moments=True`` the sample mean, volatility and correlation of the returns
    equal the inputs to within floating-point error. Use this for known-answer tests. Leave
    it off to test behaviour that should hold despite ordinary sampling error.

    Raises:
        ValueError: If the inputs are inconsistent, or the correlation matrix is not a
            symmetric, positive definite matrix with a unit diagonal.
    """
    names = list(tickers)
    means = np.asarray(annual_means, dtype=np.float64)
    vols = np.asarray(annual_vols, dtype=np.float64)
    corr = np.asarray(correlation, dtype=np.float64)
    _validate_inputs(names, means, vols, corr, n_days, initial_price, match_moments)

    shocks = np.random.default_rng(seed).standard_normal((n_days, len(names)))
    if match_moments:
        shocks = _standardise(shocks)

    daily_means = means / TRADING_DAYS_PER_YEAR
    daily_vols = vols / np.sqrt(TRADING_DAYS_PER_YEAR)
    returns = daily_means + (shocks @ np.linalg.cholesky(corr).T) * daily_vols

    growth = np.vstack([np.zeros(len(names)), np.cumsum(returns, axis=0)])
    dates = pd.bdate_range(start=start, periods=n_days + 1)

    return SyntheticMarket(
        prices=pd.DataFrame(initial_price * np.exp(growth), index=dates, columns=names),
        log_returns=pd.DataFrame(returns, index=dates[1:], columns=names),
        annual_means=pd.Series(means, index=names),
        annual_vols=pd.Series(vols, index=names),
        correlation=pd.DataFrame(corr, index=names, columns=names),
    )


def _validate_inputs(
    names: list[str],
    means: FloatArray,
    vols: FloatArray,
    corr: FloatArray,
    n_days: int,
    initial_price: float,
    match_moments: bool,
) -> None:
    n_assets = len(names)
    if n_assets == 0:
        raise ValueError("at least one ticker is required")
    if len(set(names)) != n_assets:
        raise ValueError("tickers must be unique")
    if means.shape != (n_assets,) or vols.shape != (n_assets,):
        raise ValueError("annual_means and annual_vols must have one value per ticker")
    if corr.shape != (n_assets, n_assets):
        raise ValueError("correlation must be a square matrix with one row per ticker")
    if np.any(vols < 0):
        raise ValueError("annual_vols cannot be negative")
    if n_days < 1:
        raise ValueError("n_days must be at least 1")
    if initial_price <= 0:
        raise ValueError("initial_price must be positive")
    if match_moments and n_days <= n_assets:
        raise ValueError("match_moments requires n_days to exceed the number of tickers")
    if not np.allclose(corr, corr.T) or not np.allclose(np.diag(corr), 1.0):
        raise ValueError("correlation must be symmetric with a unit diagonal")
    try:
        np.linalg.cholesky(corr)
    except np.linalg.LinAlgError as error:
        raise ValueError("correlation must be positive definite") from error


def _standardise(shocks: FloatArray) -> FloatArray:
    """Transform shocks to have exactly zero sample mean and identity sample covariance."""
    centred = shocks - shocks.mean(axis=0)
    sample_cov = np.atleast_2d(np.cov(centred, rowvar=False))
    return np.linalg.solve(np.linalg.cholesky(sample_cov), centred.T).T
