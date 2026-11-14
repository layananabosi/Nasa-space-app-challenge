"""Stage 1b - Mars topography from the MOLA DEM -> data/raw/mars_raw.csv

Input: the MGS MOLA global DEM at 463 m (GeoTIFF, from USGS Astrogeology), or a
cropped GeoTIFF per target exported from Mars Trek. Put it in data/raw/ (it is git-ignored).

    python -m src.ingest_mars --dem data/raw/Mars_MGS_MOLA_DEM_mosaic_global_463m.tif

Computes the SAME topography features as the Earth side:
slope_mean_deg, slope_p90_deg, roughness_m (3x3 local std), relief_m (p95 - p5).

Temperature and ground ice for Mars come from the literature (sites.yaml -> manual),
not from this script.
"""
import argparse
import math

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import from_bounds
from scipy.ndimage import uniform_filter

from .common import RAW, ensure_dirs, load_sites

MARS_RADIUS_M = 3_396_190  # sphere used by the USGS MOLA mosaic


def lonlat_to_xy(lon, lat, crs):
    """Raster coordinates for a lon/lat. Handles geographic or equirectangular (meters) rasters."""
    if crs is None or crs.is_geographic:
        return lon, lat
    return MARS_RADIUS_M * math.radians(lon), MARS_RADIUS_M * math.radians(lat)


def topo_features(src, site):
    lat, lon, r_km = site["lat"], site["lon"], site["radius_km"]
    dlat = math.degrees(r_km * 1000 / MARS_RADIUS_M)
    dlon = dlat / max(math.cos(math.radians(lat)), 0.05)

    x0, y0 = lonlat_to_xy(lon - dlon, lat - dlat, src.crs)
    x1, y1 = lonlat_to_xy(lon + dlon, lat + dlat, src.crs)
    window = from_bounds(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), src.transform)
    z = src.read(1, window=window, masked=True).astype("float64").filled(np.nan)
    if z.size == 0 or np.all(np.isnan(z)):
        raise ValueError("empty window: check the coordinates and the DEM extent")

    # pixel size on the ground, in meters
    px, py = abs(src.transform.a), abs(src.transform.e)
    if src.crs is None or src.crs.is_geographic:
        px = math.radians(px) * MARS_RADIUS_M
        py = math.radians(py) * MARS_RADIUS_M
    px *= math.cos(math.radians(lat))  # equirectangular stretch away from the equator

    dz_dy, dz_dx = np.gradient(z, py, px)
    slope = np.degrees(np.arctan(np.hypot(dz_dx, dz_dy)))

    mean = uniform_filter(z, size=3)
    rough = np.sqrt(np.clip(uniform_filter(z * z, size=3) - mean * mean, 0, None))

    return {
        "id": site["id"],
        "slope_mean_deg": float(np.nanmean(slope)),
        "slope_p90_deg": float(np.nanpercentile(slope, 90)),
        "roughness_m": float(np.nanmean(rough)),
        "relief_m": float(np.nanpercentile(z, 95) - np.nanpercentile(z, 5)),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dem", required=True, help="path to the MOLA DEM GeoTIFF")
    args = parser.parse_args()

    ensure_dirs()
    rows = []
    with rasterio.open(args.dem) as src:
        for t in load_sites()["targets"]:
            print(f"Mars: {t['id']} ...", flush=True)
            try:
                rows.append(topo_features(src, t))
            except Exception as e:
                print(f"  FAILED: {e}")
    out = RAW / "mars_raw.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"Saved {out} ({len(rows)} targets)")


if __name__ == "__main__":
    main()
