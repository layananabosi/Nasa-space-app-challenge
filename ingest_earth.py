"""Stage 1a - Earth features from Google Earth Engine -> data/raw/earth_raw.csv

Run once you have Earth Engine access:
    earthengine authenticate
    EE_PROJECT=your-gcp-project python -m src.ingest_earth

Datasets (cite all of them in the README):
    Copernicus DEM GLO-30        COPERNICUS/DEM/GLO30         elevation
    MODIS Terra LST 8-day        MODIS/061/MOD11A2            day/night surface temperature
    TerraClimate                 IDAHO_EPSCOR/TERRACLIMATE    precipitation, potential evapotranspiration
    ESA WorldCover 10 m v200     ESA/WorldCover/v200          land cover (bare / snow & ice)

!!! Test on ONE site first (python -m src.ingest_earth --only makhtesh_ramon)
!!! and check the band names and scale factors in the Earth Engine catalog.
"""
import argparse
import os

import pandas as pd

from .common import RAW, ensure_dirs, load_sites

SCALE = 463   # meters; matches the MOLA 463 m Mars DEM so slopes are comparable
YEAR = 2023   # one full year of temperature and climate data


def site_features(ee, site):
    region = ee.Geometry.Point([site["lon"], site["lat"]]).buffer(site["radius_km"] * 1000).bounds()

    # --- topography, resampled to the Mars DEM resolution ---
    dem_col = ee.ImageCollection("COPERNICUS/DEM/GLO30").filterBounds(region).select("DEM")
    dem = (dem_col.mosaic()
           .setDefaultProjection(dem_col.first().projection())
           .reduceResolution(ee.Reducer.mean(), maxPixels=1024)
           .reproject(crs="EPSG:4326", scale=SCALE))
    slope = ee.Terrain.slope(dem)
    rough = dem.reduceNeighborhood(ee.Reducer.stdDev(), ee.Kernel.square(1))  # 3x3 window

    topo = ee.Image.cat(slope.rename("slope"), dem.rename("elev"), rough.rename("rough")).reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.percentile([5, 90, 95]), sharedInputs=True),
        geometry=region, scale=SCALE, maxPixels=1e9)

    # --- surface temperature (MODIS LST, scale factor 0.02 -> Kelvin) ---
    lst = ee.ImageCollection("MODIS/061/MOD11A2").filterDate(f"{YEAR}-01-01", f"{YEAR + 1}-01-01")
    day = lst.select("LST_Day_1km").mean().multiply(0.02)
    night = lst.select("LST_Night_1km").mean().multiply(0.02)
    night_min = lst.select("LST_Night_1km").min().multiply(0.02)
    temp = ee.Image.cat(day.subtract(night).rename("swing"), night_min.rename("tmin")).reduceRegion(
        reducer=ee.Reducer.mean(), geometry=region, scale=1000, maxPixels=1e9)

    # --- dryness (TerraClimate: pr in mm, pet scale 0.1 mm) ---
    tc = ee.ImageCollection("IDAHO_EPSCOR/TERRACLIMATE").filterDate(f"{YEAR}-01-01", f"{YEAR + 1}-01-01")
    pr = tc.select("pr").sum()
    pet = tc.select("pet").sum().multiply(0.1)
    arid = pr.divide(pet).rename("aridity").reduceRegion(
        reducer=ee.Reducer.mean(), geometry=region, scale=4000, maxPixels=1e9)

    # --- bare ground (WorldCover class 60 = bare/sparse vegetation, 70 = snow and ice) ---
    lc = ee.ImageCollection("ESA/WorldCover/v200").first().select("Map")
    bare = lc.eq(60).Or(lc.eq(70)).rename("bare").reduceRegion(
        reducer=ee.Reducer.mean(), geometry=region, scale=100, maxPixels=1e9)

    t, c, a, b = (x.getInfo() for x in (topo, temp, arid, bare))
    return {
        "id": site["id"],
        "slope_mean_deg": t.get("slope_mean"),
        "slope_p90_deg": t.get("slope_p90"),
        "roughness_m": t.get("rough_mean"),
        "relief_m": (t["elev_p95"] - t["elev_p5"]) if t.get("elev_p95") is not None else None,
        "temp_swing_K": c.get("swing"),
        "temp_min_K": c.get("tmin"),
        "aridity": a.get("aridity"),
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
            rows.append(site_features(ee, s))
        except Exception as e:  # keep going; one bad site should not stop the run
            print(f"  FAILED: {e}")
    out = RAW / "earth_raw.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"Saved {out} ({len(rows)} sites)")


if __name__ == "__main__":
    main()
