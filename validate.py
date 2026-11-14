"""Stage 5 - does the method work? -> data/processed/validation.csv + figures/validation_*.png

Check: known analogs (positive controls) should score above negative controls.
Metric: the share of (positive, negative) pairs where the positive scores higher.
1.0 = perfect separation, 0.5 = no better than chance. Same idea as a ROC AUC.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .common import FIGURES, PROCESSED, load_missions

COLORS = {"positive": "#2a6fdb", "candidate": "#e8890c", "negative": "#9a9a9a"}
LABELS = {"positive": "Known analog", "candidate": "Our candidate", "negative": "Negative control"}


def separation(group):
    pos = group.loc[group["type"] == "positive", "afs"].dropna().values
    neg = group.loc[group["type"] == "negative", "afs"].dropna().values
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    wins = (pos[:, None] > neg[None, :]).mean() + 0.5 * (pos[:, None] == neg[None, :]).mean()
    return float(wins)


def plot(group, profile_label, target):
    g = group.sort_values("afs")
    fig, ax = plt.subplots(figsize=(8, max(4, 0.28 * len(g))))
    y = np.arange(len(g))
    ax.barh(y, g["afs"], color=[COLORS[t] for t in g["type"]], height=0.7)
    ax.errorbar(g["afs"], y, xerr=[g["afs"] - g["afs_low"], g["afs_high"] - g["afs"]],
                fmt="none", ecolor="#333333", elinewidth=0.8, capsize=2)
    ax.set_yticks(y, g["name"], fontsize=8)
    ax.set_xlim(0, 100)
    ax.set_xlabel(f"AFS vs {target} (0-100), bars = 5-95% range")
    ax.set_title(f"{profile_label}: known analogs should rank above controls", fontsize=11)
    for t, c in COLORS.items():
        ax.barh([], [], color=c, label=LABELS[t])
    ax.legend(loc="lower right", fontsize=8, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    path = FIGURES / f"validation_{profile_label.lower().replace(' ', '_')}_{target}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def run(scores=None):
    scores = scores if scores is not None else pd.read_csv(PROCESSED / "scores.csv")
    profiles = load_missions()
    rows = []
    for (pid, tid), g in scores.groupby(["profile", "target"]):
        rows.append({"profile": pid, "target": tid, "separation": separation(g)})
    res = pd.DataFrame(rows)
    res.to_csv(PROCESSED / "validation.csv", index=False)

    # one headline figure per profile: its first target
    for pid, prof in profiles.items():
        g = scores[(scores["profile"] == pid) & (scores["target"] == prof["targets"][0])]
        if len(g):
            plot(g, prof["label"], prof["targets"][0])
    return res


if __name__ == "__main__":
    print(run().round(2).to_string(index=False))
