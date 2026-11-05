import pytest

from riskanalyser.testing import FakePriceProvider, SyntheticMarket, generate_market


@pytest.fixture
def market() -> SyntheticMarket:
    """Three assets whose sample statistics exactly match their parameters."""
    return generate_market(
        tickers=["AAA", "BBB", "CCC"],
        annual_means=[0.08, 0.05, 0.02],
        annual_vols=[0.25, 0.15, 0.05],
        correlation=[
            [1.0, 0.6, -0.1],
            [0.6, 1.0, 0.1],
            [-0.1, 0.1, 1.0],
        ],
        seed=42,
        match_moments=True,
    )


@pytest.fixture
def price_provider(market: SyntheticMarket) -> FakePriceProvider:
    return FakePriceProvider(market.prices)
