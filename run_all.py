"""Run the whole AnaloGraph pipeline after ingest.

    python run_all.py            # real data: needs data/raw/earth_raw.csv and mars_raw.csv
    python run_all.py --sample   # FAKE sample data, to build and test the site early

Ingest is run separately because it needs Earth Engine login and the Mars DEM:
    python -m src.ingest_earth
    python -m src.ingest_mars --dem data/raw/<mola_dem>.tif
"""
import argparse
import subprocess
import sys

from src import export_site, score, score_scan, validate
from src.common import ensure_dirs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true", help="use the FAKE sample features")
    args = parser.parse_args()

    ensure_dirs()
    cmd = [sys.executable, "-m", "src.features"] + (["--sample"] if args.sample else [])
    subprocess.run(cmd, check=True)

    print("\n[3-4] constraints + scoring")
    score.run()
    print("[5] validation")
    print(validate.run().round(2).to_string(index=False))
    if score_scan.run() is not None:
        print("[5b] regional scan scored")
    print("[6] mission briefs + maps")
    export_site.run(sample=args.sample)
    print("\nDone. Open docs/index.html in a browser.")


if __name__ == "__main__":
    main()
