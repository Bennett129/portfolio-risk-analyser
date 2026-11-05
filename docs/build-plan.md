# Portfolio Risk Analyser: Build Plan

Upload a portfolio's holdings and get an efficient frontier, Value at Risk, a correlation heatmap, drawdown charts and Monte Carlo projections, explained in language a non-quant can understand.

**Stack:** Python analytics package, FastAPI backend, React and TypeScript frontend.

## How to use this plan

- Work through the phases in order. Each one builds on the last and ends with something you can run or test.
- Tick off a requirement only when its code and tests are merged.
- Treat each requirement as a small piece of work, roughly one pull request.
- Sizes are relative: **S** is small, **M** is medium, **L** is large.

## v1 defaults

Change these here first if your needs differ, as later phases depend on them.

| Setting | v1 default |
|---|---|
| Portfolio type | Long-only, with no leverage, shorts or options |
| Base currency | USD, with non-USD holdings rejected or clearly flagged |
| Price frequency | Daily |
| Lookback | 5 years |
| Annualisation | 252 trading days |
| Minimum shared history | 252 daily returns; 750 for VaR backtesting |
| Portfolio size | 2 to 50 holdings |
| VaR | 95% and 99%, 1-day by default |
| Simulation | 10,000 paths over 1, 5 or 10 years |
| Return method | Today's weights applied to past returns, rebalanced daily |

The return method answers "how would today's portfolio have behaved?" It does not show the user's actual past performance, and the UI must say so.

**Out of scope for v1:** user accounts, saved portfolios, live prices, multiple currencies, derivatives, factor models and trade recommendations.

---

## Phase 0: Project setup

**Goal:** an empty project where tests and linting run locally and in CI, and the frontend starts locally. The API server arrives in Phase 5.

- [ ] **0.1 Repository (S):** Initialise git, `.gitignore`, a licence and a README stub.
- [ ] **0.2 Python project (S):** Set up `uv`, `pyproject.toml` and the `src/riskanalyser/` package.
- [ ] **0.3 Quality tools (S):** Configure Ruff, mypy and pytest with coverage.
- [ ] **0.4 Frontend project (S):** Create `frontend/` using Vite, React and strict TypeScript, with Oxlint, Prettier and Vitest. (`typescript-eslint` does not yet support TypeScript 7, so ESLint is not used.)
- [ ] **0.5 CI (S):** Run backend and frontend checks in GitHub Actions on every pull request.
- [ ] **0.6 Offline test data (M):** Add a `FakePriceProvider` and a synthetic data generator with known means, volatilities and correlations.

**Done when:** a fresh clone can install and run all checks using documented commands, and CI passes without network access.

---

## Phase 1: Data foundation and core metrics

**Goal:** a hard-coded portfolio produces correct, tested correlation, drawdown and historical VaR figures.

### 1A. Domain model

- [ ] **1.1 Core types (S):** Define `Holding`, `Portfolio`, `PriceHistory` and `AnalysisSettings`, with validation.
- [ ] **1.2 Error types (S):** Add specific errors for unknown tickers, insufficient history, missing data and provider failures.

### 1B. Market data

- [ ] **1.3 Provider interface (S):** Define `PriceProvider`, returning adjusted close, unadjusted close and available currency metadata.
- [ ] **1.4 yfinance adapter (M):** Implement the interface and convert provider failures into your own error types.
- [ ] **1.5 Local cache (M):** Store prices in Parquet or DuckDB, refresh stale data daily, and report when older cached data is used.

### 1C. Data cleaning

- [ ] **1.6 Date alignment (M):** Align assets to shared dates, and report the final window and which ticker limited it.
- [ ] **1.7 Missing data (S):** Do not fill long gaps. Report any fills applied, and reject series that break the history minimum.
- [ ] **1.8 Suspicious data (S):** Flag non-positive prices and one-day moves above 50%. Report them, but do not silently remove them.

### 1D. Returns and weights

