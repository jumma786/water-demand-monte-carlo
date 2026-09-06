"""Run the simulation on real NESO data and write results to output/."""
import json
from pathlib import Path
import pandas as pd
from src.data import load_daily_peaks
from src.fit import fit_winter_weekday_peaks, fit_annual_trend, fit_weekend_effect
from src.simulate import (simulate, summarise, exceedance, convergence,
                          variance_contribution)

OUT = Path("output"); OUT.mkdir(exist_ok=True)
daily = load_daily_peaks()
print(f"days: {len(daily)}  {daily.index.min().date()} to {daily.index.max().date()}\n")

peaks = fit_winter_weekday_peaks(daily)
trend = fit_annual_trend(daily)
week = fit_weekend_effect(daily)
print("=== FITTED FROM DATA ===")
print(peaks["by_year"].round(0).to_string())
print(f"  skew {peaks['detrended_skew']:.3f} | KS p vs normal {peaks['ks_pvalue_vs_normal']:.4f}")
print(f"  YoY mean {trend['yoy_mean_mw']:.0f} MW, sd {trend['yoy_sd_mw']:.0f} MW")
print(f"  weekday-weekend gap {week['gap_mw']:.0f} MW (p={week['t_pvalue']:.2e})\n")

emp = simulate(daily, variation="empirical")
nor = simulate(daily, variation="normal")
se, sn = summarise(emp), summarise(nor)
rows = []
for th in (44_000, 45_000, 46_000):
    rows.append({"threshold_mw": th, "empirical": exceedance(emp, th),
                 "normal": exceedance(nor, th),
                 "overstatement_x": exceedance(nor, th) / max(exceedance(emp, th), 1e-9)})
exc = pd.DataFrame(rows)

print("=== SIMULATION ===")
print(pd.DataFrame({"empirical": se, "normal": sn}).round(0).to_string())
print("\n=== EXCEEDANCE ===")
print(exc.round(4).to_string(index=False))
var = variance_contribution(daily)
conv = convergence(daily)
print("\n=== VARIANCE ===\n" + var.round(4).to_string(index=False))
print("\n=== CONVERGENCE ===\n" + conv.round(0).to_string(index=False))

(OUT / "summary.json").write_text(json.dumps(
    {"empirical": se, "normal": sn,
     "skew": peaks["detrended_skew"], "ks_p": peaks["ks_pvalue_vs_normal"]}, indent=2))
exc.to_csv(OUT / "exceedance.csv", index=False)
var.to_csv(OUT / "variance_contribution.csv", index=False)
conv.to_csv(OUT / "convergence.csv", index=False)
peaks["by_year"].to_csv(OUT / "winter_peaks_by_year.csv")
