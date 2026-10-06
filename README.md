# FX & Rates Research Lab

A compact Python research project linking FX forward valuation, interest-rate
curve construction, swap pricing and bucketed market risk. Designed to make
pricing conventions and testable financial identities visible to a reviewer.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python -m pytest -q
fx-rates-lab --quotes data/quotes.json --output results
```

Open `results/report.html`. The sample quotes are **synthetic**, not scraped or
live. All pricing code uses the Python standard library; pytest is a dev dependency.

## Research questions

- How do domestic/foreign discount curves determine FX forward points?
- Can deposit and par-swap input quotes be repriced after bootstrapping?
- Which curve maturities drive a forward or swap's interest-rate sensitivity?
- How do spot and rate shocks change the PV of existing contracts?

## What is implemented

- Simple-rate deposit bootstrap and numerical par-swap bootstrap.
- Log-linear discount-factor interpolation with no silent extrapolation.
- Continuous zero rates, including negative-rate support.
- EURUSD forward pricing and mark-to-market in USD.
- Spot-starting pay-fixed/receive-floating swaps with semiannual fixed payments.
- Signed parallel and bucketed zero-rate sensitivities using central differences.
- Scenario analysis and reproducible CSV/HTML reporting.
- Calibration, no-arbitrage identities, sensitivity-sign and invalid-input tests.
- Linux GitHub Actions, a Python-version matrix, generated report artifacts and
  a non-root Docker runner and a configured container-delivery artifact pipeline.

## Conventions and formulas

Spot S is **domestic currency per foreign currency** (USD per EUR here).
D_d and D_f are domestic and foreign discount factors; N is foreign notional.

```
F(T) = S * D_f(T) / D_d(T)
PV_forward = N * [S * D_f(T) - K * D_d(T)]
Swap annuity = sum(accrual_i * D_d(t_i))
Par fixed rate = [1 - D_d(T)] / annuity
Pay-fixed swap PV = N * [1 - D_d(T) - K * annuity]
```

Time is in years, rates in decimals and forward points in 1e-4 quote units.
Bucket sensitivities bump interpolated **continuous zero-rate pillars**, not
market quotes; they are not hedge notionals. The reported value is a signed PV
change for a +1bp shift, so pay-fixed swap risk is normally positive. This avoids
ambiguity with DV01 conventions that reverse the sign.

## Limitations

Single-curve swaps; no distinct projection/discount curves, cross-currency basis,
FX spot settlement adjustment, calendar/day-count conventions, stub payments,
collateral modelling, credit adjustments, executable quotes or actual feeds.
No forecast or return claims. Synthetic scenarios are educational price/risk
experiments. Production FX/rates desks require richer market conventions.

## Software workflow

Use feature branches, commits and pull requests. The review template focuses on
financial identities, quote conventions, risk units and regression coverage.
CI is configured to run unit tests and generate reports on Linux; successful
local validation does not imply GitHub Actions has already run or a colleague
has reviewed this code.

## References

- QuantLib discount-curve implementation: https://github.com/lballabio/QuantLib/blob/master/ql/termstructures/yield/discountcurve.hpp
- QuantLib FX-forward tests: https://github.com/lballabio/QuantLib/blob/master/test-suite/fxforward.cpp
- QuantLib curve introduction: https://www.quantlib.org/slides/dima-ql-intro-2.pdf

This project implements a small independent educational model; it does not use
QuantLib as a dependency or claim QuantLib parity.
