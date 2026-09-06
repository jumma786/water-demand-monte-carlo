"""Run the simulation and write results to output/."""
import json
from pathlib import Path
from src.simulate import simulate, summarise, convergence, variance_contribution
from src.assumptions import ASSUMPTIONS, HOUSEHOLDS

OUT = Path("output"); OUT.mkdir(exist_ok=True)

sims = simulate(ASSUMPTIONS, HOUSEHOLDS, n_sims=250_000, seed=42)
summ = summarise(sims)
conv = convergence(ASSUMPTIONS, HOUSEHOLDS)
var = variance_contribution(sims)

# deterministic point estimate, for comparison against the distribution
point = (HOUSEHOLDS * 2.35 * 138.0 * 0.99 / 1e6) / (1 - 0.19)
summ["deterministic_point_estimate"] = float(point)
summ["point_estimate_percentile"] = float((sims["distribution_input_ml_d"] < point).mean())

(OUT / "summary.json").write_text(json.dumps(summ, indent=2))
conv.to_csv(OUT / "convergence.csv", index=False)
var.to_csv(OUT / "variance_contribution.csv", index=False)

print("=== DISTRIBUTION INPUT (Ml/d) ===")
for k, v in summ.items():
    print(f"  {k:32s} {v:,.4f}" if isinstance(v, float) else f"  {k:32s} {v:,}")
print("\n=== CONVERGENCE ===")
print(conv.to_string(index=False))
print("\n=== VARIANCE CONTRIBUTION ===")
print(var.to_string(index=False))
