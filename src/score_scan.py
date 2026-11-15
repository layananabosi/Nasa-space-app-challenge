"""Score the regional scan -> data/processed/scan_scores.csv

Every grid square is scored with the same mission rules and weights as the 23 sites.
To keep scores comparable with the briefs, the 0-100 scale is anchored on the 23 sites:
a square scores 100 on a feature if it matches the Mars target exactly, and 0 if it is
as far away as the worst of the 23 sites (anything further is clipped to 0).

Ice drilling is skipped: there is no ground ice in this region.
"""
import math

import numpy as np
import pandas as pd

from .common import FEATURES, PROCESSED, RAW, load_missions, load_sites, read_features
from .constraints import check_site

SKIP_PROFILES = {"ice_drilling"}
NEW_KM = 30  # a square further than this from all 23 sites on our list counts as "new to our list"


def km(lat1, lon1, lat2, lon2):
    p = math.pi / 180
    a = (math.sin((lat2 - lat1) * p / 2) ** 2
         + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(a))


def nearest_site(lat, lon, sites):
    best = min(sites, key=lambda s: km(lat, lon, s["lat"], s["lon"]))
    return best["name"], km(lat, lon, best["lat"], best["lon"])


def run(region="negev_sinai_jordan"):
    path = RAW / f"scan_{region}.csv"
    if not path.exists():
        return None
    scan = pd.read_csv(path)
    scan["ground_ice"] = 0  # hot desert: no permafrost
    feats_all = read_features()
    for c in FEATURES:
        feats_all[c] = pd.to_numeric(feats_all[c], errors="coerce")
        scan[c] = pd.to_numeric(scan[c], errors="coerce")
    earth = feats_all[feats_all["world"] == "earth"]
    mars = feats_all[feats_all["world"] == "mars"].set_index("id")
    sites = load_sites()["candidates"]

    near = [nearest_site(r.lat, r.lon, sites) for r in scan.itertuples()]
    scan["nearest_site"] = [n for n, _ in near]
    scan["nearest_km"] = [d for _, d in near]

    rows = []
    for pid, prof in load_missions().items():
        if pid in SKIP_PROFILES:
            continue
        feats = list(prof["weights"])
        w = pd.Series(prof["weights"], dtype=float)
        span = (feats_all[feats].max() - feats_all[feats].min()).replace(0, np.nan)
        failed = [check_site(r, prof.get("constraints")) for _, r in scan.iterrows()]
        for tid in prof["targets"]:
            if tid not in mars.index:
                continue
            t = mars.loc[tid, feats].astype(float)
            worst = (earth[feats] - t).abs().max().replace(0, np.nan)
            diff = (scan[feats] - t).abs()
            s = (1 - diff / worst).clip(lower=0).fillna(1.0).where(diff.notna())
            mask = s.notna().astype(float)
            afs = 100 * (s.fillna(0) * w).sum(axis=1) / (mask * w).sum(axis=1).replace(0, np.nan)
            gap = 100 * (diff / span).mean(axis=1)
            best_site = None
            sc = PROCESSED / "scores.csv"
            if sc.exists():
                ref = pd.read_csv(sc).query("profile == @pid and target == @tid and eligible")
                best_site = ref["afs"].max() if len(ref) else None
            for k, r in scan.iterrows():
                rows.append({
                    "profile": pid, "target": tid, "id": r["id"], "lat": r["lat"], "lon": r["lon"],
                    "afs": afs[k], "gap_index": gap[k], "eligible": not failed[k],
                    "failed": "; ".join(failed[k]), "nearest_site": r["nearest_site"],
                    "nearest_km": r["nearest_km"], "new": r["nearest_km"] > NEW_KM,
                    "best_site_afs": best_site,
                    **{f"s_{f}": s.at[k, f] for f in feats},
                })
    out = pd.DataFrame(rows).sort_values(["profile", "target", "afs"], ascending=[True, True, False])
    out.to_csv(PROCESSED / "scan_scores.csv", index=False)
    return out


if __name__ == "__main__":
    res = run()
    if res is None:
        print("No scan data yet. Run: python -m src.scan_region")
    else:
        for (p, t), g in res[res["eligible"]].groupby(["profile", "target"]):
            top = g.head(3)
            print(f"{p:13} {t:16}", " | ".join(f"{r.lat:.2f},{r.lon:.2f} {r.afs:.0f}"
                                                 f"{' NEW' if r.new else ''}" for r in top.itertuples()))
