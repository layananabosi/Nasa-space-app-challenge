"""Stage 4 - AFS score, sub-scores, Gap Index and confidence ranges -> data/processed/scores.csv

AFS (Analog Fitness Score), per feature j, Earth site e, Mars target t, profile m:

    s_j(e,t)    = 1 - |x_ej - x_tj| / max_e' |x_e'j - x_tj|      (relative to the other Earth sites)
    AFS_m(e,t)  = 100 * sum_j w_mj s_j(e,t) / sum_j w_mj

Gap Index (absolute distance, 0 = identical, 100 = as far apart as anything in our data):

    gap_j(e,t)  = |x_ej - x_tj| / (max - min of feature j over ALL places, Earth + Mars)
    Gap(e,t)    = 100 * mean_j gap_j

Confidence range: AFS recomputed 500 times with weights drawn around the profile weights
(Dirichlet), reported as the 5th-95th percentile.
"""
import numpy as np
import pandas as pd

from .common import PROCESSED, load_missions, read_features
from .constraints import run as run_constraints

N_BOOT = 500
CONCENTRATION = 20  # higher = weights stay closer to the chosen ones
RNG = np.random.default_rng(42)


def subscores(earth, target, feats):
    """s_j for every Earth site vs one target. NaN where either side is missing."""
    diff = (earth[feats] - target[feats]).abs()
    worst = diff.max(axis=0).replace(0, np.nan)
    s = 1 - diff / worst
    return s.fillna(1.0).where(diff.notna())


def weighted(s, w):
    """Weighted mean over available features, renormalizing weights per row."""
    mask = s.notna().astype(float)
    num = (s.fillna(0) * w).sum(axis=1)
    den = (mask * w).sum(axis=1).replace(0, np.nan)
    return 100 * num / den


def run(features=None):
    df = features if features is not None else read_features()
    for c in df.columns:
        if c not in ("id", "name", "world", "type"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
    earth = df[df["world"] == "earth"].set_index("id")
    mars = df[df["world"] == "mars"].set_index("id")
    eligible = run_constraints(df).set_index(["profile", "id"])

    rows = []
    for pid, prof in load_missions().items():
        feats = list(prof["weights"])
        w = pd.Series(prof["weights"], dtype=float)
        w = w / w.sum()
        span = (df[feats].max() - df[feats].min()).replace(0, np.nan)

        for tid in prof["targets"]:
            if tid not in mars.index:
                print(f"  skip {pid}/{tid}: target not in features.csv")
                continue
            t = mars.loc[tid]
            s = subscores(earth, t, feats)
            afs = weighted(s, w)

            boot = np.column_stack([
                weighted(s, pd.Series(RNG.dirichlet(w.values * CONCENTRATION * len(w)), index=feats))
                for _ in range(N_BOOT)
            ])
            gap = 100 * ((earth[feats] - t[feats]).abs() / span).mean(axis=1)

            for eid in earth.index:
                el = eligible.loc[(pid, eid)]
                row = {
                    "profile": pid, "target": tid, "id": eid,
                    "name": earth.at[eid, "name"], "type": earth.at[eid, "type"],
                    "lat": earth.at[eid, "lat"], "lon": earth.at[eid, "lon"],
                    "afs": afs[eid],
                    "afs_low": np.nanpercentile(boot[earth.index.get_loc(eid)], 5),
                    "afs_high": np.nanpercentile(boot[earth.index.get_loc(eid)], 95),
                    "gap_index": gap[eid],
                    "eligible": bool(el["eligible"]), "failed": el["failed"],
                }
                row.update({f"s_{f}": s.at[eid, f] for f in feats})
                rows.append(row)

    out = pd.DataFrame(rows).sort_values(["profile", "target", "afs"], ascending=[True, True, False])
    out.to_csv(PROCESSED / "scores.csv", index=False)
    return out


if __name__ == "__main__":
    res = run()
    top = res[res["eligible"]].groupby(["profile", "target"]).head(3)
    print(top[["profile", "target", "name", "afs", "afs_low", "afs_high", "gap_index"]].round(1).to_string(index=False))
