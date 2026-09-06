import numpy as np
import pytest
from src.data import load_daily_peaks
from src.fit import fit_winter_weekday_peaks, fit_weekend_effect
from src.simulate import (simulate, summarise, exceedance, convergence,
                          variance_contribution, _residuals)

N = 20_000


@pytest.fixture(scope="module")
def daily():
    return load_daily_peaks()


def test_real_data_loads_six_years(daily):
    assert daily.index.min().year == 2019 and daily.index.max().year == 2024
    assert 2150 < len(daily) < 2200, "expect ~2192 complete days"


def test_partial_days_excluded(daily):
    """Every retained day must be a full day of settlement periods."""
    assert daily["peak_mw"].min() > 10_000, "a partial day would show as a dip"


def test_peaks_are_physically_plausible(daily):
    assert daily["peak_mw"].between(15_000, 60_000).all()


def test_winter_peaks_exceed_summer(daily):
    w = daily[daily["is_winter"]]["peak_mw"].mean()
    s = daily[daily["month"].isin([6, 7, 8])]["peak_mw"].mean()
    assert w > s, "GB winter peaks must exceed summer"


def test_weekday_effect_is_real_and_signed(daily):
    e = fit_weekend_effect(daily)
    assert e["gap_mw"] > 0, "weekday peaks should exceed weekend"
    assert e["t_pvalue"] < 0.01


def test_residuals_are_centred(daily):
    r = _residuals(daily)
    assert abs(r.mean()) < 1e-6, "within-year residuals must centre on zero"


def test_data_rejects_normality(daily):
    """The finding the whole README rests on; assert it so it cannot rot."""
    f = fit_winter_weekday_peaks(daily)
    assert f["ks_pvalue_vs_normal"] < 0.05, "normality no longer rejected"
    assert f["detrended_skew"] < -0.3, "left skew has changed"


def test_reproducible_with_seed(daily):
    a = simulate(daily, n_sims=N, seed=7)
    b = simulate(daily, n_sims=N, seed=7)
    assert np.array_equal(a, b)


def test_percentiles_ordered(daily):
    s = summarise(simulate(daily, n_sims=N, seed=42))
    assert s["p10"] < s["p50"] < s["p90"] < s["p99"]


def test_normal_overstates_the_upper_tail(daily):
    """The headline result, asserted."""
    emp = simulate(daily, n_sims=200_000, seed=42, variation="empirical")
    nor = simulate(daily, n_sims=200_000, seed=42, variation="normal")
    assert exceedance(nor, 45_000) > 2 * exceedance(emp, 45_000)


def test_exceedance_is_monotonic(daily):
    sim = simulate(daily, n_sims=N, seed=42)
    assert exceedance(sim, 40_000) > exceedance(sim, 44_000) > exceedance(sim, 48_000)


def test_variance_shares_sum_to_about_one(daily):
    v = variance_contribution(daily, n_sims=N)
    assert 0.97 < v["share"].sum() < 1.03


def test_day_to_day_dominates_annual_shift(daily):
    v = variance_contribution(daily, n_sims=N).set_index("component")
    assert (v.loc["day-to-day variation", "share"]
            > v.loc["year-on-year shift", "share"])


def test_convergence_tightens(daily):
    c = convergence(daily, sizes=(1_000, 25_000, 500_000))
    shifts = c["p99_shift_vs_previous"].dropna().tolist()
    assert shifts[-1] < shifts[0]


def test_unknown_variation_raises(daily):
    with pytest.raises(ValueError):
        simulate(daily, n_sims=100, variation="student-t")
