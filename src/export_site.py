"""Stage 6 - mission briefs + maps as a static website -> docs/

docs/index.html                      landing page: validation + every mission x target
docs/briefs/<profile>__<target>.html the mission brief (top 3, why, gaps, rejected, sources)
docs/maps/<profile>__<target>.html   interactive map embedded in the brief

GitHub Pages: Settings -> Pages -> Deploy from branch -> main, folder /docs.
The briefs open straight from the disk. The maps load Leaflet and map tiles from the
internet, so for a room without internet, keep screenshots of the maps in the slides.
"""
import math
import shutil
from html import escape

import folium
import pandas as pd

from .common import FIGURES, PROCESSED, SITE, load_gaps, load_missions, load_sites

TEAM = "Layan Anabosi and Mia Anabosi"
SOURCES = ("NASA MODIS land surface temperature, NASA MGS MOLA elevation, ESA Copernicus DEM, "
           "ESA WorldCover, TerraClimate precipitation, Mars Climate Database, NASA SWIM ice maps")

PRETTY = {
    "slope_mean_deg": "mean slope", "slope_p90_deg": "steep slopes", "roughness_m": "roughness",
    "relief_m": "relief", "temp_swing_K": "day-night temperature swing", "temp_min_K": "cold nights",
    "aridity": "dryness", "bare_fraction": "bare ground", "ground_ice": "ground ice",
}
TYPE_LABEL = {"positive": "Known analog", "candidate": "Our candidate", "negative": "Negative control"}

# Score ramp for the maps: butterscotch, brighter = closer match
RAMP = [(75, "#f2c46d"), (55, "#c08a3e"), (0, "#6e5536")]
REJECTED = "#5c6475"

FONTS = ("<link rel='preconnect' href='https://fonts.googleapis.com'>"
         "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
         "<link href='https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,300..800&display=swap' "
         "rel='stylesheet'>")

