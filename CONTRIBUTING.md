# How we work

Two people, 36 hours, one branch (`main`). Tasks live in [Issues](../../issues), each assigned to one of us.

## Every time

1. `git pull` before you start working.
2. Commit small and often. Push right away so the other person has your work.
3. `python run_all.py --sample` must still run before you push.
4. Finishing an issue? Put `Closes #<number>` in the commit message, and the issue closes when you push.

## Who touches what (avoids conflicts)

| Area | Owner |
| --- | --- |
| `src/ingest_mars.py`, Mars targets in `config/sites.yaml`, `config/gaps.yaml` | Mia |
| `src/ingest_earth.py`, `src/export_site.py`, Earth candidates in `config/sites.yaml` | [your name] |
| `config/missions.yaml`, `src/score.py`, `src/constraints.py`, `src/validate.py` | together, one person types |

## Generated files

`data/processed/`, `figures/` and `docs/` are produced by `run_all.py`.
**Only one person runs `run_all.py` and commits these folders.** If both do, every push conflicts.

## Commits

Short, present tense, what changed: `Add MOLA slope and roughness for Mars targets`.
