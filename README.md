# AnaloGraph

**Decision support for Mars analog missions.** AnaloGraph turns open NASA and partner-agency data into a mission brief: for a given mission and Mars target, it recommends where on Earth to practice, explains why, shows which known analogs were rejected, and states honestly what Earth cannot simulate.

Built for the [2026 NASA Space Apps Challenge](https://www.spaceappschallenge.org/2026/), challenge *Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars*. See [CHALLENGE.md](CHALLENGE.md).

> **Status:** in progress during the hackathon (Nov 14–15, 2026). Results on the site are **fake sample data** until the real pipeline run.

## The problem

Mission teams test equipment and methods at terrestrial analogs (Atacama, Haughton Crater, Death Valley) before they fly, but these sites are chosen largely by experience, and their similarity to specific Mars targets is not well characterized.

## Our approach

For each **mission profile** (ice drilling, landing and rover traverse, habitat, astrobiology) and each **Mars target** (Jezero, Gale, Meridiani Planum, Elysium Planitia, Arcadia Planitia, Deuteronilus Mensae):

1. **Constraints first.** Pass/fail rules per mission (e.g. ice drilling needs ground ice), the way landing-site selection starts from engineering limits.
2. **Analog Fitness Score (AFS, 0–100).** Each Earth site is compared with the target on physical features measured the same way on both worlds, relative to all other Earth candidates:

   ```
   s_j(e,t)   = 1 - |x_ej - x_tj| / max_e' |x_e'j - x_tj|
   AFS_m(e,t) = 100 * Σ_j w_mj s_j(e,t) / Σ_j w_mj
   ```
3. **Gap Index (0–100).** The absolute distance that remains, plus a fixed list of environmental gaps no Earth site closes (gravity, pressure, radiation, magnetic field).
4. **Confidence range.** AFS recomputed 500 times with perturbed weights; we report the 5th–95th percentile.
5. **Validation.** Known analogs (positive controls) must outrank clearly non-Mars-like sites (negative controls). We report the share of correctly ordered pairs.
6. **Mission brief.** A web page per profile and target: top 3 sites, why, weakest match, rejected sites with the failed rule, gaps, sources.

### Features (same unit on Earth and Mars)

| Feature | Earth source | Mars source |
| --- | --- | --- |
| Mean and 90th-percentile slope, local roughness, relief (at ~463 m) | Copernicus DEM GLO-30 | MGS MOLA DEM 463 m |
| Day–night surface temperature swing, coldest night | MODIS MOD11A2 LST | Literature / Mars Climate Database |
| Aridity (precipitation / potential evapotranspiration) | TerraClimate | 0 (no precipitation) |
| Bare ground fraction | ESA WorldCover v200 | 1 (no vegetation) |
| Ground ice (0/1) | Literature (permafrost sites) | SWIM ice maps, literature |

## Pipeline

| Stage | Script | Output |
| --- | --- | --- |
| 0 Config | `config/*.yaml` | sites, mission profiles, gaps |
| 1a Earth ingest | `src/ingest_earth.py` (Google Earth Engine) | `data/raw/earth_raw.csv` |
| 1b Mars ingest | `src/ingest_mars.py` (MOLA DEM) | `data/raw/mars_raw.csv` |
| 2 Features | `src/features.py` | `data/processed/features.csv` |
| 3 Constraints | `src/constraints.py` | `data/processed/eligible.csv` |
| 4 Scoring | `src/score.py` | `data/processed/scores.csv` |
| 5 Validation | `src/validate.py` | `data/processed/validation.csv`, `figures/` |
| 6 Briefs and maps | `src/export_site.py` | `docs/` (website) |

## Quick start

```bash
pip install -r requirements.txt

# 1. Try the full pipeline on FAKE sample data (no downloads needed)
python run_all.py --sample
# open docs/index.html

# 2. Real data
earthengine authenticate
EE_PROJECT=<your-gcp-project> python -m src.ingest_earth
python -m src.ingest_mars --dem data/raw/<MOLA_DEM_463m>.tif
python run_all.py
```

Website: GitHub **Settings → Pages → Deploy from branch → `main` / `docs`**.

## Repository layout

```
analograph/
├── config/          sites.yaml, missions.yaml, gaps.yaml
├── src/             one script per pipeline stage
├── data/raw/        downloads (git-ignored)
├── data/processed/  pipeline outputs
├── data/sample/     FAKE sample features for testing only
├── figures/         charts for the slides
├── docs/            generated website (GitHub Pages)
├── run_all.py
├── CHALLENGE.md     the challenge and how we answer it
└── CONTRIBUTING.md  how we work (branches, pull requests)
```

## Limitations

- No Earth site matches Mars in absolute terms; AFS ranks Earth sites *against each other*. The Gap Index and the gaps table make the remaining distance explicit.
- Orbital and global datasets are coarse (~0.5–4 km); a site box is 20 × 20 km.
- Mars temperatures and ground-ice values come from the literature, not from the same instrument as Earth.
- Weights and thresholds are expert choices; the confidence range shows how sensitive the ranking is to them.

## Data sources

NASA and partner resources listed by the challenge:
[NASA Earthdata Search](https://search.earthdata.nasa.gov/) ·
[NASA Worldview](https://worldview.earthdata.nasa.gov/) ·
[NASA Planetary Data System](https://pds.nasa.gov/) ·
[LRO data (PDS Geosciences)](https://pds-geosciences.wustl.edu/missions/lro/) ·
[Copernicus Data Space Ecosystem (ESA)](https://dataspace.copernicus.eu/) ·
[JAXA G-Portal](https://gportal.jaxa.jp/gpr/index/index)

Datasets used (TODO: add exact versions and access dates):
- Copernicus DEM GLO-30 (ESA), via Google Earth Engine
- MODIS Terra Land Surface Temperature MOD11A2 v6.1 (NASA LP DAAC), via Google Earth Engine
- TerraClimate (Abatzoglou et al., 2018), via Google Earth Engine
- ESA WorldCover 10 m v200
- Mars Global Surveyor MOLA DEM 463 m (NASA / USGS Astrogeology)
- Subsurface Water Ice Mapping (SWIM) project maps

Software: Python, NumPy, pandas, SciPy, rasterio, Matplotlib, folium / Leaflet, Google Earth Engine.

## References

- Foucher F. et al. (2021). Definition and use of functional analogues in planetary exploration. *Planetary and Space Science* 197, 105162.
- Morgan G.A. et al. (2021). Availability of subsurface water-ice resources in the northern mid-latitudes of Mars. *Nature Astronomy* 5, 230–236.
- Hassler D.M. et al. (2014). Mars' surface radiation environment measured with the Mars Science Laboratory's Curiosity rover. *Science* 343, 1244797.
- Johnson C.L. et al. (2020). Crustal and time-varying magnetic fields at the InSight landing site on Mars. *Nature Geoscience* 13, 199–204.
- D-MARS, Desert Mars Analog Ramon Station, Makhtesh Ramon, Israel.

## Team

**ML Mappers**: Mia Anabosi, [your name]

Tasks are tracked in [Issues](../../issues). Workflow: [CONTRIBUTING.md](CONTRIBUTING.md).

## Use of AI tools

We used an AI assistant (Claude) for planning, code scaffolding and documentation. All data choices, thresholds, results and conclusions were reviewed by the team.

## License

MIT, see [LICENSE](LICENSE).
