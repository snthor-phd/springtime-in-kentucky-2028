#!/usr/bin/env python3
"""Build the Springtime in Kentucky 2028 caravan site from data/*.json.

Edit data/trip.json, data/stops.json, data/decisions.json or data/routes.json, then run:
    python3 build.py
deploy.sh runs this automatically before pushing.
"""
import json, html, datetime as dt
from pathlib import Path

ROOT = Path(__file__).parent
D = lambda f: json.loads((ROOT / "data" / f).read_text())
TRIP, STOPS, DECS, ROUTES = D("trip.json"), D("stops.json"), D("decisions.json"), D("routes.json")
LEGS = ROUTES.get("legs", {})
START = dt.date.fromisoformat(TRIP["start"])
END = dt.date.fromisoformat(TRIP["end"])
FAREWELL = dt.date.fromisoformat(TRIP["farewell"])
FIXED = [dict(f, date=dt.date.fromisoformat(f["date"])) for f in TRIP["fixed"]]
DERBY = next(f for f in FIXED if f["kind"] == "derby")
TOTAL_NIGHTS = (END - START).days + 1          # last caravan night is the end date
TOW_FACTOR = 1.2                               # towing takes ~20% longer than car time
TITLE = TRIP["title"]
e = html.escape


def fmt(d, year=False):
    return d.strftime("%a %b %-d, %Y" if year else "%a %b %-d")


def plural(n, w):
    return f"{n} {w}{'' if n == 1 else 's'}"


def plan():
    """Expand trip stops into dated segments with the drive leg into each stop."""
    segs, day, prev = [], START, "home"
    for sid, n in TRIP["stops"]:
        leg = LEGS.get(f"{prev}-{sid}")
        segs.append(dict(id=sid, nights=n, arrive=day, depart=day + dt.timedelta(n), prev=prev,
                         mi=leg["mi"] if leg else None,
                         tow_h=round(leg["car_h"] * TOW_FACTOR, 1) if leg else None))
        day += dt.timedelta(n)
        prev = sid
    planned = sum(s["nights"] for s in segs)
    leg = LEGS.get(f"{prev}-home") if segs else None
    home = dict(prev=prev, mi=leg["mi"] if leg else None,
                tow_h=round(leg["car_h"] * TOW_FACTOR, 1) if leg else None)
    miles = sum(s["mi"] or 0 for s in segs) + (home["mi"] or 0)
    return dict(segs=segs, planned=planned, open=TOTAL_NIGHTS - planned, home=home, miles=miles,
                legs_known=all(s["mi"] is not None for s in segs) and home["mi"] is not None)


P = plan()