- [ ] **1.9 Portfolio weights (S):** Calculate market value as `quantity × latest unadjusted close`, then convert to weights that sum to 1.
- [ ] **1.10 Asset returns (S):** Calculate simple and log returns from adjusted close, with function names that make the type explicit.
- [ ] **1.11 Portfolio returns (S):** Combine simple asset returns using fixed weights.
- [ ] **1.12 Summary statistics (S):** Add annualised return, volatility, CAGR, Sharpe ratio, skew and excess kurtosis.

### 1E. First risk metrics

- [ ] **1.13 Correlation (S):** Calculate the correlation matrix over the shared date window.
- [ ] **1.14 Cluster ordering (S):** Group similar assets using SciPy hierarchical clustering so the heatmap is easier to read.
- [ ] **1.15 Drawdown (M):** Calculate the drawdown series, maximum drawdown, peak, trough, recovery date and duration. Mark unrecovered drawdowns as ongoing.
- [ ] **1.16 Historical VaR (S):** Calculate VaR as a positive loss, in both percentage and currency terms.
- [ ] **1.17 Historical CVaR (S):** Calculate the average loss beyond the VaR cutoff.

### Required tests

- [ ] Prices `[100, 120, 90, 110, 130]` give a maximum drawdown of 25%, with recovery at 130.
- [ ] A correlation matrix is symmetric, has a diagonal of 1, and has all values between −1 and 1.
- [ ] A 2-for-1 split in the raw price does not create a −50% return when adjusted prices are used.
- [ ] Portfolio weights always sum to 1.
- [ ] CVaR is never smaller than VaR at the same confidence level.
- [ ] Results match QuantStats or another independent calculation within a documented tolerance.

**Done when:** one command prints all Phase 1 metrics for a sample portfolio, and the tests run offline.

---

## Phase 2: Estimators, parametric VaR and efficient frontier

**Goal:** a stable long-only frontier showing the user's position and the uncertainty in the result.

### 2A. Estimators

- [ ] **2.1 Sample covariance (S):** Calculate and annualise the covariance matrix.
- [ ] **2.2 Shrinkage covariance (S):** Add Ledoit-Wolf and make it the default.
- [ ] **2.3 Matrix health checks (S):** Check symmetry, positive semi-definiteness, condition number and the ratio of observations to assets.
- [ ] **2.4 Expected returns (M):** Add historical mean returns, with optional shrinkage toward the cross-asset average.

### 2B. Parametric risk

- [ ] **2.5 Parametric VaR and CVaR (S):** Implement both using the normal distribution and the portfolio mean and volatility.
- [ ] **2.6 Multi-day VaR (S):** Add square-root-of-time scaling and return the independence assumption with the result.
- [ ] **2.7 Method comparison (S):** Show historical and parametric VaR together, and flag large differences as possible evidence of fat tails.

### 2C. Efficient frontier

- [ ] **2.8 Minimum-variance portfolio (S):** Solve it in CVXPY, long-only and fully invested.
- [ ] **2.9 Maximum-return portfolio (S):** Find the top of the feasible frontier under the same constraints.
- [ ] **2.10 Frontier sweep (M):** Solve about 50 target returns, then handle infeasible and failed solves explicitly.
- [ ] **2.11 Maximum Sharpe portfolio (M):** Add it using a risk-free rate from FRED, with a configurable fallback.
- [ ] **2.12 Maximum position size (S):** Add an optional per-asset limit, and reject limits that make the problem infeasible.
- [ ] **2.13 Current portfolio position (S):** Calculate where the user's portfolio sits relative to the frontier, including same-risk and same-return comparisons.
- [ ] **2.14 Frontier uncertainty (M):** Re-estimate the frontier on bootstrapped returns to create an uncertainty band.

### 2D. Risk attribution

- [ ] **2.15 Risk contribution (S):** Calculate each holding's share of portfolio variance using `w_i (Σw)_i / (wᵀΣw)`.
- [ ] **2.16 Diversification ratio (S):** Calculate weighted average volatility divided by portfolio volatility.

