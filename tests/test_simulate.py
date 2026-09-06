import numpy as np
import pytest
from src.simulate import simulate, summarise, convergence, variance_contribution, Assumption
from src.assumptions import ASSUMPTIONS, HOUSEHOLDS

SMALL = 20_000


def test_reproducible_with_seed():
    a = simulate(ASSUMPTIONS, HOUSEHOLDS, n_sims=SMALL, seed=7)
    b = simulate(ASSUMPTIONS, HOUSEHOLDS, n_sims=SMALL, seed=7)
    assert a.equals(b), "same seed must reproduce identical draws"


def test_different_seeds_differ():
    a = simulate(ASSUMPTIONS, HOUSEHOLDS, n_sims=SMALL, seed=1)
    b = simulate(ASSUMPTIONS, HOUSEHOLDS, n_sims=SMALL, seed=2)
    assert not np.isclose(a["distribution_input_ml_d"].mean(),
                          b["distribution_input_ml_d"].mean(), atol=1e-9)


def test_percentiles_ordered():
    s = summarise(simulate(ASSUMPTIONS, HOUSEHOLDS, n_sims=SMALL, seed=42))
    assert s["p10"] < s["p50"] < s["p90"]


def test_distribution_input_exceeds_household_demand():
    """Leakage is additive on the distribution side, so DI must exceed demand."""
    sims = simulate(ASSUMPTIONS, HOUSEHOLDS, n_sims=SMALL, seed=42)
    assert (sims["distribution_input_ml_d"] > sims["household_demand_ml_d"]).all()


def test_invalid_draws_are_rejected_not_clipped():
    sims = simulate(ASSUMPTIONS, HOUSEHOLDS, n_sims=SMALL, seed=42)
    assert (sims["leakage_fraction"] >= 0).all()
    assert (sims["leakage_fraction"] < 0.6).all()
    assert (sims["pcc_l_per_head_per_day"] > 0).all()


def test_zero_leakage_makes_di_equal_demand():
    a = dict(ASSUMPTIONS)
    a["leakage_fraction"] = Assumption("no leak", "uniform", (0.0, 0.0), "fraction")
    sims = simulate(a, HOUSEHOLDS, n_sims=1_000, seed=3)
    assert np.allclose(sims["distribution_input_ml_d"], sims["household_demand_ml_d"])


def test_convergence_estimate_stabilises():
    """The p50 shift between successive sample sizes must shrink."""
    conv = convergence(ASSUMPTIONS, HOUSEHOLDS, sizes=(1_000, 10_000, 100_000))
    shifts = conv["p50_shift_vs_previous"].dropna().tolist()
    assert shifts[-1] < shifts[0], "estimate should settle as n grows"


def test_variance_shares_sum_to_one():
    sims = simulate(ASSUMPTIONS, HOUSEHOLDS, n_sims=SMALL, seed=42)
    var = variance_contribution(sims)
    assert np.isclose(var["share_of_explained_variance"].sum(), 1.0)


def test_occupancy_dominates_meter_factor():
    """Ordering is the actionable output; assert it explicitly."""
    sims = simulate(ASSUMPTIONS, HOUSEHOLDS, n_sims=SMALL, seed=42)
    var = variance_contribution(sims).set_index("input")
    assert (var.loc["occupancy", "share_of_explained_variance"]
            > var.loc["meter_factor", "share_of_explained_variance"])


def test_widening_an_input_widens_the_output():
    narrow = simulate(ASSUMPTIONS, HOUSEHOLDS, n_sims=SMALL, seed=5)
    wide_a = dict(ASSUMPTIONS)
    wide_a["pcc"] = Assumption("pcc wide", "normal", (138.0, 30.0), "l/h/d")
    wide = simulate(wide_a, HOUSEHOLDS, n_sims=SMALL, seed=5)
    assert (summarise(wide)["p90_minus_p10"]
            > summarise(narrow)["p90_minus_p10"])


def test_unsupported_distribution_raises():
    bad = Assumption("bad", "cauchy", (0, 1), "x")
    with pytest.raises(ValueError):
        bad.draw(10, np.random.default_rng(0))