def page(title, body, depth, head_extra="", scripts=""):
    up = "../" * depth
    nav = [("", "Overview"), ("itinerary/", "Itinerary"), ("route-map/", "Route map"),
           ("campgrounds/", "Campgrounds"), ("decisions/", "Decisions")]
    links = "".join(f'<a href="{up}{p}">{e(t)}</a>' for p, t in nav)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<title>{e(title)} — {e(TITLE)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Libre+Caslon+Text:wght@400;700&family=Figtree:ital,wght@0,400;0,500;0,700;1,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{up}assets/css/site.css">{head_extra}
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🌹</text></svg>">
</head><body>
<header class="top"><a class="brand" href="{up}">Springtime in Kentucky <span>2028</span></a><nav>{links}</nav></header>
<main>{body}</main>
<footer>Airstream caravan led by {e(TRIP["leaders"])}. Towing times are estimates (car time + 20%). Campgrounds are candidates until booked.</footer>
{scripts}</body></html>"""


# ---------- signature element: the 23-day calendar strip ----------
def strip_svg():
    days = (FAREWELL - START).days + 1
    W, L, R = 1000, 8, 8
    px = (W - L - R) / days
    out, y0 = [], 40
    for d in range(days):
        date = START + dt.timedelta(d)
        x = L + d * px
        if date.weekday() in (5, 6):
            out.append(f'<rect x="{x:.1f}" y="{y0 - 6}" width="{px:.1f}" height="64" class="st-wknd"/>')
        if date.weekday() == 5 or d == 0:
            out.append(f'<text x="{x + 3:.1f}" y="{y0 - 12}" class="st-date">{date.strftime("%a %b %-d")}</text>')
    # planned stops, then the unplanned remainder
    for s in P["segs"]:
        d0 = (s["arrive"] - START).days
        x, w = L + d0 * px, s["nights"] * px
        name = STOPS[s["id"]]["name"]
        out.append(f'<rect x="{x + 1:.1f}" y="{y0}" width="{w - 2:.1f}" height="30" rx="3" class="st-stop">'
                   f'<title>{e(name)}: {fmt(s["arrive"])} to {fmt(s["depart"])}, {plural(s["nights"], "night")}</title></rect>')
        if len(name) * 6 <= w - 6:
            out.append(f'<text x="{x + w / 2:.1f}" y="{y0 + 20}" text-anchor="middle" class="st-lab">{e(name)}</text>')
    if P["open"] > 0:
        x = L + P["planned"] * px
        w = P["open"] * px
        out.append(f'<rect x="{x + 1:.1f}" y="{y0}" width="{w - 2:.1f}" height="30" rx="3" class="st-open"/>')
        out.append(f'<text x="{x + w / 2:.1f}" y="{y0 + 20}" text-anchor="middle" class="st-openlab">'
                   f'{plural(P["open"], "night")} still to plan</text>')
    # farewell day
    fx = L + (FAREWELL - START).days * px
    out.append(f'<rect x="{fx + 1:.1f}" y="{y0}" width="{px - 2:.1f}" height="30" rx="3" class="st-farewell">'
               f'<title>Farewell, {fmt(FAREWELL)}</title></rect>')
    # fixed events: direct labels below the strip
    for f in FIXED:
        d = (f["date"] - START).days
        cx = L + d * px + px / 2
        cls = "st-derby" if f["kind"] == "derby" else "st-fixed"
        out.append(f'<line x1="{cx:.1f}" y1="{y0 - 6}" x2="{cx:.1f}" y2="{y0 + 44}" class="{cls}-line"/>')
        anchor = "end" if d > days - 4 else "middle"
        out.append(f'<text x="{cx:.1f}" y="{y0 + 58}" text-anchor="{anchor}" class="{cls}-lab">'
                   f'{e(f["label"])}, {f["date"].strftime("%a %b %-d")}</text>')
    H = y0 + 66
    return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Calendar strip of the caravan, '
            f'{fmt(START)} to {fmt(FAREWELL)}" class="strip">{"".join(out)}</svg>')


def index_page():
    derby_day = (DERBY["date"] - START).days + 1
    status = (f"{plural(len(P['segs']), 'stop')} planned, {plural(P['open'], 'night')} still open"
              if P["segs"] else "Stops not chosen yet")
    body = f"""
<section class="hero">
  <p class="dates">{START.strftime("%B %-d")} – {END.strftime("%B %-d")}, 2028 · farewell {FAREWELL.strftime("%B %-d")}</p>
  <h1>Three weeks of Kentucky in spring, with Derby Day on day {derby_day}.</h1>
  <p class="lede">An Airstream caravan led by {e(TRIP["leaders"])}. Bluegrass, bourbon, horse country and the hills — the route is still taking shape.</p>
  <p class="countdown" id="countdown"></p>
</section>
<section class="compare">
  <h2>{TOTAL_NIGHTS} caravan nights; the Derby is the one fixed date</h2>
  <div class="scroll">{strip_svg()}</div>
  <p class="caption">Each column is one day; weekends are shaded. Stops appear here as they're added. Hover or tap a block for dates.</p>
  <table class="facts">
    <tbody>
      <tr><th>Roll in</th><td>{fmt(START, True)}</td></tr>
      <tr><th>Kentucky Derby</th><td>{fmt(DERBY["date"], True)}, {e(DERBY["place"])}</td></tr>
      <tr><th>Last caravan night</th><td>{fmt(END, True)}</td></tr>
      <tr><th>Farewell</th><td>{fmt(FAREWELL, True)}</td></tr>
      <tr><th>Plan so far</th><td>{status}</td></tr>
      <tr><th>Leaders</th><td>{e(TRIP["leaders"])}</td></tr>
    </tbody>
  </table>
</section>
<section class="pages">
  <a href="itinerary/"><h3>Itinerary</h3><p>Day-by-day: dates, drives, things to do.</p></a>
  <a href="route-map/"><h3>Route map</h3><p>Stops and campgrounds on the map, with GPS downloads.</p></a>
  <a href="campgrounds/"><h3>Campgrounds</h3><p>Candidates at every stop and the booking tracker.</p></a>
  <a href="decisions/"><h3>Decisions</h3><p>What's settled and what's still open.</p></a>
</section>"""
    js = f"""<script>
(function(){{var s=new Date("{START.isoformat()}T12:00:00"),n=new Date(),d=Math.round((s-n)/864e5),el=document.getElementById("countdown");
if(d>0)el.textContent=d+" days until we roll out.";else if(d>-{TOTAL_NIGHTS + 1})el.textContent="Day "+(1-d)+" of the caravan.";else el.textContent="Caravan complete.";}})();
</script>"""
    return page("Overview", body, 0, scripts=js)


def drive_text(s):
    frm = STOPS[s["prev"]]["name"] if s["prev"] != "home" else "home"
    if s["mi"] is None:
        return f"From {e(frm)}; mileage TBD"
    return f'{s["mi"]} mi from {e(frm)}, about {s["tow_h"]} h towing'


def itinerary_page():
    items = []
    for i, s in enumerate(P["segs"], 1):
        st = STOPS[s["id"]]
        acts = "".join(f"<li>{e(x)}</li>" for x in st["activities"])
        camps = "; ".join(e(c["name"]) for c in st["campgrounds"]) or "Not chosen yet"
        fixed = "".join(f'<p class="fixedev">{e(f["label"])}, {fmt(f["date"])}</p>' for f in FIXED
                        if s["arrive"] <= f["date"] < s["depart"])
        items.append(f"""<li class="stop">
<div class="when"><span class="n">{i}</span><b>{s['arrive'].strftime('%b %-d')}–{s['depart'].strftime('%b %-d')}</b><span>{plural(s['nights'], 'night')}</span></div>
<div class="what"><h3>{e(st['name'])} <small>{e(st['place'])}</small></h3>
<p class="drive">{drive_text(s)}</p>{fixed}{f"<p>{e(st['blurb'])}</p>" if st['blurb'] else ''}
{f'<ul>{acts}</ul>' if acts else ''}<p class="camp">Campground: {camps}</p></div></li>""")
    if P["open"] > 0:
        first_open = START + dt.timedelta(P["planned"])
        fixed = "".join(f'<p class="fixedev">{e(f["label"])}, {fmt(f["date"])}</p>' for f in FIXED
                        if f["date"] >= first_open and f["kind"] != "farewell")
        items.append(f"""<li class="stop k-open">
<div class="when"><span class="n">…</span><b>{first_open.strftime('%b %-d')}–{(END + dt.timedelta(1)).strftime('%b %-d')}</b><span>{plural(P['open'], 'night')}</span></div>
<div class="what"><h3>Still to plan</h3>{fixed}<p class="drive">Stops get added here as they're chosen.</p></div></li>""")
    items.append(f"""<li class="stop k-farewell"><div class="when"><span class="n">★</span><b>{FAREWELL.strftime('%b %-d')}</b><span>farewell</span></div>
<div class="what"><h3>Farewell</h3><p class="drive">{fmt(FAREWELL, True)}; place to be set.</p></div></li>""")
    lede = (f"{plural(P['planned'], 'night')} planned of {TOTAL_NIGHTS}."
            + (f" {P['miles']:,} towing miles." if P["segs"] and P["legs_known"] else ""))
    body = f'<h1>Itinerary</h1><p class="lede">{lede}</p><ol class="stops">{"".join(items)}</ol>'
    return page("Itinerary", body, 1)


def route_line():
    pts, prev = [], "home"
    order = [s["id"] for s in P["segs"]] + (["home"] if P["segs"] else [])
    for sid in order:
        leg = LEGS.get(f"{prev}-{sid}")
        if leg and leg.get("geom"):
            pts += leg["geom"]
        else:
            pts += [[STOPS[prev]["lat"], STOPS[prev]["lon"]], [STOPS[sid]["lat"], STOPS[sid]["lon"]]]
        prev = sid
    return pts


def route_page():
    data = {"line": route_line(), "stops": [
        dict(name=STOPS[s["id"]]["name"], place=STOPS[s["id"]]["place"],
             dates=f'{s["arrive"].strftime("%b %-d")}–{s["depart"].strftime("%b %-d")}', nights=s["nights"],
             camps=[dict(name=c["name"], lat=c["lat"], lon=c["lon"]) for c in STOPS[s["id"]]["campgrounds"]],
             lat=STOPS[s["id"]]["lat"], lon=STOPS[s["id"]]["lon"]) for s in P["segs"]]}
    dl = ('<p class="downloads">Downloads: <a href="springtime-kentucky-2028.kml" download>KML</a> '
          '<a href="springtime-kentucky-2028.gpx" download>GPX</a></p>'
          '<p class="caption">KML imports into Google My Maps (Create map → Import). GPX loads into most RV GPS units and apps.</p>'
          if P["segs"] else '<p class="caption">No stops yet. Pins, the route and GPS downloads appear once stops are added.</p>')
    body = f'<h1>Route map</h1><div id="map" aria-label="Route map"></div>{dl}'
    head = '\n<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">'
    js = f"""<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script>
var DATA={json.dumps(data, ensure_ascii=False)};
var map=L.map('map',{{scrollWheelZoom:false}});
L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{maxZoom:18,attribution:'&copy; OpenStreetMap contributors'}}).addTo(map);
if(DATA.stops.length){{
 var line=L.polyline(DATA.line,{{color:'#2F5D46',weight:4,opacity:.85}}).addTo(map);
 DATA.stops.forEach(function(s,i){{
  s.camps.forEach(function(c){{L.circleMarker([c.lat,c.lon],{{radius:4,color:'#2F5D46',weight:1,fillColor:'#fff',fillOpacity:1}}).bindTooltip(c.name).addTo(map)}});
  L.circleMarker([s.lat,s.lon],{{radius:8,color:'#fff',weight:2,fillColor:'#2F5D46',fillOpacity:1}})
  .bindPopup('<b>'+(i+1)+'. '+s.name+'</b><br>'+s.place+'<br>'+s.dates+' ('+s.nights+' night'+(s.nights>1?'s':'')+')').addTo(map);}});
 map.fitBounds(line.getBounds(),{{padding:[20,20]}});
}}else{{map.fitBounds([[36.5,-89.6],[39.15,-81.9]]);}}
</script>"""
    return page("Route map", body, 1, head_extra=head, scripts=js)


def kml():
    coords = " ".join(f"{lon},{lat},0" for lat, lon in route_line())
    marks = []
    for i, s in enumerate(P["segs"], 1):
        for c in STOPS[s["id"]]["campgrounds"]:
            marks.append(f'<Placemark><name>{i}. {e(STOPS[s["id"]]["name"])} — {e(c["name"])}</name>'
                         f'<description>{fmt(s["arrive"])} to {fmt(s["depart"])}, {plural(s["nights"], "night")}.</description>'
                         f'<Point><coordinates>{c["lon"]},{c["lat"]},0</coordinates></Point></Placemark>')
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>{e(TITLE)}</name>
<Style id="r"><LineStyle><color>ff465d2f</color><width>4</width></LineStyle></Style>
<Placemark><name>Route</name><styleUrl>#r</styleUrl><LineString><tessellate>1</tessellate><coordinates>{coords}</coordinates></LineString></Placemark>
{''.join(marks)}</Document></kml>"""


def gpx():
    wpts = []
    for i, s in enumerate(P["segs"], 1):
        for c in STOPS[s["id"]]["campgrounds"][:1]:
            wpts.append(f'<wpt lat="{c["lat"]}" lon="{c["lon"]}"><name>{i}. {e(c["name"])}</name>'
                        f'<desc>{e(STOPS[s["id"]]["name"])}, {fmt(s["arrive"])} for {plural(s["nights"], "night")}</desc></wpt>')
    trk = "".join(f'<trkpt lat="{lat}" lon="{lon}"/>' for lat, lon in route_line())
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="springtime-in-kentucky-2028" xmlns="http://www.topografix.com/GPX/1/1">
{''.join(wpts)}<trk><name>{e(TITLE)}</name><trkseg>{trk}</trkseg></trk></gpx>"""


def cell(v):
    return f'<td>{e(v)}</td>' if v else '<td class="todo">Check</td>'


def campgrounds_page():
    rows = []
    for s in P["segs"]:
        st = STOPS[s["id"]]
        camps = st["campgrounds"] or [dict(name="Not chosen yet", type="", notes="")]
        for j, c in enumerate(camps):
            first = j == 0
            when = f'{s["arrive"].strftime("%b %-d")}–{s["depart"].strftime("%b %-d")}'
            rows.append(f"""<tr{' class="grp"' if first else ''}>
<th scope="row">{e(st['name']) if first else ''}{f'<small>{when}</small>' if first else ''}</th>
<td>{e(c['name'])}</td><td>{e(c.get('type', ''))}</td><td>{e(c.get('notes', ''))}</td>
{cell(c.get('fit'))}{cell(c.get('opens'))}<td>{e(c.get('status', 'Candidate'))}</td></tr>""")
    table = (f"""<div class="scroll"><table class="camps"><thead><tr><th>Stop</th><th>Campground</th><th>Type</th><th>Notes</th><th>Site fit</th><th>Booking opens</th><th>Status</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>""" if rows else
             '<p class="empty">No stops chosen yet, so no campground candidates. They’ll show up here with site fit and booking dates.</p>')
    body = f"""<h1>Campgrounds</h1>
<p class="lede">Nothing’s booked. “Check” means not verified yet.</p>{table}"""
    return page("Campgrounds", body, 1)


def decisions_page():
    items = "".join(f"""<li class="{d['status']}"><h3>{e(d['q'])}</h3><p class="who">{e(d['who'])}, {e(d['status'])}</p>
{f"<p>{e(d['note'])}</p>" if d['note'] else ''}</li>""" for d in DECS)
    body = f'<h1>Decisions</h1><p class="lede">What’s settled and what’s still open.</p><ul class="decisions">{items}</ul>'
    return page("Decisions", body, 1)


def write(rel, text):
    f = ROOT / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text)


if __name__ == "__main__":
    for sid, _ in TRIP["stops"]:
        assert sid in STOPS, f"trip.json lists '{sid}' but stops.json has no such stop"
    assert P["planned"] <= TOTAL_NIGHTS, f"{P['planned']} nights planned but the caravan has {TOTAL_NIGHTS}"
    write("index.html", index_page())
    write("itinerary/index.html", itinerary_page())
    write("route-map/index.html", route_page())
    write("campgrounds/index.html", campgrounds_page())
    write("decisions/index.html", decisions_page())
    if P["segs"]:
        write("route-map/springtime-kentucky-2028.kml", kml())
        write("route-map/springtime-kentucky-2028.gpx", gpx())
    print(f"{TITLE}: {START} to {END}, farewell {FAREWELL}; "
          f"{P['planned']}/{TOTAL_NIGHTS} nights planned across {len(P['segs'])} stops")