### Required tests

- [ ] For normal returns with zero mean, 95% VaR is about `1.645σ` and CVaR is about `2.063σ`.
- [ ] The two-asset minimum-variance result matches the closed-form solution when that solution has no negative weights.
- [ ] Every frontier result is long-only and fully invested, and it respects position limits.
- [ ] Volatility increases along the frontier as target return rises, within solver tolerance.
- [ ] Risk contributions sum to 1.
- [ ] Too little history produces a warning, or a clear error if the result cannot be calculated.
- [ ] Results match PyPortfolioOpt within a documented tolerance.

**Done when:** a script exports a frontier plot containing the user's position, the key optimal portfolios and an uncertainty band.

---

## Phase 3: Monte Carlo simulation

**Goal:** reproducible projections with assumptions that are visible and can be changed.

### 3A. Simulation engine

- [ ] **3.1 Configuration (S):** Define horizon, path count, starting value, seed, drift method and simulation method.
- [ ] **3.2 Correlated normal returns (M):** Generate asset-level log returns using Cholesky decomposition, with a clear fallback or error if decomposition fails.
- [ ] **3.3 Block bootstrap (M):** Sample blocks of whole trading days, so assets keep their same-day relationships and some volatility clustering.
- [ ] **3.4 Drift options (S):** Support historical drift, zero drift and a user-entered annual return. Remove the historical drift from bootstrap samples when another option is chosen.
- [ ] **3.5 Portfolio paths (M):** Convert log returns to simple returns, apply daily rebalanced weights, and compound the result.
- [ ] **3.6 Memory limits (M):** Simulate in batches and keep only portfolio-level paths.

### 3B. Results

- [ ] **3.7 Fan chart data (S):** Return the 5th, 10th, 25th, 50th, 75th, 90th and 95th percentiles over time, not all paths.
- [ ] **3.8 Outcome probabilities (S):** Calculate the chance of ending below the starting value and of reaching a user-entered target.
- [ ] **3.9 Path drawdowns (S):** Calculate the distribution of each path's maximum drawdown.
- [ ] **3.10 Method comparison (S):** Show normal and bootstrap results together, with a short explanation of any difference.

### Required tests

- [ ] The same seed gives identical results, and a different seed gives different results.
- [ ] With zero volatility, every path matches the expected deterministic growth.
- [ ] Simulated means and correlations match the inputs within sampling error.
- [ ] Percentiles are ordered correctly at every time step.
- [ ] Bootstrap samples use only whole days from the source data.
- [ ] A performance test records runtime and peak memory for 10,000 paths, 10 years and 50 assets.

**Done when:** default settings finish within a documented time budget, and the results show their assumptions.

---

## Phase 4: VaR backtesting

**Goal:** evidence showing whether the VaR models matched what happened.

- [ ] **4.1 Rolling forecasts (M):** Estimate VaR using a 500-day window, then test it on the next day without lookahead.
- [ ] **4.2 Breach tracking (S):** Record every date on which the loss exceeded VaR.
- [ ] **4.3 Kupiec test (M):** Calculate the likelihood-ratio statistic and p-value, including when there are zero breaches.
- [ ] **4.4 Independence check (M):** Add the Christoffersen test to detect clustered breaches.
- [ ] **4.5 Model comparison (S):** Compare historical and parametric VaR at both confidence levels.
- [ ] **4.6 Backtest results (S):** Return the expected and actual breach counts, test results, breach dates and any warnings.

### Required tests

- [ ] Changing a future return cannot alter an earlier VaR forecast.
- [ ] Kupiec results match a hand-calculated example.
- [ ] Synthetic normal data breaches 95% VaR at close to the expected 5% rate.
- [ ] A short return history produces an "insufficient history" result rather than a misleading statistic.

**Done when:** the backtest runs on the sample portfolio and its results are ready for the API.

