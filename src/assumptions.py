"""Illustrative input assumptions.

These are NOT company figures. They are plausible ranges chosen to exercise the
model, and every one is declared here so a reviewer can change a number and see
the effect rather than hunt through code.
"""
from .simulate import Assumption

HOUSEHOLDS = 2_300_000  # scale reference only

ASSUMPTIONS = {
    "occupancy": Assumption(
        name="Household occupancy",
        dist="triangular", params=(1.9, 2.35, 3.1), unit="people/household"),
    "pcc": Assumption(
        name="Per capita consumption",
        dist="normal", params=(138.0, 12.0), unit="litres/head/day"),
    "meter_factor": Assumption(
        name="Meter registration factor",
        dist="triangular", params=(0.96, 0.99, 1.01), unit="ratio"),
    "leakage_fraction": Assumption(
        name="Leakage as fraction of distribution input",
        dist="triangular", params=(0.14, 0.19, 0.26), unit="fraction"),
}
