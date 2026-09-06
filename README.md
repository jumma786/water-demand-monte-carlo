# Water Demand Monte Carlo

A Monte Carlo simulation of household water demand and distribution input, built
to answer a question a point estimate cannot: **how wrong could this number be,
and which assumption is making it wrong?**

```bash
pip install -r requirements.txt
python run_analysis.py
python -m pytest tests/ -q
```

---

## The finding

Running 250,000 iterations over four uncertain inputs:

| Measure | Distribution input (Ml/d) |
|---|---|
| P10 | **792.6** |
| P50 | **947.2** |
| P90 | **1,133.4** |
| Mean | 956.2 |
| Standard deviation | 131.8 |
| P90 − P10 spread | **340.8** |

**The deterministic point estimate is 911.6 Ml/d, which sits at the 39th
percentile of the simulated distribution.**

That is the reason this repository exists. Taking the central value of every
input and multiplying through does not produce the central outcome. It produces
a figure the real answer exceeds roughly 61% of the time, because the inputs
combine multiplicatively and two of them are skewed. A planner using the point
estimate is not being conservative; they are being optimistic without knowing it.

## Which assumption actually matters

Attribution by squared Spearman rank correlation, normalised:

| Input | Share of explained variance |
|---|---|
| Household occupancy | **55.6%** |
| Per capita consumption | **39.1%** |
| Leakage fraction | 4.7% |
| Meter registration factor | 0.5% |

Rank-based rather than linear, so a non-linear response does not break the
attribution.

**The practical consequence:** effort spent narrowing the meter registration
factor changes almost nothing. Half a percent of the spread is not worth a
metering study. Occupancy and per capita consumption carry 95% of the
uncertainty between them, and that is where measurement investment belongs.

## Convergence, because a Monte Carlo result without it has unknown precision

| Iterations | P50 | P90 | P50 shift vs previous |
|---|---|---|---|
| 1,000 | 943.07 | 1,126.13 | — |
| 5,000 | 946.09 | 1,130.53 | 3.02 |
| 10,000 | 949.84 | 1,131.04 | 3.75 |
| 50,000 | 947.25 | 1,130.67 | 2.59 |
| 100,000 | 948.19 | 1,131.51 | 0.94 |
| 250,000 | 947.18 | 1,133.44 | 1.01 |

The median settles to within about 1 Ml/d by 100,000 iterations. Below 10,000 the
estimate still moves by 3–4 Ml/d between runs, which is the kind of instability
that gets mistaken for a real change when a model is re-run next quarter.

## How it works

```
occupancy x per capita consumption x meter factor x households
        |
        v
household demand (Ml/d)
        |
        v  divided by (1 - leakage fraction)
distribution input (Ml/d)
```

Each input is drawn from a declared distribution (triangular, normal or uniform)
in `src/assumptions.py`. Physically impossible draws are **rejected, not silently
clipped**, because clipping quietly distorts the tail you are trying to measure.

## Testing

11 tests covering seed reproducibility, percentile ordering, the leakage
identity, rejection of invalid draws, convergence behaviour, variance shares
summing to one, and the assertion that widening an input widens the output.

```
11 passed
```

## Data and honesty

**No company data is used anywhere in this repository.** Every input is an
illustrative range declared in `src/assumptions.py`, chosen to be plausible for a
large UK water company and to exercise the model. The household count is a scale
reference only.

This means the headline numbers are **not** a forecast for any real region. What
is transferable is the method: the structure of the propagation, the convergence
check, the rejection-not-clipping rule, and the variance attribution that tells
you which assumption to go and measure properly.

Swap the contents of `src/assumptions.py` for real distributions and the analysis
runs unchanged.

## Layout

```
src/simulate.py       simulation, summary, convergence, variance attribution
src/assumptions.py    every uncertain input, declared in one place
run_analysis.py       runs it and writes output/
tests/                11 tests
output/               summary.json, convergence.csv, variance_contribution.csv
```
