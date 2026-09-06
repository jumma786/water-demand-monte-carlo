"""Real GB electricity demand from NESO, aggregated to daily peaks.

Source: NESO Historic Demand Data, half-hourly settlement periods, 2019-2024.
https://www.neso.energy/data-portal/historic-demand-data
Licence: NESO Open Data Licence.

Files are not committed; run `python -m src.download` to fetch them.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
YEARS = (2019, 2020, 2021, 2022, 2023, 2024)


def load_daily_peaks(years=YEARS) -> pd.DataFrame:
    """Daily peak National Demand (MW), one row per complete day."""
    frames = []
    for y in years:
        f = RAW / f"demanddata_{y}.csv"
        if not f.exists():
            raise FileNotFoundError(f"{f} missing. Run: python -m src.download")
        df = pd.read_csv(f)
        df.columns = [c.strip().upper() for c in df.columns]
        frames.append(df[["SETTLEMENT_DATE", "SETTLEMENT_PERIOD", "ND"]])
    hh = pd.concat(frames, ignore_index=True)
    hh["date"] = pd.to_datetime(hh["SETTLEMENT_DATE"], format="mixed", dayfirst=True)
    hh["ND"] = pd.to_numeric(hh["ND"], errors="coerce")
    hh = hh.dropna(subset=["ND"])

    g = hh.groupby("date")["ND"]
    daily = pd.DataFrame({"peak_mw": g.max(), "periods": g.size()})
    # partial days would understate the peak; drop rather than average
    daily = daily[(daily["periods"] >= 46) & (daily["periods"] <= 50)]
    daily = daily.drop(columns=["periods"]).sort_index()
    daily["year"] = daily.index.year
    daily["month"] = daily.index.month
    daily["is_winter"] = daily["month"].isin([11, 12, 1, 2])
    daily["is_weekday"] = daily.index.dayofweek < 5
    return daily
