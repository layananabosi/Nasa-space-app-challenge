"""Stage 2 - merge Earth + Mars + literature values -> data/processed/features.csv

One row per place (Earth candidates and Mars targets), same columns, same units.

    python -m src.features            # from data/raw/earth_raw.csv + mars_raw.csv
    python -m src.features --sample   # use the FAKE sample table, to build the map early
"""
import argparse
import shutil

import pandas as pd

from .common import FEATURES, ID_COLS, PROCESSED, RAW, SAMPLE, ensure_dirs, load_sites


def site_rows(sites, world):
    rows = []
    for s in sites:
        row = {
            "id": s["id"], "name": s["name"], "world": world,
            "type": s.get("type", "target"), "lat": s["lat"], "lon": s["lon"],
        }
        row.update({k: v for k, v in (s.get("manual") or {}).items()})
        rows.append(row)
    return pd.DataFrame(rows)


def build():
    cfg = load_sites()
    earth = site_rows(cfg["candidates"], "earth").merge(
        pd.read_csv(RAW / "earth_raw.csv"), on="id", how="left")
    mars = site_rows(cfg["targets"], "mars").merge(
        pd.read_csv(RAW / "mars_raw.csv"), on="id", how="left")

    # Mars has no rain and no plants
    mars["aridity"] = 0.0
    mars["bare_fraction"] = 1.0

    df = pd.concat([earth, mars], ignore_index=True)
    for col in FEATURES:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[ID_COLS + FEATURES]

    empty = df[FEATURES].isna().sum()
    if empty.any():
        print("Missing values per feature (scoring will skip them per pair):")
        print(empty[empty > 0].to_string())
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true", help="use the FAKE sample features")
    args = parser.parse_args()

    ensure_dirs()
    out = PROCESSED / "features.csv"
    if args.sample:
        shutil.copy(SAMPLE / "features_FAKE_sample.csv", out)
        print(f"!!! Using FAKE sample data -> {out}. Never present these numbers.")
        return
    df = build()
    df.to_csv(out, index=False)
    print(f"Saved {out} ({len(df)} rows)")


if __name__ == "__main__":
    main()