---

## Phase 5: FastAPI backend and upload flow

**Goal:** a documented API can validate holdings and return the full analysis.

### 5A. Application

- [ ] **5.1 App setup (S):** Create the FastAPI app, versioned routes, environment settings and CORS rules.
- [ ] **5.2 Health endpoint (S):** Add `GET /health`.
- [ ] **5.3 Response schemas (M):** Define Pydantic models for each analysis section and shared warnings.
- [ ] **5.4 Error format (S):** Return consistent machine-readable error codes with user-friendly messages.

### 5B. Upload and validation

- [ ] **5.5 Holdings validation (M):** Add `POST /api/v1/portfolios/validate` for CSV files with `ticker` and `quantity` columns.
- [ ] **5.6 File safety (S):** Enforce a 1 MB limit, file type checks, UTF-8 decoding and a row limit.
- [ ] **5.7 Row-level errors (S):** Report missing fields, invalid quantities, duplicate tickers, negative positions and unknown tickers.
- [ ] **5.8 Sample portfolio (S):** Add `GET /api/v1/portfolios/sample`.

### 5C. Analysis endpoints

- [ ] **5.9 Interpretation engine (M):** Implement `explain/` as pure functions returning a headline, detail, assumptions and severity.
- [ ] **5.10 Full analysis (M):** Add `POST /api/v1/analysis`, combining all sections and their explanations.
- [ ] **5.11 Simulation rerun (S):** Add `POST /api/v1/analysis/simulation`, so changing assumptions does not rerun everything.
- [ ] **5.12 JSON safety (S):** Convert `NaN` and infinity to `null`, or to a clear warning.
- [ ] **5.13 CPU-bound work (S):** Use sync route handlers so heavy work stays off the async event loop, and enforce an analysis time limit.

### 5D. Protection

- [ ] **5.14 No retained holdings (S):** Process uploads in memory and keep holdings out of logs.
- [ ] **5.15 Rate limiting (S):** Limit expensive endpoints by client.
- [ ] **5.16 Structured logging (S):** Log request ID, duration and status without any portfolio data.

### Required tests

- [ ] Route tests cover success and every documented error using `FakePriceProvider`.
- [ ] A contract test confirms the OpenAPI schema can generate the TypeScript types.
- [ ] A log capture test confirms holdings do not appear in logs.
- [ ] Explanation tests cover every threshold, and no text recommends buying or selling a security.

**Done when:** the full upload-to-analysis flow works from the OpenAPI docs page.

---

## Phase 6: React frontend

**Goal:** a non-quant can upload a portfolio and understand the results without help.

### 6A. Foundations

- [ ] **6.1 API types (S):** Generate TypeScript types from OpenAPI using `openapi-typescript`.
- [ ] **6.2 API client (S):** Use TanStack Query for requests, loading state and errors.
- [ ] **6.3 Design foundations (M):** Create layout, typography, colour tokens, number formatting and responsive rules.
- [ ] **6.4 Shared states (S):** Build loading, empty, warning and error components, plus an error boundary.
- [ ] **6.5 Chart foundation (M):** Create a Plotly wrapper with shared styling, and lazy-load the Plotly bundle.

### 6B. Upload flow

- [ ] **6.6 Landing page (S):** Explain the product and offer upload or sample portfolio options.
- [ ] **6.7 File upload (M):** Add drag and drop, a file picker and a downloadable CSV template.
- [ ] **6.8 Validation review (M):** Show parsed holdings and row-level errors before analysis.
- [ ] **6.9 Analysis settings (S):** Add lookback and confidence controls with sensible defaults.
- [ ] **6.10 Analysis progress (S):** Show progress and let users retry after a failure.

### 6C. Results

