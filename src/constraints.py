"""Stage 3 - pass/fail constraints per mission profile -> data/processed/eligible.csv

Like NASA landing-site selection: engineering limits come first, science ranking second.
A site that fails a rule is still shown in the brief, with the rule it failed.
"""
import operator

import pandas as pd

from .common import PROCESSED, load_missions, read_features

OPS = {"<=": operator.le, ">=": operator.ge, "<": operator.lt, ">": operator.gt, "==": operator.eq}


def check_site(row, constraints):
    failed = []
    for rule in constraints or []:
        value = row.get(rule["feature"])
        if pd.isna(value):
            failed.append(f"missing {rule['feature']}")
        elif not OPS[rule["op"]](value, rule["value"]):
            failed.append(rule.get("reason") or f"{rule['feature']} {rule['op']} {rule['value']}")
    return failed


def run(features=None):
    df = features if features is not None else read_features()
    earth = df[df["world"] == "earth"]
    rows = []
    for pid, prof in load_missions().items():
        for _, site in earth.iterrows():
            failed = check_site(site, prof.get("constraints"))
            rows.append({"profile": pid, "id": site["id"],
                         "eligible": not failed, "failed": "; ".join(failed)})
    out = pd.DataFrame(rows)
    out.to_csv(PROCESSED / "eligible.csv", index=False)
    return out


if __name__ == "__main__":
    res = run()
    print(res.groupby("profile")["eligible"].sum().rename("eligible sites").to_string())
