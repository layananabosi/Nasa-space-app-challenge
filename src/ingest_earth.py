"""Stage 1a - Earth features from Google Earth Engine -> data/raw/earth_raw.csv

Run once you have Earth Engine access:
    earthengine authenticate
    EE_PROJECT=your-gcp-project python -m src.ingest_earth

Datasets (cite all of them in the README):
    Copernicus DEM GLO-30        COPERNICUS/DEM/GLO30         elevation
    MODIS Terra LST 8-day        MODIS/061/MOD11A2            day/night surface temperature
    TerraClimate                 IDAHO_EPSCOR/TERRACLIMATE    precipitation
    ESA WorldCover 10 m v200     ESA/WorldCover/v200          land cover (bare / snow & ice)

!!! Test on ONE site first (python -m src.ingest_earth --only svalbard)
!!! and check the band names and scale factors in the Earth Engine catalog.

Changes (14 Nov):
  - Topography is reprojected to a local UTM zone, so pixels are square 463 m
    at every latitude (EPSG:4326 pixels shrink east-west toward the poles).
  - temp_swing_K is the day-minus-night difference inside each 8-day composite,
    then averaged. Averaging day and night separately mixed polar summer days
    with polar winter nights.
  - "aridity" is now annual precipitation in mm (Mars = 0). P/PET calls cold
    polar deserts "humid" because PET is near zero there.
  - bare_fraction is computed over land only (WorldCover water, class 80, masked).
"""
import argparse
import os

import pandas as pd

from .common import RAW, ensure_dirs, load_sites

SCALE = 463   # meters; matches the MOLA 463 m Mars DEM so slopes are comparable
YEAR = 2023   # one full year of temperature and climate data


def utm_crs(lat, lon):
    """Local metric projection (UTM zone) so pixels are square at any latitude."""
    zone = int((lon + 180) // 6) + 1
    return f"EPSG:{(32600 if lat >= 0 else 32700) + zone}"


def site_features(ee, site):
    region = ee.Geometry.Point([site["lon"], site["lat"]]).buffer(site["radius_km"] * 1000).bounds()
    crs = utm_crs(site["lat"], site["lon"])

    # --- topography, resampled to the Mars DEM resolution, square pixels ---
    dem_col = ee.ImageCollection("COPERNICUS/DEM/GLO30").filterBounds(region).select("DEM")
    dem = (dem_col.mosaic()
           .setDefaultProjection(dem_col.first().projection())
           .reduceResolution(ee.Reducer.mean(), maxPixels=1024)
           .reproject(crs=crs, scale=SCALE))
    slope = ee.Terrain.slope(dem)
    rough = dem.reduceNeighborhood(ee.Reducer.stdDev(), ee.Kernel.square(1))  # 3x3 window

    topo = ee.Image.cat(slope.rename("slope"), dem.rename("elev"), rough.rename("rough")).reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.percentile([5, 90, 95]), sharedInputs=True),
        geometry=region, crs=crs, scale=SCALE, maxPixels=1e9)

    # --- surface temperature (MODIS Terra LST, ~10:30 day / ~22:30 night, scale 0.02 -> K) ---
    lst = ee.ImageCollection("MODIS/061/MOD11A2").filterDate(f"{YEAR}-01-01", f"{YEAR + 1}-01-01")
    # day - night inside each composite; a pixel counts only when both exist
    swing = lst.map(lambda i: i.select("LST_Day_1km").multiply(0.02)
                    .subtract(i.select("LST_Night_1km").multiply(0.02))).mean()
    # coldest 8-day night mean of the year
    night_min = lst.select("LST_Night_1km").min().multiply(0.02)
    temp = ee.Image.cat(swing.rename("swing"), night_min.rename("tmin")).reduceRegion(
        reducer=ee.Reducer.mean(), geometry=region, scale=1000, maxPixels=1e9)

    # --- dryness: annual precipitation in mm (TerraClimate pr, monthly mm) ---
    tc = ee.ImageCollection("IDAHO_EPSCOR/TERRACLIMATE").filterDate(f"{YEAR}-01-01", f"{YEAR + 1}-01-01")
    precip = tc.select("pr").sum().rename("precip").reduceRegion(
        reducer=ee.Reducer.mean(), geometry=region, scale=4000, maxPixels=1e9)

    # --- bare ground (WorldCover class 60 = bare/sparse vegetation, 70 = snow and ice) ---
    # computed over LAND only: water (class 80: sea, lakes, ponds) is masked out, since water is not vegetation
    lc = ee.ImageCollection("ESA/WorldCover/v200").first().select("Map")
    bare = lc.eq(60).Or(lc.eq(70)).updateMask(lc.neq(80)).rename("bare").reduceRegion(
        reducer=ee.Reducer.mean(), geometry=region, scale=100, maxPixels=1e9)

    t, c, p, b = (x.getInfo() for x in (topo, temp, precip, bare))
    return {
        "id": site["id"],
        "slope_mean_deg": t.get("slope_mean"),
        "slope_p90_deg": t.get("slope_p90"),
        "roughness_m": t.get("rough_mean"),
        "relief_m": (t["elev_p95"] - t["elev_p5"]) if t.get("elev_p95") is not None else None,
        "temp_swing_K": c.get("swing"),
        "temp_min_K": c.get("tmin"),
        "aridity": p.get("precip"),   # annual precipitation, mm (column name kept for the other scripts)
        "bare_fraction": b.get("bare"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="run a single site id (for testing)")
    args = parser.parse_args()

    import ee
    ee.Initialize(project=os.environ.get("EE_PROJECT"))

    ensure_dirs()
    sites = load_sites()["candidates"]
    if args.only:
        sites = [s for s in sites if s["id"] == args.only]

    rows = []
    for s in sites:
        print(f"Earth: {s['id']} ...", flush=True)
        try:
            row = site_features(ee, s)
            print("  " + ", ".join(f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}"
                                   for k, v in row.items() if k != "id"), flush=True)
            rows.append(row)
        except Exception as e:  # keep going; one bad site should not stop the run
            print(f"  FAILED: {e}")
    out = RAW / "earth_raw.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"Saved {out} ({len(rows)} sites)")


if __name__ == "__main__":
    main()
