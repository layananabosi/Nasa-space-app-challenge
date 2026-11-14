"""Stage 6 - mission briefs + maps as a static website -> docs/

docs/index.html                      landing page: every profile x target
docs/briefs/<profile>__<target>.html the mission brief (top 3, why, gaps, rejected, sources)
docs/maps/<profile>__<target>.html   interactive map embedded in the brief

GitHub Pages: Settings -> Pages -> Deploy from branch -> main, folder /docs.
The briefs open straight from the disk. The maps load Leaflet and map tiles from the
internet, so for a room without internet, keep screenshots of the maps in the slides.
"""
import shutil
from html import escape

import folium
import pandas as pd

from .common import FIGURES, PROCESSED, SITE, load_gaps, load_missions, load_sites

PRETTY = {
    "slope_mean_deg": "mean slope", "slope_p90_deg": "steep slopes", "roughness_m": "roughness",
    "relief_m": "relief", "temp_swing_K": "day-night temperature swing", "temp_min_K": "cold nights",
    "aridity": "dryness", "bare_fraction": "bare ground", "ground_ice": "ground ice",
}
TYPE_LABEL = {"positive": "known analog", "candidate": "new candidate", "negative": "negative control"}

CSS = """
:root{--bg:#fbfaf7;--fg:#1d1d1b;--muted:#6b6a66;--line:#e2e0da;--card:#ffffff;--accent:#2a6fdb;--warn:#b54708}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--fg:#ecebe7;--muted:#a3a29d;--line:#33322f;--card:#1f1f1d;--accent:#7aa7f0;--warn:#f0a35e}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:960px;margin:0 auto;padding:32px 16px 64px}
h1{font-size:28px;margin:0 0 4px}h2{font-size:18px;margin:36px 0 12px}a{color:var(--accent)}
.muted{color:var(--muted)}.banner{border:1px solid var(--warn);color:var(--warn);padding:10px 14px;border-radius:8px;margin:16px 0}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px}
.score{font-size:30px;font-weight:650}.badge{display:inline-block;font-size:12px;border:1px solid var(--line);border-radius:99px;padding:1px 8px;color:var(--muted)}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:600}iframe{width:100%;height:440px;border:1px solid var(--line);border-radius:10px}
img{max-width:100%;border:1px solid var(--line);border-radius:10px;background:#fff}
"""


def page(title, body, sample):
    banner = ('<div class="banner"><b>FAKE SAMPLE DATA.</b> These numbers are placeholders '
              'for building the site. Do not present them.</div>') if sample else ""
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{escape(title)}</title><style>{CSS}</style></head>"
            f"<body><main>{banner}{body}</main></body></html>")


def fmt(x, nd=0):
    return "n/a" if pd.isna(x) else f"{x:.{nd}f}"


def reasons(row, feats, best=True, n=2):
    s = pd.Series({f: row.get(f"s_{f}") for f in feats}).dropna()
    s = s.sort_values(ascending=not best).head(n)
    return ", ".join(PRETTY.get(f, f) for f in s.index) or "n/a"


def site_map(g, path):
    m = folium.Map(location=[20, 10], zoom_start=2, tiles="OpenStreetMap")
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery", name="Satellite").add_to(m)
    for _, r in g.iterrows():
        if not r["eligible"]:
            color = "#9a9a9a"
        elif r["afs"] >= 75:
            color = "#1a9850"
        elif r["afs"] >= 55:
            color = "#e8b10c"
        else:
            color = "#d73027"
        pop = (f"<b>{escape(r['name'])}</b><br>AFS {fmt(r['afs'])} ({fmt(r['afs_low'])}-{fmt(r['afs_high'])})"
               f"<br>Gap Index {fmt(r['gap_index'])}<br>{TYPE_LABEL.get(r['type'], r['type'])}"
               + ("" if r["eligible"] else f"<br><i>Rejected: {escape(r['failed'])}</i>"))
        folium.CircleMarker([r["lat"], r["lon"]], radius=7, color=color, fill=True,
                            fill_opacity=0.9 if r["eligible"] else 0.3,
                            popup=folium.Popup(pop, max_width=260), tooltip=r["name"]).add_to(m)
    folium.LayerControl().add_to(m)
    m.save(str(path))