CSS = """
:root{
  --night:#141823; --panel:#1b2130; --raised:#232a3b; --line:#2e3648;
  --regolith:#ebe5d9; --dust:#a3a9b8; --faint:#6f7789;
  --butter:#f2c46d; --earth:#78aee6; --control:#5c6475;
  --w-ex:125%;
}
*{box-sizing:border-box}
html{background:var(--night)}
body{margin:0;background:var(--night);color:var(--regolith);
  font-family:'Archivo',system-ui,-apple-system,'Segoe UI',sans-serif;font-size:16px;line-height:1.55;
  font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}
main{max-width:1060px;margin:0 auto;padding:40px 20px 80px}
a{color:var(--butter);text-underline-offset:3px}
a:focus-visible{outline:2px solid var(--butter);outline-offset:3px;border-radius:2px}
p{max-width:68ch}
.muted{color:var(--dust)}
.small{font-size:14px}

/* masthead */
.mast{display:flex;justify-content:space-between;align-items:baseline;gap:16px;flex-wrap:wrap;
  padding-bottom:18px;border-bottom:1px solid var(--line)}
.wordmark{font-stretch:var(--w-ex);font-weight:750;font-size:20px;letter-spacing:-.01em;color:var(--regolith);text-decoration:none}
.wordmark span{color:var(--butter)}
.mast .who{color:var(--dust);font-size:14px}

/* type scale */
h1{font-stretch:var(--w-ex);font-weight:780;font-size:clamp(34px,6.2vw,68px);line-height:1.02;
  letter-spacing:-.025em;margin:48px 0 18px;max-width:16ch}
h2{font-stretch:var(--w-ex);font-weight:700;font-size:22px;letter-spacing:-.01em;margin:64px 0 8px}
h3{font-weight:650;font-size:18px;margin:0 0 4px}
.lede{font-size:19px;color:var(--dust);max-width:60ch}

/* validation */
.versus{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--line);border:1px solid var(--line);
  border-radius:14px;overflow:hidden;margin-top:18px}
.versus > div{background:var(--panel);padding:24px 24px 22px}
.versus .big{font-stretch:var(--w-ex);font-weight:780;font-size:clamp(44px,7vw,72px);line-height:1;letter-spacing:-.03em}
.versus .base .big{color:var(--dust)}
.versus .ours .big{color:var(--butter)}
.versus .what{font-weight:650;margin-top:10px}
.meter{height:8px;background:var(--raised);border-radius:99px;margin-top:16px;position:relative}
.meter i{position:absolute;inset:0 auto 0 0;border-radius:99px;background:var(--dust)}
.ours .meter i{background:var(--butter)}
.meter b{position:absolute;top:-4px;bottom:-4px;width:1px;background:var(--faint)}

/* missions on the landing page */
.mission{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.35fr);gap:28px;padding:28px 0;
  border-top:1px solid var(--line)}
.mission:first-of-type{border-top:0}
.mission h3{font-stretch:var(--w-ex);font-size:21px;font-weight:720}
.targets{list-style:none;margin:0;padding:0}
.targets li{border-bottom:1px solid var(--line)}
.targets li:last-child{border-bottom:0}
.targets a{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:4px 16px;padding:12px 4px;
  color:var(--regolith);text-decoration:none}
.targets a:hover{background:var(--panel)}
.targets .t{font-weight:600}
.targets .auc{color:var(--dust);font-size:14px;text-align:right}
.targets .pick{grid-column:1/-1;color:var(--dust);font-size:14px}
.targets .pick strong{color:var(--butter);font-weight:600}

/* brief: the match */
.crumb{font-size:14px;margin-top:22px;display:inline-block}
.kicker{color:var(--dust);font-size:15px;margin:36px 0 0}
.brief h1{margin-top:6px;max-width:20ch}
.ranked{list-style:none;margin:20px 0 0;padding:0;counter-reset:rank}
.ranked li{display:grid;grid-template-columns:64px minmax(0,1fr) 170px;gap:8px 22px;align-items:start;
  padding:24px 0;border-top:1px solid var(--line)}
.ranked .no{font-stretch:var(--w-ex);font-weight:300;font-size:44px;line-height:1;color:var(--faint)}
.ranked li:first-child .no{color:var(--butter);font-weight:700}
.ranked h3{font-size:22px;font-weight:680}
.tag{font-size:13px;margin-left:8px;padding:2px 9px;border-radius:99px;vertical-align:3px;
  border:1px solid currentColor;white-space:nowrap;display:inline-block}
.tag.positive{color:var(--earth)}.tag.candidate{color:var(--butter)}.tag.negative{color:var(--dust)}
.ranked dl{display:grid;grid-template-columns:auto 1fr;gap:4px 14px;margin:12px 0 0;font-size:15px}
.ranked dt{color:var(--dust)}.ranked dd{margin:0}
.ranked .score{text-align:right}
.ranked .score .big{font-stretch:var(--w-ex);font-weight:760;font-size:48px;line-height:1;letter-spacing:-.03em}
.ranked .score .unit{color:var(--dust);font-size:13px}
.range{height:6px;background:var(--raised);border-radius:99px;position:relative;margin-top:12px}
.range i{position:absolute;top:0;bottom:0;background:var(--butter);opacity:.45;border-radius:99px}
.range b{position:absolute;top:-4px;bottom:-4px;width:3px;margin-left:-1px;background:var(--butter);border-radius:2px}

/* map */
.mapwrap{border:1px solid var(--line);border-radius:14px;overflow:hidden;background:var(--panel)}
iframe{display:block;width:100%;height:460px;border:0;background:var(--panel)}
.legend{display:flex;flex-wrap:wrap;gap:8px 22px;padding:12px 16px;font-size:14px;color:var(--dust);
  border-top:1px solid var(--line)}
.legend span{display:inline-flex;align-items:center;gap:8px}
.dot{width:12px;height:12px;border-radius:50%;display:inline-block}
.dot.hollow{background:transparent;border:2px solid var(--control)}

/* tables */
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;border:1px solid var(--line);border-radius:14px}
table{width:100%;border-collapse:collapse;font-size:15px;min-width:560px}
th,td{text-align:left;padding:11px 14px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}
th{color:var(--dust);font-weight:600;font-size:14px;background:var(--panel)}
td.num{white-space:nowrap}
.bar{display:inline-block;height:6px;border-radius:99px;background:var(--butter);vertical-align:middle;
  margin-right:10px;opacity:.85}
.who-type{white-space:nowrap}
.who-type .dot{width:9px;height:9px;margin-right:7px}

.question{font-size:clamp(30px,4.8vw,54px);max-width:21ch;margin-top:10px}
.note{margin-top:72px;padding:28px 30px;background:var(--panel);border-left:3px solid var(--butter);border-radius:4px 14px 14px 4px}
.note h2{margin-top:0}
.note p{font-size:17px}
.note .sign{font-stretch:var(--w-ex);font-weight:700;color:var(--butter);margin-bottom:0}

/* figure + footer */
figure{margin:18px 0 0}
figure img{display:block;max-width:100%;border-radius:12px;background:#fff}
figcaption{color:var(--dust);font-size:14px;margin-top:8px}
footer{margin-top:72px;padding-top:20px;border-top:1px solid var(--line);color:var(--dust);font-size:14px}
footer p{max-width:none}

@media (max-width:760px){
  main{padding:28px 16px 64px}
  .versus{grid-template-columns:1fr}
  .mission{grid-template-columns:1fr;gap:10px}
  .ranked li{grid-template-columns:44px minmax(0,1fr)}
  .ranked .no{font-size:32px}
  .ranked .score{grid-column:2;text-align:left}
  iframe{height:360px}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
"""

