# Portfolio Risk Analyser

Upload a portfolio's holdings and get an efficient frontier, Value at Risk, a correlation heatmap, drawdown charts and Monte Carlo projections, explained in plain English.

**Status:** early development. See the [build plan](docs/build-plan.md) for what's planned.

Results will be historical analysis, not financial advice.

## Project layout

```text
src/riskanalyser/   Python analytics package
  testing/          Synthetic market data and a fake price provider
tests/              Python tests
frontend/           React and TypeScript app
docs/               Build plan
```

## Setup

You need [uv](https://docs.astral.sh/uv/) and Node.js 24. `uv` installs the correct Python version for you.

```sh
uv sync
npm ci --prefix frontend
```

## Python checks

```sh
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest --cov
```

Tests run offline. Any test that tries to use the network fails.

## Frontend

Run these from `frontend/`:

```sh
npm run dev           # start the development server
npm run lint
npm run format:check
npm run typecheck
npm test
npm run build
```

## License

[MIT](LICENSE)