def brief(pid, prof, tid, target, g, gaps, sample, fig_name):
    feats = list(prof["weights"])
    ok = g[g["eligible"]].sort_values("afs", ascending=False)
    rejected = g[~g["eligible"] & g["type"].isin(["positive", "candidate"])]

    cards = "".join(
        f"<div class='card'><div class='badge'>{escape(TYPE_LABEL.get(r['type'], r['type']))}</div>"
        f"<h3>{i}. {escape(r['name'])}</h3><div class='score'>{fmt(r['afs'])}</div>"
        f"<div class='muted'>AFS, range {fmt(r['afs_low'])}-{fmt(r['afs_high'])}</div>"
        f"<p><b>Why:</b> {reasons(r, feats)}</p>"
        f"<p><b>Weakest match:</b> {reasons(r, feats, best=False)}</p>"
        f"<p><b>Gap Index:</b> {fmt(r['gap_index'])} / 100</p></div>"
        for i, (_, r) in enumerate(ok.head(3).iterrows(), 1)) or "<p>No site passed the constraints.</p>"

    ranking = "".join(
        f"<tr><td>{i}</td><td>{escape(r['name'])}</td><td>{TYPE_LABEL.get(r['type'], r['type'])}</td>"
        f"<td>{fmt(r['afs'])} ({fmt(r['afs_low'])}-{fmt(r['afs_high'])})</td><td>{fmt(r['gap_index'])}</td></tr>"
        for i, (_, r) in enumerate(ok.iterrows(), 1))
    rej = "".join(f"<tr><td>{escape(r['name'])}</td><td>{TYPE_LABEL.get(r['type'], r['type'])}</td>"
                  f"<td>{escape(r['failed'])}</td></tr>" for _, r in rejected.iterrows()) \
        or "<tr><td colspan='3'>None</td></tr>"
    gap_rows = "".join(f"<tr><td>{escape(x['factor'])}</td><td>{escape(x['earth'])}</td>"
                       f"<td>{escape(x['mars'])}</td><td>{escape(x['impact'])}</td>"
                       f"<td class='muted'>{escape(x['source'])}</td></tr>" for x in gaps)
    rules = "; ".join(f"{PRETTY.get(c['feature'], c['feature'])} {c['op']} {c['value']}"
                      for c in prof.get("constraints") or []) or "none"
    fig = f"<h2>Validation</h2><img src='../figures/{fig_name}' alt='validation chart'>" if fig_name else ""

    body = f"""
<p class='muted'><a href='../index.html'>AnaloGraph</a> · mission brief</p>
<h1>{escape(prof['label'])} → {escape(target['name'])}</h1>
<p class='muted'>Mars target: {escape(target['name'])} ({escape(str(target.get('mission', '')))})</p>
<p>{escape(prof['question'])}</p>
<h2>Recommended Earth sites</h2><div class='cards'>{cards}</div>
<h2>Map</h2><iframe src='../maps/{pid}__{tid}.html' title='map'></iframe>
<h2>Full ranking (sites that passed the constraints)</h2>
<table><tr><th>#</th><th>Site</th><th>Type</th><th>AFS (5-95%)</th><th>Gap Index</th></tr>{ranking}</table>
<h2>Rejected and why</h2><p class='muted'>Constraints: {escape(rules)}</p>
<table><tr><th>Site</th><th>Type</th><th>Failed rule</th></tr>{rej}</table>
<h2>What Earth cannot simulate</h2>
<table><tr><th>Factor</th><th>Earth</th><th>Mars</th><th>Impact</th><th>Source</th></tr>{gap_rows}</table>
{fig}
<h2>How to read this</h2><p class='muted'>AFS (0-100) ranks Earth sites against each other for this target and
mission. The range shows how much it moves when the weights change. Gap Index (0-100) is the absolute distance
that remains: lower is closer. Method and data sources are in the project README.</p>"""
    return page(f"{prof['label']} → {target['name']}", body, sample)


def run(sample=False):
    scores = pd.read_csv(PROCESSED / "scores.csv")
    validation = pd.read_csv(PROCESSED / "validation.csv")
    profiles, gaps = load_missions(), load_gaps()
    targets = {t["id"]: t for t in load_sites()["targets"]}

    for d in ("briefs", "maps", "figures"):
        (SITE / d).mkdir(parents=True, exist_ok=True)
    for f in FIGURES.glob("validation_*.png"):
        shutil.copy(f, SITE / "figures" / f.name)

    links = []
    for pid, prof in profiles.items():
        items = []
        for tid in prof["targets"]:
            g = scores[(scores["profile"] == pid) & (scores["target"] == tid)]
            if g.empty:
                continue
            fig = f"validation_{prof['label'].lower().replace(' ', '_')}_{tid}.png"
            fig = fig if (SITE / "figures" / fig).exists() else None
            site_map(g, SITE / "maps" / f"{pid}__{tid}.html")
            (SITE / "briefs" / f"{pid}__{tid}.html").write_text(
                brief(pid, prof, tid, targets[tid], g, gaps, sample, fig), encoding="utf-8")
            sep = validation.query("profile == @pid and target == @tid")["separation"]
            sep = fmt(sep.iloc[0], 2) if len(sep) else "n/a"
            items.append(f"<tr><td><a href='briefs/{pid}__{tid}.html'>{escape(targets[tid]['name'])}</a></td>"
                         f"<td>{sep}</td></tr>")
        links.append(f"<div class='card'><h3>{escape(prof['label'])}</h3><p class='muted'>"
                     f"{escape(prof['question'])}</p><table><tr><th>Mars target</th>"
                     f"<th>Validation</th></tr>{''.join(items)}</table></div>")

    body = f"""
<h1>AnaloGraph</h1>
<p class='muted'>Decision support for Mars analog missions · NASA Space Apps 2026</p>
<p>Pick a mission and a Mars target. Each brief recommends where on Earth to practice, explains why,
shows which known analogs were rejected, and states what Earth cannot simulate.</p>
<p class='muted'>Validation = share of (known analog, negative control) pairs ranked correctly. 1.00 is perfect, 0.50 is chance.</p>
<div class='cards'>{''.join(links)}</div>"""
    (SITE / "index.html").write_text(page("AnaloGraph", body, sample), encoding="utf-8")
    print(f"Site written to {SITE}/index.html")


if __name__ == "__main__":
    run()
