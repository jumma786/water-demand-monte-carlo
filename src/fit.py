"""Estimate every simulation input FROM THE DATA. Nothing is assumed.

Each function returns both the fitted parameters and the sample they were
fitted on, so a reader can check the fit rather than trust it.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats


def fit_winter_weekday_peaks(daily: pd.DataFrame) -> dict:
    """Distribution of winter weekday peak demand, per year.

    Winter weekdays are when the system is stressed, so that is the population
    a capacity question cares about.
    """
    w = daily[daily["is_winter"] & daily["is_weekday"]]
    by_year = w.groupby("year")["peak_mw"].agg(["mean", "std", "count", "max"])
    # normal fit on the pooled, de-trended sample
    detrended = w["peak_mw"] - w["year"].map(by_year["mean"])
    mu, sigma = float(w["peak_mw"].mean()), float(detrended.std(ddof=1))
    ks = stats.kstest((detrended - detrended.mean()) / detrended.std(ddof=1), "norm")
    return {
        "pooled_mean_mw": mu,
        "within_year_sd_mw": sigma,
        "n_observations": int(len(w)),
        "by_year": by_year,
        "detrended_skew": float(stats.skew(detrended)),
        "ks_pvalue_vs_normal": float(ks.pvalue),
    }


def fit_annual_trend(daily: pd.DataFrame) -> dict:
    """Year-on-year change in winter weekday peak, measured not assumed."""
    w = daily[daily["is_winter"] & daily["is_weekday"]]
    means = w.groupby("year")["peak_mw"].mean()
    yoy = means.diff().dropna()
    return {
        "annual_means_mw": means,
        "yoy_changes_mw": yoy,
        "yoy_mean_mw": float(yoy.mean()),
        "yoy_sd_mw": float(yoy.std(ddof=1)),
        "n_transitions": int(len(yoy)),
    }


def fit_weekend_effect(daily: pd.DataFrame) -> dict:
    """Observed weekday-minus-weekend gap in winter peaks."""
    w = daily[daily["is_winter"]]
    wd = w[w["is_weekday"]]["peak_mw"]
    we = w[~w["is_weekday"]]["peak_mw"]
    t = stats.ttest_ind(wd, we, equal_var=False)
    return {
        "weekday_mean_mw": float(wd.mean()),
        "weekend_mean_mw": float(we.mean()),
        "gap_mw": float(wd.mean() - we.mean()),
        "t_pvalue": float(t.pvalue),
    }
