# Peak Demand Monte Carlo — On Real Data

A Monte Carlo forecast of next winter's peak electricity demand, where **every
input distribution is estimated from measured data rather than assumed**.

The headline result is about method, not megawatts: reaching for a normal
distribution out of habit **overstates the tail risk by a factor of four**.

```bash
python -m src.download      # fetch the NESO CSVs (not committed)
python run_analysis.py
python -m pytest tests/ -q
```

---

## The data

**NESO (National Energy System Operator) Historic Demand Data**, half-hourly
settlement periods for 2019–2024, under the NESO Open Data Licence.
<https://www.neso.energy/data-portal/historic-demand-data>

105,222 half-hourly readings, aggregated to **2,192 complete days**. Days with
fewer than 46 or more than 50 settlement periods are dropped rather than
averaged, because a partially captured day looks like a demand dip that never
happened. Clock-change days legitimately have 46 or 50 and are kept.

The population of interest is **winter weekday peaks** (Nov–Feb, Mon–Fri), which
is when the system is stressed and therefore what a capacity question is about.
That gives 516 observations.

## What the data says before any simulation runs

| Year | Mean winter weekday peak (MW) | SD | n |
|---|---|---|---|
| 2019 | 43,278 | 2,555 | 86 |
| 2020 | 42,043 | 1,891 | 87 |
| 2021 | 42,172 | 2,585 | 86 |
| 2022 | 40,286 | 3,407 | 85 |
| 2023 | 39,212 | 2,847 | 85 |
| 2024 | 39,420 | 2,813 | 87 |

Year-on-year change averages **−772 MW** with a standard deviation of **911 MW**
across five transitions, so the decline is real but noisy: two of the five years
went up.

Weekday peaks exceed weekend peaks by **3,172 MW** (Welch t-test, p = 1.15e-29).

**And the distribution is not normal.** De-trended winter weekday peaks have a
skew of **−0.687**, and a Kolmogorov–Smirnov test rejects normality at
**p = 0.0145**.

## The finding

Two variants of the same simulation, 200,000 iterations each. Both use the same
measured year-on-year term. They differ only in how day-to-day variation is
drawn: from a fitted normal, or by **bootstrapping the actual residuals**.

| | Empirical bootstrap | Fitted normal |
|---|---|---|
| P50 | 38,843 MW | 38,656 MW |
| P90 | 42,135 MW | 42,304 MW |
| **P99** | **44,275 MW** | **45,265 MW** |

| Exceedance | Empirical | Normal | Overstatement |
|---|---|---|---|
| P(peak > 44,000 MW) | 1.47% | 3.00% | **2.0×** |
| P(peak > 45,000 MW) | 0.30% | 1.30% | **4.3×** |
| P(peak > 46,000 MW) | 0.04% | 0.48% | **12×** |

Because the real distribution is left-skewed, a normal puts far too much mass in
the upper tail. An analyst who fits a normal without testing it will plan for a
peak roughly four times less likely than their model claims, and the error grows
the further into the tail you look — which is precisely the region a capacity
margin decision lives in.

The KS test that catches this takes one line. It is asserted in the test suite so
the finding cannot quietly rot if the data is refreshed.

## Where the uncertainty comes from

| Component | Share of variance |
|---|---|
| Day-to-day variation | **89.6%** |
| Year-on-year shift | 10.2% |

Nine tenths of the spread is weather and behaviour on the day, not the trend.
Refining the trend estimate is therefore close to worthless for this question;
the payoff is in modelling daily variation better.

## Convergence

| Iterations | P50 | P99 | P99 shift vs previous |
|---|---|---|---|
| 1,000 | 38,827 | 44,006 | — |
| 5,000 | 38,780 | 44,140 | 134 |
| 25,000 | 38,839 | 44,274 | 134 |
| 100,000 | 38,821 | 44,207 | 68 |
| 200,000 | 38,843 | 44,275 | 68 |
| 500,000 | 38,823 | 44,241 | 34 |

Tail percentiles converge far more slowly than the median. At 1,000 iterations
the P99 still moves by over 130 MW between runs, which is enough to change a
margin decision. A Monte Carlo result quoted without a convergence check is a
number of unknown precision.

## Testing

15 tests, all passing. They cover data span and completeness, physical
plausibility, the winter-exceeds-summer and weekday-exceeds-weekend sanity
checks, residual centring, **the non-normality finding**, seed reproducibility,
percentile ordering, **the normal-overstates-the-tail result**, exceedance
monotonicity, variance shares, and convergence tightening.

## Honesty

The data is real and openly licensed. The simulation structure is a
deliberate simplification: peak = last winter's level + a year-on-year shift +
day-to-day variation. It carries no weather covariate, no explicit COVID
adjustment for 2020, and no embedded-generation treatment, all of which a
production forecast would need.

So the megawatt figures are a demonstration, not an operational forecast. What
transfers is the method: fitting inputs from data instead of assuming them,
testing the distributional assumption before relying on it, separating where the
uncertainty actually comes from, and checking convergence at the percentile you
intend to quote.

## Layout

```
src/data.py        load NESO half-hourly, aggregate to daily peaks
src/fit.py         estimate every input from the data, with fit diagnostics
src/simulate.py    simulation, summary, exceedance, convergence, variance split
src/download.py    fetch the source CSVs
run_analysis.py    runs everything, writes output/
tests/             15 tests
```
