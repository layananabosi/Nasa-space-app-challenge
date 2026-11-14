"""Shared paths, config loading and the feature list used by every stage."""
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
SAMPLE = ROOT / "data" / "sample"
FIGURES = ROOT / "figures"
SITE = ROOT / "docs"  # GitHub Pages serves this folder

# The one contract between the two halves of the team:
# every feature exists for Earth AND Mars, in the SAME unit.
FEATURES = [
    "slope_mean_deg",  # mean slope at ~463 m resolution (degrees)
    "slope_p90_deg",   # 90th percentile slope (degrees)
    "roughness_m",     # mean local std of elevation in a 3x3 window (m)
    "relief_m",        # elevation p95 - p5 inside the box (m)
    "temp_swing_K",    # mean day minus mean night surface temperature (K)
    "temp_min_K",      # coldest night surface temperature (K)
    "aridity",         # yearly precipitation in mm (Mars = 0); name kept for compatibility
    "bare_fraction",   # share of bare or non-vegetated ground, 0..1 (Mars = 1)
    "ground_ice",      # 1 = ground ice / permafrost present, 0 = not (literature)
]

ID_COLS = ["id", "name", "world", "type", "lat", "lon"]


def load_yaml(name):
    with open(CONFIG / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_sites():
    return load_yaml("sites.yaml")


def load_missions():
    return load_yaml("missions.yaml")["profiles"]


def load_gaps():
    return load_yaml("gaps.yaml")["gaps"]


def read_features(path=None):
    path = path or PROCESSED / "features.csv"
    df = pd.read_csv(path)
    missing = [c for c in ID_COLS + FEATURES if c not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing columns: {missing}")
    return df


def ensure_dirs():
    for d in (RAW, PROCESSED, FIGURES, SITE):
        d.mkdir(parents=True, exist_ok=True)
