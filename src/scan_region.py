"""Regional scan - measure every ~20 km grid square in a region -> data/raw/scan_<region>.csv

The challenge asks to search Earth systematically for analogs nobody has studied yet,
not only to rank places we already know. This script splits a region into squares the
same size as our site boxes (20 x 20 km) and measures every square with exactly the same
code as the 23 sites (src/ingest_earth.site_features), so the numbers are comparable.

    EE_PROJECT=your-project python -m src.scan_region --limit 5   # quick test, 5 squares
    EE_PROJECT=your-project python -m src.scan_region             # whole region

PowerShell:
    $env:EE_PROJECT="your-project"; python -m src.scan_region --limit 5

Squares over the sea come back without land data and are dropped.
"""
import argparse
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from .common import RAW, ensure_dirs
from .ingest_earth import site_features

# Negev, Sinai, Arava and southern Jordan
REGIONS = {
    "negev_sinai_jordan": {"lat": (27.6, 31.6), "lon": (32.4, 36.8)},
}
CELL_KM = 20  # same as the 20 x 20 km site boxes


def grid(name):
    box = REGIONS[name]
    dlat = CELL_KM / 111.0
    cells = []
    lat = box["lat"][0] + dlat / 2
    i = 0
    while lat < box["lat"][1]:
        dlon = CELL_KM / (111.0 * math.cos(math.radians(lat)))
        lon = box["lon"][0] + dlon / 2
        j = 0
        while lon < box["lon"][1]:
            cells.append({"id": f"cell_{i:02d}_{j:02d}", "lat": round(lat, 4), "lon": round(lon, 4),
                          "radius_km": CELL_KM / 2})
            lon += dlon
            j += 1
        lat += dlat
        i += 1
    return cells


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default="negev_sinai_jordan", choices=list(REGIONS))
    parser.add_argument("--limit", type=int, help="only the first N squares (for testing)")
    parser.add_argument("--workers", type=int, default=16, help="squares measured at the same time")
    args = parser.parse_args()

    import ee
    ee.Initialize(project=os.environ.get("EE_PROJECT"))

    ensure_dirs()
    cells = grid(args.region)
    if args.limit:
        # spread the test squares across the region instead of taking one corner
        step = max(1, len(cells) // args.limit)
        cells = cells[::step][:args.limit]
    print(f"{args.region}: measuring {len(cells)} squares of {CELL_KM} x {CELL_KM} km ...", flush=True)

    def measure(cell):
        for attempt in range(3):  # Earth Engine sometimes refuses when busy; retry
            try:
                row = site_features(ee, cell)
                row.update(lat=cell["lat"], lon=cell["lon"])
                return row
            except Exception as e:
                last = e
                time.sleep(2 * (attempt + 1))
        raise last

    rows, failed, start = [], 0, time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(measure, c): c for c in cells}
        for n, fut in enumerate(as_completed(futures), 1):
            try:
                rows.append(fut.result())
            except Exception as e:
                failed += 1
                print(f"  {futures[fut]['id']} FAILED: {str(e)[:120]}")
            if n % 25 == 0 or n == len(cells):
                print(f"  {n}/{len(cells)} done ({time.time() - start:.0f} s)", flush=True)

    df = pd.DataFrame(rows)
    land = df.dropna(subset=["bare_fraction", "temp_swing_K", "slope_mean_deg"]) if len(df) else df
    out = RAW / f"scan_{args.region}.csv"
    land.to_csv(out, index=False)
    print(f"Saved {out}: {len(land)} land squares ({len(df) - len(land)} sea or no data, {failed} failed)")


if __name__ == "__main__":
    main()
