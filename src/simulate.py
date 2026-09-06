"""Monte Carlo forecast of next winter's peak demand, from measured inputs.

Every distribution is estimated from six years of NESO half-hourly data. The
only judgement in the model is structural: peak = last winter's level, plus a
year-on-year shift, plus day-to-day variation.

Two variants are run deliberately:
  - "normal"    : day-to-day variation drawn from a fitted normal
  - "empirical" : drawn by bootstrapping the ACTUAL residuals

The data rejects normality (see fit.py), so the gap between the two is the
error a modeller inherits by reaching for a normal out of habit.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .fit import fit_annual_trend, fit_winter_weekday_peaks


def _residuals(daily: pd.DataFrame) -> np.ndarray:
    w = daily[daily["is_winter"] & daily["is_weekday"]]
    year_means = w.groupby("year")["peak_mw"].transform("mean")
    return (w["peak_mw"] - year_means).to_numpy()


def simulate(daily: pd.DataFrame, n_sims: int = 200_000, seed: int = 42,
             variation: str = "empirical") -> np.ndarray:
    """Simulated peak demand (MW) for the winter after the data ends."""
    rng = np.random.default_rng(seed)
    peaks = fit_winter_weekday_peaks(daily)
    trend = fit_annual_trend(daily)

    last_year_mean = float(peaks["by_year"]["mean"].iloc[-1])

    # year-on-year shift: mean and spread both measured from 5 observed transitions
    yoy = rng.normal(trend["yoy_mean_mw"], trend["yoy_sd_mw"], n_sims)

    res = _residuals(daily)
    if variation == "empirical":
        day = rng.choice(res, size=n_sims, replace=True)   # bootstrap
    elif variation == "normal":
        day = rng.normal(0.0, res.std(ddof=1), n_sims)
    else:
        raise ValueError("variation must be 'empirical' or 'normal'")

    return last_year_mean + yoy + day


def summarise(sim: np.ndarray) -> dict:
    s = pd.Series(sim)
    return {
        "n_iterations": len(s),
        "mean": float(s.mean()),
        "p10": float(s.quantile(0.10)),
        "p50": float(s.quantile(0.50)),
        "p90": float(s.quantile(0.90)),
        "p99": float(s.quantile(0.99)),
        "p90_minus_p10": float(s.quantile(0.90) - s.quantile(0.10)),
    }


def exceedance(sim: np.ndarray, threshold_mw: float) -> float:
    """Probability the winter peak exceeds a stated capacity threshold."""
    return float((sim > threshold_mw).mean())


def convergence(daily: pd.DataFrame,
                sizes=(1_000, 5_000, 25_000, 100_000, 200_000, 500_000),
                seed: int = 42) -> pd.DataFrame:
    rows = []
    for n in sizes:
        s = summarise(simulate(daily, n_sims=n, seed=seed))
        rows.append({"n_sims": n, "p50": s["p50"], "p99": s["p99"]})
    df = pd.DataFrame(rows)
    df["p99_shift_vs_previous"] = df["p99"].diff().abs()
    return df


def variance_contribution(daily: pd.DataFrame, n_sims: int = 200_000,
                          seed: int = 42) -> pd.DataFrame:
    """Split the output spread between the trend term and day-to-day variation."""
    rng = np.random.default_rng(seed)
    trend = fit_annual_trend(daily)
    res = _residuals(daily)
    yoy = rng.normal(trend["yoy_mean_mw"], trend["yoy_sd_mw"], n_sims)
    day = rng.choice(res, size=n_sims, replace=True)
    total = np.var(yoy + day, ddof=1)
    rows = [
        {"component": "day-to-day variation", "variance": float(np.var(day, ddof=1))},
        {"component": "year-on-year shift", "variance": float(np.var(yoy, ddof=1))},
    ]
    out = pd.DataFrame(rows)
    out["share"] = out["variance"] / total
    return out.sort_values("share", ascending=False).reset_index(drop=True)