DOT = {"positive": "var(--earth)", "candidate": "var(--butter)", "negative": "var(--control)"}


def page(title, body, sample):
    banner = ("<p class='small' style='border:1px solid var(--butter);color:var(--butter);padding:10px 14px;"
              "border-radius:10px;max-width:none'><b>Fake sample data.</b> These numbers are placeholders "
              "for building the site. Do not present them.</p>") if sample else ""
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<meta name='color-scheme' content='dark'>"
            f"<title>{escape(title)}</title>{FONTS}<style>{CSS}</style></head>"
            f"<body><main>{banner}{body}"
            f"<footer><p>Made by {escape(TEAM)} for the 2026 NASA Space Apps Challenge.</p>"
            f"<p>Data: {escape(SOURCES)}. Method and sources: "
            f"<a href='https://github.com/layananabosi/Nasa-space-app-challenge'>GitHub repository</a>.</p>"
            f"</footer></main></body></html>")


def mast(root):
    return (f"<header class='mast'><a class='wordmark' href='{root}index.html'>Analo<span>Graph</span></a>"
            f"<span class='who'>{escape(TEAM)}</span></header>")


def fmt(x, nd=0):
    return "n/a" if pd.isna(x) else f"{x:.{nd}f}"


def ramp(score):
    return next(c for lim, c in RAMP if score >= lim)


def reasons(row, feats, best=True, n=2):
    s = pd.Series({f: row.get(f"s_{f}") for f in feats}).dropna()
    s = s.sort_values(ascending=not best).head(n)
    return ", ".join(PRETTY.get(f, f) for f in s.index) or "n/a"


def dark_base(m):
    """Esri dark gray basemap: free, no API key (CartoDB tiles now need one)."""
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        attr="Esri, HERE, Garmin, OpenStreetMap contributors", name="Dark map", max_zoom=16).add_to(m)