- [ ] **6.11 Overview (M):** Show key numbers, the biggest risk findings and data warnings.
- [ ] **6.12 VaR and backtest (M):** Show a return histogram, VaR and CVaR markers, and a plain-English backtest result.
- [ ] **6.13 Efficient frontier (M):** Show the frontier, uncertainty band, "you are here" marker and hover details.
- [ ] **6.14 Correlation heatmap (M):** Use clustered order, a fixed −1 to +1 diverging scale and value tooltips.
- [ ] **6.15 Risk contribution (S):** Compare each holding's portfolio weight with its share of risk.
- [ ] **6.16 Drawdown (M):** Show an underwater chart with the worst drawdown and recovery period marked.
- [ ] **6.17 Monte Carlo (M):** Show a fan chart with controls for horizon, drift, starting value and target.
- [ ] **6.18 Assumptions and methods (S):** Add an expandable explanation to each chart section.
- [ ] **6.19 Disclaimer (S):** State that results are historical analysis, not financial advice.

### 6D. Quality

- [ ] **6.20 Accessibility (M):** Support keyboard use and screen readers, avoid relying on colour alone, and provide table alternatives for charts.
- [ ] **6.21 Mobile layout (M):** Keep charts readable at phone width, with no horizontal page scrolling.
- [ ] **6.22 Component tests (M):** Test upload states, warnings, formatting and result rendering with Vitest and Testing Library.
- [ ] **6.23 End-to-end tests (M):** Use Playwright to cover the sample portfolio, valid upload and invalid upload flows.
- [ ] **6.24 User test (S):** Ask two or three non-quants to explain each chart, then fix what confuses them.

**Done when:** test users can correctly explain the VaR, correlation and Monte Carlo sections in their own words.

---

## Phase 7: Deployment and project presentation

**Goal:** a public demo and a repository that clearly shows your statistical reasoning.

### 7A. Deployment

- [ ] **7.1 Containers (S):** Add a backend Dockerfile and a Compose setup for local use.
- [ ] **7.2 Backend hosting (M):** Deploy to Render, Fly.io or similar, with persistent cache storage if available.
- [ ] **7.3 Frontend hosting (S):** Deploy to Vercel, Netlify or similar, with production CORS settings.
- [ ] **7.4 Secrets (S):** Store API keys in the hosting provider's secret storage.
- [ ] **7.5 Production data check (M):** Confirm the data provider's terms allow public use and that it works reliably from the host. Switch provider if needed.
- [ ] **7.6 Monitoring (S):** Add uptime checks and error reporting with portfolio data scrubbed.
- [ ] **7.7 Deploy pipeline (S):** Deploy automatically after checks pass on the main branch.

### 7B. Presentation

- [ ] **7.8 README (M):** Add a demo link, screenshots, an architecture diagram and setup instructions.
- [ ] **7.9 Methodology document (M):** Explain formulas, assumptions, limitations and why each method was chosen.
- [ ] **7.10 Validation report (M):** Publish independent-library comparisons and VaR backtest results.
- [ ] **7.11 Walkthrough (S):** Record a short demo using the sample portfolio.

**Done when:** a stranger can open the demo, load the sample portfolio and get results without any setup.

---

## Optional extensions

Add these only after v1 is complete:

1. **Multi-currency support:** the most useful next step, covering FX conversion and currency risk.
2. **GARCH volatility:** forecast changing volatility using `arch`.
3. **Stress tests:** replay events such as 2008 and 2020.
4. **Student-t simulation:** add a parametric fat-tailed model.
5. **Benchmark comparison:** add beta, tracking error and a chosen market index.
6. **Downloadable PDF report:** package the results for sharing.
7. **Accounts and saved portfolios:** this adds a database, authentication and stricter data-security duties.

## Definition of done for every requirement

- [ ] Types, linting and tests pass in CI.
- [ ] Calculations cover normal cases and edge cases, and have a known-answer or independent check where possible.
- [ ] Units are clear, such as daily or annual, and percentage or currency.
- [ ] Assumptions and data problems reach the API response, and the UI where relevant.
- [ ] Failures produce a clear error rather than a misleading number.
