"""Monte Carlo simulation of household water demand.

Propagates uncertainty from four independent inputs through to distributed
demand, so a planner receives a range with stated confidence rather than a
single point estimate.

All parameters are ILLUSTRATIVE ranges declared in `assumptions.py`. No
company data is used; see README "Data and honesty".
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass


@dataclass(frozen=True)
class Assumption:
    """A named uncertain input, expressed as a distribution."""
    name: str
    dist: str          # "normal" | "lognormal" | "triangular" | "uniform"
    params: tuple
    unit: str

    def draw(self, n: int, rng: np.random.Generator) -> np.ndarray:
        if self.dist == "normal":
            mu, sd = self.params
            return rng.normal(mu, sd, n)
        if self.dist == "lognormal":
            mu, sigma = self.params
            return rng.lognormal(mu, sigma, n)
        if self.dist == "triangular":
            lo, mode, hi = self.params
            return rng.triangular(lo, mode, hi, n)
        if self.dist == "uniform":
            lo, hi = self.params
            return rng.uniform(lo, hi, n)
        raise ValueError(f"unsupported distribution: {self.dist}")


def simulate(assumptions: dict[str, Assumption], households: int,
             n_sims: int = 100_000, seed: int = 42) -> pd.DataFrame:
    """Run the simulation and return per-iteration components and totals.

    Demand (Ml/d) = households x occupancy x PCC x meter_factor / 1e6
    Distribution input = demand / (1 - leakage_fraction)
    """
    rng = np.random.default_rng(seed)
    occ = assumptions["occupancy"].draw(n_sims, rng)
    pcc = assumptions["pcc"].draw(n_sims, rng)
    meter = assumptions["meter_factor"].draw(n_sims, rng)
    leak = assumptions["leakage_fraction"].draw(n_sims, rng)

    # guard rails: physical impossibilities are rejected, not clipped silently
    valid = (occ > 0) & (pcc > 0) & (meter > 0) & (leak >= 0) & (leak < 0.6)
    occ, pcc, meter, leak = occ[valid], pcc[valid], meter[valid], leak[valid]

    household_demand_ml_d = households * occ * pcc * meter / 1e6
    distribution_input_ml_d = household_demand_ml_d / (1.0 - leak)

    return pd.DataFrame({
        "occupancy": occ,
        "pcc_l_per_head_per_day": pcc,
        "meter_factor": meter,
        "leakage_fraction": leak,
        "household_demand_ml_d": household_demand_ml_d,
        "distribution_input_ml_d": distribution_input_ml_d,
    })


def summarise(sims: pd.DataFrame, column: str = "distribution_input_ml_d") -> dict:
    s = sims[column]
    return {
        "n_iterations": int(len(s)),
        "mean": float(s.mean()),
        "std": float(s.std(ddof=1)),
        "p10": float(s.quantile(0.10)),
        "p50": float(s.quantile(0.50)),
        "p90": float(s.quantile(0.90)),
        "p90_minus_p10": float(s.quantile(0.90) - s.quantile(0.10)),
    }


def convergence(assumptions: dict, households: int,
                sizes=(1_000, 5_000, 10_000, 50_000, 100_000, 250_000),
                seed: int = 42) -> pd.DataFrame:
    """Show the estimate stabilising as iteration count grows.

    A Monte Carlo result quoted without this is a number of unknown precision.
    """
    rows = []
    for n in sizes:
        summ = summarise(simulate(assumptions, households, n_sims=n, seed=seed))
        rows.append({"n_sims": n, "p50": summ["p50"], "p90": summ["p90"],
                     "std": summ["std"]})
    df = pd.DataFrame(rows)
    df["p50_shift_vs_previous"] = df["p50"].diff().abs()
    return df


def variance_contribution(sims: pd.DataFrame) -> pd.DataFrame:
    """Which input actually drives the spread.

    Uses squared Spearman rank correlation between each input and the output,
    normalised to sum to 1. Rank-based so a non-linear response does not break
    the attribution.
    """
    from scipy.stats import spearmanr
    target = sims["distribution_input_ml_d"]
    inputs = ["occupancy", "pcc_l_per_head_per_day", "meter_factor",
              "leakage_fraction"]
    rho2 = {}
    for c in inputs:
        r, _ = spearmanr(sims[c], target)
        rho2[c] = r ** 2
    total = sum(rho2.values())
    out = (pd.DataFrame({"input": list(rho2), "rho_squared": list(rho2.values())})
           .assign(share_of_explained_variance=lambda d: d.rho_squared / total)
           .sort_values("share_of_explained_variance", ascending=False)
           .reset_index(drop=True))
    return out