def site_map(g, path):
    m = folium.Map(location=[20, 10], zoom_start=2, tiles=None)
    dark_base(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery", name="Satellite").add_to(m)
    for _, r in g.sort_values("afs").iterrows():
        ok = bool(r["eligible"])
        color = ramp(r["afs"]) if ok else REJECTED
        pop = (f"<b>{escape(r['name'])}</b><br>Score {fmt(r['afs'])} "
               f"(range {fmt(r['afs_low'])} to {fmt(r['afs_high'])})"
               f"<br>Gap Index {fmt(r['gap_index'])}<br>{TYPE_LABEL.get(r['type'], r['type'])}"
               + ("" if ok else f"<br><i>Rejected: {escape(r['failed'])}</i>"))
        folium.CircleMarker([r["lat"], r["lon"]], radius=8 if ok else 6, color=color, weight=2,
                            fill=ok, fill_color=color, fill_opacity=0.9,
                            popup=folium.Popup(pop, max_width=260), tooltip=r["name"]).add_to(m)
    folium.LayerControl().add_to(m)
    m.save(str(path))


def range_bar(r):
    lo, hi, mid = (max(0, min(100, v)) for v in (r["afs_low"], r["afs_high"], r["afs"]))
    return f"<div class='range' aria-hidden='true'><i style='left:{lo}%;width:{hi - lo}%'></i><b style='left:{mid}%'></b></div>"


def type_cell(t):
    return f"<span class='who-type'><span class='dot' style='background:{DOT.get(t, 'var(--dust)')}'></span>{TYPE_LABEL.get(t, t)}</span>"


def brief(pid, prof, tid, target, g, gaps, sample, fig_name):
    feats = list(prof["weights"])
    ok = g[g["eligible"]].sort_values("afs", ascending=False)
    rejected = g[~g["eligible"] & g["type"].isin(["positive", "candidate"])].sort_values("afs", ascending=False)
    best = ok.iloc[0]["name"] if len(ok) else None

    top = "".join(
        f"<li><div class='no'>{i}</div><div><h3>{escape(r['name'])}"
        f"<span class='tag {r['type']}'>{TYPE_LABEL.get(r['type'], r['type'])}</span></h3>"
        f"<dl><dt>Matches best on</dt><dd>{reasons(r, feats)}</dd>"
        f"<dt>Weakest match</dt><dd>{reasons(r, feats, best=False)}</dd>"
        f"<dt>Gap Index</dt><dd>{fmt(r['gap_index'])} of 100, lower is closer to Mars</dd></dl></div>"
        f"<div class='score'><div class='big'>{fmt(r['afs'])}</div>"
        f"<div class='unit'>score, range {fmt(r['afs_low'])} to {fmt(r['afs_high'])}</div>{range_bar(r)}</div></li>"
        for i, (_, r) in enumerate(ok.head(3).iterrows(), 1)) or "<li><p>No site passed this mission's rules.</p></li>"

    ranking = "".join(
        f"<tr><td class='num'>{i}</td><td>{escape(r['name'])}</td><td>{type_cell(r['type'])}</td>"
        f"<td class='num'><span class='bar' style='width:{max(2, r['afs']) * 0.9:.0f}px'></span>{fmt(r['afs'])}"
        f" <span class='muted small'>({fmt(r['afs_low'])} to {fmt(r['afs_high'])})</span></td>"
        f"<td class='num'>{fmt(r['gap_index'])}</td></tr>"
        for i, (_, r) in enumerate(ok.iterrows(), 1))
    rej = "".join(f"<tr><td>{escape(r['name'])}</td><td>{type_cell(r['type'])}</td>"
                  f"<td>{escape(r['failed'])}</td></tr>" for _, r in rejected.iterrows()) \
        or "<tr><td colspan='3' class='muted'>No known analog or candidate was rejected.</td></tr>"
    gap_rows = "".join(f"<tr><td>{escape(x['factor'])}</td><td>{escape(x['earth'])}</td>"
                       f"<td>{escape(x['mars'])}</td><td>{escape(x['impact'])}</td>"
                       f"<td class='muted small'>{escape(x['source'])}</td></tr>" for x in gaps)
    rules = "; ".join(f"{PRETTY.get(c['feature'], c['feature'])} {c['op']} {c['value']}"
                      for c in prof.get("constraints") or []) or "none"
    fig = (f"<h2>Validation</h2><figure><img src='../figures/{fig_name}' alt='Bar chart of scores for every "
           f"Earth site, known analogs compared with negative controls'><figcaption>Known analogs should score "
           f"above the negative controls. Whiskers show the score range when weights change.</figcaption></figure>"
           ) if fig_name else ""
    headline = (f"Practice at {escape(best)}" if best else "No Earth site passes")

    body = f"""{mast('../')}
<div class='brief'>
<a class='crumb' href='../index.html'>All missions</a>
<p class='kicker'>{escape(prof['label'])} for {escape(target['name'])}, the {escape(str(target.get('mission', '')))} site</p>
<h1>{headline}</h1>
<p class='lede'>{escape(prof['question'])}</p>

<h2>Recommended Earth sites</h2>
<p class='muted small'>Ranked among sites that pass this mission's rules. Scores compare Earth sites with
each other for this target, from 0 to 100.</p>
<ol class='ranked'>{top}</ol>

<h2>Map</h2>
<div class='mapwrap'><iframe src='../maps/{pid}__{tid}.html' title='Map of all Earth sites scored for this mission'></iframe>
<div class='legend'><span><i class='dot' style='background:{RAMP[0][1]}'></i>Score 75 or more</span>
<span><i class='dot' style='background:{RAMP[1][1]}'></i>55 to 74</span>
<span><i class='dot' style='background:{RAMP[2][1]}'></i>Below 55</span>
<span><i class='dot hollow'></i>Rejected by a mission rule</span></div></div>

<h2>Full ranking</h2>
<div class='scroll'><table><tr><th>Rank</th><th>Site</th><th>Type</th><th>Score (range)</th><th>Gap Index</th></tr>{ranking}</table></div>

<h2>Rejected and why</h2>
<p class='muted small'>Mission rules: {escape(rules)}. Negative controls are left out of this list.</p>
<div class='scroll'><table><tr><th>Site</th><th>Type</th><th>Rule it failed</th></tr>{rej}</table></div>

<h2>What Earth cannot simulate</h2>
<div class='scroll'><table><tr><th>Factor</th><th>Earth</th><th>Mars</th><th>What it means for the test</th><th>Source</th></tr>{gap_rows}</table></div>
{fig}
<h2>How to read this brief</h2>
<p class='muted'>The score ranks Earth sites against each other for this target and mission, using only
the properties that matter for the test. The range shows how much it moves when the weights change. The
Gap Index is the distance that remains in absolute terms: no place on Earth is Mars.</p>
</div>"""
    return page(f"{prof['label']} for {target['name']}: AnaloGraph", body, sample)


def run(sample=False):
    scores = pd.read_csv(PROCESSED / "scores.csv")
    validation = pd.read_csv(PROCESSED / "validation.csv")
    profiles, gaps = load_missions(), load_gaps()
    sites = load_sites()
    targets = {t["id"]: t for t in sites["targets"]}

    for d in ("briefs", "maps", "figures"):
        (SITE / d).mkdir(parents=True, exist_ok=True)
    for f in FIGURES.glob("validation_*.png"):
        shutil.copy(f, SITE / "figures" / f.name)

    missions = []
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
            ok = g[g["eligible"]].sort_values("afs", ascending=False)
            pick = (f"Top pick <strong>{escape(ok.iloc[0]['name'])}</strong>, score {fmt(ok.iloc[0]['afs'])}"
                    if len(ok) else "No site passes the rules")
            items.append(f"<li><a href='briefs/{pid}__{tid}.html'><span class='t'>{escape(targets[tid]['name'])}"
                         f"</span><span class='auc'>AUC {sep}</span><span class='pick'>{pick}</span></a></li>")
        missions.append(f"<section class='mission'><div><h3>{escape(prof['label'])}</h3>"
                        f"<p class='muted'>{escape(prof['question'])}</p></div>"
                        f"<ul class='targets'>{''.join(items)}</ul></section>")

    ov = validation[validation["profile"] == "overall"]
    ms = validation[validation["profile"] != "overall"]
    n_earth, n_mars = len(sites["candidates"]), len(sites["targets"])
    validation_block = ""
    if len(ov):
        b, o = ov["separation"].mean(), ms["separation"].mean()
        validation_block = f"""
<h2>Can you trust the rankings?</h2>
<p class='muted'>The method is never told which sites are famous Mars analogs. If it works, those should
still score above places that are clearly not Mars-like, such as rainforest and farmland. AUC is the share
of those pairs ranked correctly: 1.00 is perfect, 0.50 is a coin flip.</p>
<div class='versus'>
<div class='base'><div class='big'>{b:.2f}</div><div class='what'>Every feature counts equally</div>
<div class='muted small'>Naive baseline, no mission rules</div>
<div class='meter'><i style='width:{b * 100:.0f}%'></i><b style='left:50%'></b></div></div>
<div class='ours'><div class='big'>{o:.2f}</div><div class='what'>Mission-specific scoring</div>
<div class='muted small'>{int((ms['separation'] >= 0.95).sum())} of {len(ms)} mission targets at 0.95 or above</div>
<div class='meter'><i style='width:{o * 100:.0f}%'></i><b style='left:50%'></b></div></div>
</div>
<p class='muted small'>The thin line on each bar marks a coin flip. Weights were set before seeing any results.
Landing tests score lowest, by design: on terrain alone, flat farmland resembles flat Mars plains.</p>"""

    scan_path = PROCESSED / "scan_scores.csv"
    scan = pd.read_csv(scan_path) if scan_path.exists() else None
    if scan is not None and not scan.empty:
        scan_page(scan, profiles, targets, sample)

    body = f"""{mast('')}
<p class='kicker'>Built by two sisters over one weekend, for NASA Space Apps 2026</p>
<h1 class='question'>If you had to rehearse a Mars mission tomorrow, where on Earth would you go?</h1>
<p class='lede'>Rovers and crews rehearse in deserts, craters and polar valleys long before they fly, and most of
those places were chosen by experience. We compared {n_earth} of them with {n_mars} sites on Mars, using open NASA
and ESA data, to find out which place fits which mission, and why.</p>
{validation_block}
{scan_teaser(scan)}
<h2>Mission briefs</h2>
<p class='muted'>Each brief recommends three Earth sites, explains the match, lists which known analogs
fail the mission's rules, and shows what no Earth site can simulate.</p>
{''.join(missions)}
<section class='note'>
<h2>How our weekend went</h2>
<p>We started on Saturday morning with a list of famous Mars analogs and one question: are they really the best
places to practice?</p>
<p>By the afternoon, we had accidentally parked Curiosity on top of a 5 km mountain. We had typed in the middle of
Gale Crater instead of the spot where the rover actually landed, and the middle of Gale Crater is Mount Sharp.
We had also moved InSight about 1,100 km across Mars. Both are now back where they landed.</p>
<p>Then our first results told us that a Dutch farm field is a lot like Mars. On terrain alone, it is: both are
extremely flat. So the landing briefs now check for bare ground too, and landing still has the lowest score in our
validation. We kept it that way, because it is true.</p>
<p>Along the way, a Google form asked whether our project fights climate change. It does not. It looks for Mars on
Earth.</p>
<p>Some answers we did not see coming. The best match for the plains where Opportunity and InSight landed is
Salar de Uyuni in Bolivia, one of the flattest places on Earth. For practice drives near Jezero and Gale, the top
matches were all in the Negev. And without being told it was famous, our method put the Atacama Desert first for
life detection at every Mars target. We are taking that as a good sign.</p>
<p>No place on Earth has Mars's thin air, its cold nights or its radiation. We wrote those limits on every brief
instead of leaving them out.</p>
<p class='sign'>Layan and Mia</p>
</section>"""
    (SITE / "index.html").write_text(page("AnaloGraph: Mars analog sites on Earth", body, sample), encoding="utf-8")
    print(f"Site written to {SITE}/index.html")


SCAN_REGION = "the Negev, Sinai and southern Jordan"


def scan_teaser(sc):
    """Short block for the landing page; empty when no scan has been run."""
    if sc is None or sc.empty:
        return ""
    n = sc["id"].nunique()
    beats = sc[sc["eligible"] & sc["new"] & (sc["afs"] > sc["best_site_afs"])]
    n_new = beats["id"].nunique()
    line = (f"{n_new} squares outside our starting list score higher than the best of our 23 sites "
            f"for at least one mission." if n_new else
            "No square outside our starting list beats our 23 sites, but several come close.")
    return (f"<h2>Searching beyond the famous sites</h2>"
            f"<p class='muted'>Ranking famous sites is not enough, so we split {SCAN_REGION} into {n} squares of "
            f"20 by 20 km and scored every one of them. {line}</p>"
            f"<p><a href='scan.html'>See the regional search</a></p>")


def scan_page(sc, profiles, targets, sample):
    cell_deg = 20 / 111.0
    m = folium.Map(location=[sc["lat"].mean(), sc["lon"].mean()], zoom_start=7, tiles=None)
    dark_base(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery", name="Satellite").add_to(m)
    sections, first = [], True
    for pid, prof in profiles.items():
        for tid in prof["targets"]:
            g = sc[(sc["profile"] == pid) & (sc["target"] == tid)]
            if g.empty:
                continue
            layer = folium.FeatureGroup(name=f"{prof['label']}: {targets[tid]['name']}", show=first)
            first = False
            for r in g.itertuples():
                dlon = cell_deg / math.cos(math.radians(r.lat))
                color = ramp(r.afs) if r.eligible else REJECTED
                pop = (f"<b>{r.lat:.2f}, {r.lon:.2f}</b><br>Score {fmt(r.afs)}, Gap Index {fmt(r.gap_index)}"
                       f"<br>{fmt(r.nearest_km)} km from {escape(r.nearest_site)}"
                       + ("<br><b>New to our list</b>" if r.new else "")
                       + ("" if r.eligible else f"<br><i>Rejected: {escape(r.failed)}</i>"))
                folium.Rectangle([[r.lat - cell_deg / 2, r.lon - dlon / 2], [r.lat + cell_deg / 2, r.lon + dlon / 2]],
                                 color=color, weight=0.5, fill=True, fill_color=color,
                                 fill_opacity=0.65 if r.eligible else 0.15,
                                 popup=folium.Popup(pop, max_width=260)).add_to(layer)
            layer.add_to(m)

            ok = g[g["eligible"]].head(5)
            best = g["best_site_afs"].iloc[0]
            beat = int((g["eligible"] & (g["afs"] > best)).sum()) if pd.notna(best) else 0
            rows = "".join(
                f"<tr><td class='num'><a href='https://www.google.com/maps/@{r.lat:.4f},{r.lon:.4f},11z/data=!3m1!1e3'>"
                f"{r.lat:.2f}, {r.lon:.2f}</a></td>"
                f"<td class='num'><span class='bar' style='width:{max(2, r.afs) * 0.9:.0f}px'></span>{fmt(r.afs)}</td>"
                f"<td class='num'>{fmt(r.gap_index)}</td>"
                f"<td>{fmt(r.nearest_km)} km from {escape(r.nearest_site)}"
                + (" <span class='tag candidate'>New to our list</span>" if r.new else "") + "</td></tr>"
                for r in ok.itertuples()) or "<tr><td colspan='4' class='muted'>No square passes this mission's rules.</td></tr>"
            sections.append(
                f"<h3 style='margin-top:36px'>{escape(prof['label'])} for {escape(targets[tid]['name'])}</h3>"
                f"<p class='muted small'>Best of our 23 sites: {fmt(best)}. Squares in the region that score higher: "
                f"{beat}.</p>"
                f"<div class='scroll'><table><tr><th>Square (opens satellite view)</th><th>Score</th>"
                f"<th>Gap Index</th><th>Nearest site on our list</th></tr>{rows}</table></div>")
    folium.LayerControl(collapsed=False).add_to(m)
    m.save(str(SITE / "maps" / "scan.html"))

    n = sc["id"].nunique()
    body = f"""{mast('')}
<a class='crumb' href='index.html'>All missions</a>
<p class='kicker'>Regional search, {n} squares of 20 by 20 km</p>
<h1 class='question'>What if the best place to practice is not on anyone's list yet?</h1>
<p class='lede'>We split {SCAN_REGION} into a grid and measured every square with exactly the same NASA and ESA
data and the same mission rules as our 23 sites. Squares more than 30 km from every site we started with are
marked "new to our list". Some may already be known to geologists; they are places worth checking.</p>
<h2>Map</h2>
<div class='mapwrap'><iframe src='maps/scan.html' title='Map of scored squares, one layer per mission and Mars site'></iframe>
<div class='legend'><span><i class='dot' style='background:{RAMP[0][1]}'></i>Score 75 or more</span>
<span><i class='dot' style='background:{RAMP[1][1]}'></i>55 to 74</span>
<span><i class='dot' style='background:{RAMP[2][1]}'></i>Below 55</span>
<span><i class='dot hollow'></i>Rejected by a mission rule</span></div></div>
<p class='muted small'>Use the layer menu on the map to switch missions and Mars sites. Ice drilling is left out:
there is no ground ice in this region.</p>
<h2>Best squares for each mission</h2>
<p class='muted'>Scores use the same 0 to 100 scale as the briefs, so a square scoring above the best of our 23
sites is a better match than any place we started with.</p>
{''.join(sections)}
<h2>How to read this</h2>
<p class='muted'>A square is an average over 400 square kilometres, so a high score points to an area worth a closer
look, not a finished answer. Cities, farms and roads inside a square lower its bare-ground value.</p>"""
    (SITE / "scan.html").write_text(page("Regional search: AnaloGraph", body, sample), encoding="utf-8")
    print(f"Scan page written to {SITE}/scan.html")


if __name__ == "__main__":
    run()