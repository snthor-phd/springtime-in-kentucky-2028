#!/usr/bin/env python3
"""Build the Springtime in Kentucky 2028 caravan site from data/*.json.

Edit anything in data/, then run:
    python3 build.py
deploy.sh runs this automatically before pushing.

trip.json "mode": "planning" builds everything, including the Planning section.
                  "participants" builds the version for caravan members: no tasks, budget,
                  ideas, decisions, booking status, or campgrounds that weren't chosen.
"""
import json, html, shutil, datetime as dt
from pathlib import Path

ROOT = Path(__file__).parent


def D(f, default=None):
    p = ROOT / "data" / f
    return json.loads(p.read_text()) if p.exists() else default


TRIP, STOPS, CAMPS = D("trip.json"), D("stops.json"), D("campgrounds.json")
CONTACTS, IDEAS, TASKS = D("contacts.json", {}), D("ideas.json", {"ideas": []}), D("tasks.json", {"tasks": []})
BUDGET, DECS = D("budget.json", {}), D("decisions.json", [])
LEGS = D("routes.json", {}).get("legs", {})
PLACES = D("places.json", {})
CAMPS = {k: v for k, v in CAMPS.items() if not k.startswith("_")}

PLANNING = TRIP.get("mode", "planning") == "planning"
SITE = TRIP.get("site_url", "").rstrip("/") + "/"
START = dt.date.fromisoformat(TRIP["start"])
END = dt.date.fromisoformat(TRIP["end"])
FAREWELL = dt.date.fromisoformat(TRIP["farewell"])
TOTAL_NIGHTS = (END - START).days + 1
FIXED = [dict(f, date=dt.date.fromisoformat(f["date"])) for f in TRIP["fixed"]]
TODAY = dt.date.today()
TOW_FACTOR = 1.2
TITLE = TRIP["title"]
e = html.escape
TZ_NOTE = "Bowling Green is on Central time; everything else is Eastern."


def fmt(d, year=False):
    return d.strftime("%a %b %-d, %Y" if year else "%a %b %-d")


def short(d):
    return d.strftime("%b %-d")


def plural(n, w):
    return f"{n} {w}{'' if n == 1 else 's'}"


def ll(pid):
    p = PLACES.get(pid)
    return (p["lat"], p["lon"]) if p else None


# ---------------------------------------------------------------- plan
def plan():
    segs, day, prev = [], START, None
    for sid, n in TRIP["stops"]:
        st = STOPS[sid]
        cg = st.get("campground")
        leg = LEGS.get(f"{STOPS[prev]['campground']}-{cg}") if prev else None
        segs.append(dict(id=sid, nights=n, arrive=day, depart=day + dt.timedelta(n), prev=prev, camp=cg,
                         mi=leg["mi"] if leg else None,
                         tow_h=round(leg["car_h"] * TOW_FACTOR, 1) if leg else None))
        day += dt.timedelta(n)
        prev = sid
    planned = sum(s["nights"] for s in segs)
    miles = sum(s["mi"] or 0 for s in segs)
    return dict(segs=segs, planned=planned, open=TOTAL_NIGHTS - planned, miles=miles)


P = plan()
SEG = {s["id"]: s for s in P["segs"]}


def base_of(d):
    for s in P["segs"]:
        if s["arrive"] <= d < s["depart"]:
            return s["id"]
    return None


# ---------------------------------------------------------------- page shell
def nav(depth, section):
    up = "../" * depth
    items = [("", "Overview"), ("itinerary/", "Itinerary"), ("route-map/", "Map"),
             ("campgrounds/", "Campgrounds"), ("contacts/", "Contacts")]
    if PLANNING:
        items.append(("planning/", "Planning"))
    out = []
    for p, t in items:
        cur = ' aria-current="page"' if section == p else ""
        out.append(f'<a href="{up}{p}"{cur}>{e(t)}</a>')
    return "".join(out)


SUB = [("planning/", "Dashboard"), ("planning/tasks/", "Tasks & calendar"), ("planning/bookings/", "Booking windows"),
       ("planning/ideas/", "Ideas"), ("planning/budget/", "Budget"), ("planning/decisions/", "Decisions")]


def subnav(depth, cur):
    up = "../" * depth
    cur_attr = ' aria-current="page"'
    return '<nav class="subnav" aria-label="Planning">' + "".join(
        f'<a href="{up}{p}"{cur_attr if p == cur else ""}>{e(t)}</a>' for p, t in SUB) + "</nav>"


def page(title, body, depth, section, head_extra="", scripts=""):
    up = "../" * depth
    banner = ('<div class="modebar">Planning version for the caravan leaders; not for participants yet. '
              'Send changes to Steve.</div>') if PLANNING else ""
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
<header class="top"><a class="brand" href="{up}">Springtime in Kentucky <span>2028</span></a><nav>{nav(depth, section)}</nav></header>
{banner}<main>{body}</main>
<footer>Airstream Club International caravan led by {e(TRIP["leaders"])}. Towing times are estimates (car time + 20%). {e(TZ_NOTE)}<br>Airstream is a registered trademark of Airstream, Inc. All rights reserved.</footer>
{scripts}</body></html>"""


# ---------------------------------------------------------------- overview
def strip_svg():
    days = (FAREWELL - START).days + 1
    W, L, R = 1000, 8, 8
    px = (W - L - R) / days
    out, y0 = [], 40
    for d in range(days):
        date = START + dt.timedelta(d)
        x = L + d * px
        if date.weekday() in (5, 6):
            out.append(f'<rect x="{x:.1f}" y="{y0 - 6}" width="{px:.1f}" height="44" class="st-wknd"/>')
        if date.weekday() == 5 or d == 0:
            out.append(f'<text x="{x + 3:.1f}" y="{y0 - 12}" class="st-date">{date.strftime("%a %b %-d")}</text>')
    for s in P["segs"]:
        d0 = (s["arrive"] - START).days
        x, w = L + d0 * px, s["nights"] * px
        name = STOPS[s["id"]]["name"].split(" & ")[0].replace(" horse country", "")
        out.append(f'<rect x="{x + 1:.1f}" y="{y0}" width="{w - 2:.1f}" height="30" rx="3" class="st-stop">'
                   f'<title>{e(STOPS[s["id"]]["name"])}: {fmt(s["arrive"])} to {fmt(s["depart"])}, '
                   f'{plural(s["nights"], "night")}</title></rect>')
        if len(name) * 6.2 <= w - 6:
            out.append(f'<text x="{x + w / 2:.1f}" y="{y0 + 20}" text-anchor="middle" class="st-lab">{e(name)}</text>')
    if P["open"] > 0:
        x, w = L + P["planned"] * px, P["open"] * px
        out.append(f'<rect x="{x + 1:.1f}" y="{y0}" width="{w - 2:.1f}" height="30" rx="3" class="st-open"/>')
    fx = L + (FAREWELL - START).days * px
    out.append(f'<rect x="{fx + 1:.1f}" y="{y0}" width="{px - 2:.1f}" height="30" rx="3" class="st-farewell">'
               f'<title>Farewell, {fmt(FAREWELL)}</title></rect>')
    rows = {"race": 58, "derby": 74, "farewell": 58}
    for f in FIXED:
        d = (f["date"] - START).days
        cx = L + d * px + px / 2
        cls = "st-derby" if f["kind"] in ("derby", "race") else "st-fixed"
        ty = y0 + rows.get(f["kind"], 58)
        out.append(f'<line x1="{cx:.1f}" y1="{y0 + 30}" x2="{cx:.1f}" y2="{ty - 12}" class="{cls}-line"/>')
        out.append(f'<rect x="{L + d * px + 1:.1f}" y="{y0 + 26}" width="{px - 2:.1f}" height="4" class="{cls}-mark"/>')
        anchor = "end" if d > days - 5 else "middle"
        out.append(f'<text x="{cx:.1f}" y="{ty}" text-anchor="{anchor}" class="{cls}-lab">'
                   f'{e(f["label"])}, {f["date"].strftime("%a %b %-d")}</text>')
    H = y0 + 82
    return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Calendar strip of the caravan, '
            f'{fmt(START)} to {fmt(FAREWELL)}" class="strip">{"".join(out)}</svg>')


def index_page():
    derby = next(f for f in FIXED if f["kind"] == "derby")
    race = next((f for f in FIXED if f["kind"] == "race"), None)
    route = " → ".join(STOPS[s["id"]]["name"].split(" & ")[0].replace(" horse country", "") for s in P["segs"])
    body = f"""
<section class="hero">
  <p class="dates">{START.strftime("%B %-d")} – {END.strftime("%B %-d")}, 2028 · farewell {FAREWELL.strftime("%B %-d")}</p>
  <h1>Three weeks of Kentucky in spring, with Derby Day on day {(derby["date"] - START).days + 1}.</h1>
  <p class="lede">An Airstream Club International caravan led by {e(TRIP["leaders"])}. Cave country, Derby week, bourbon, horse farms and mountain music, west to east.</p>
  <p class="countdown" id="countdown"></p>
</section>
<section class="compare">
  <h2>{TOTAL_NIGHTS} nights, five bases, and a day at the races before the Derby</h2>
  <div class="scroll">{strip_svg()}</div>
  <p class="caption">Each block is one base, sized by nights; weekends are shaded. Hover or tap a block for dates.</p>
  <table class="facts"><tbody>
    <tr><th>Route</th><td>{e(route)}</td></tr>
    <tr><th>Roll in</th><td>{fmt(START, True)}, {e(STOPS[P["segs"][0]["id"]]["place"])}</td></tr>
    {f'<tr><th>Race day</th><td>{fmt(race["date"], True)}, {e(race["place"])}</td></tr>' if race else ''}
    <tr><th>Kentucky Derby</th><td>{fmt(derby["date"], True)}, {e(derby["place"])}</td></tr>
    <tr><th>Farewell</th><td>{fmt(FAREWELL, True)}</td></tr>
    <tr><th>Towing</th><td>{P["miles"]:,} miles base to base (getting to the start is on your own)</td></tr>
    <tr><th>Leaders</th><td>{e(TRIP["leaders"])}</td></tr>
  </tbody></table>
</section>
<section class="pages">
  <a href="itinerary/"><h3>Itinerary</h3><p>Base by base: dates, drives, campgrounds, highlights.</p></a>
  <a href="route-map/"><h3>Map</h3><p>Road route, campgrounds, sights and hospitals, with GPS downloads.</p></a>
  <a href="campgrounds/"><h3>Campgrounds</h3><p>Where we park at each base{', plus the candidates' if PLANNING else ''}.</p></a>
  <a href="contacts/"><h3>Contacts</h3><p>Hospitals and campgrounds by base.</p></a>
  {'<a href="planning/"><h3>Planning</h3><p>Tasks, calendar, booking windows, ideas, budget and decisions.</p></a>' if PLANNING else ''}
</section>"""
    js = f"""<script>
(function(){{var s=new Date("{START.isoformat()}T12:00:00"),n=new Date(),d=Math.round((s-n)/864e5),el=document.getElementById("countdown");
if(d>0)el.textContent=d+" days until we roll out.";else if(d>-{TOTAL_NIGHTS + 1})el.textContent="Day "+(1-d)+" of the caravan.";else el.textContent="Caravan complete.";}})();
</script>"""
    return page("Overview", body, 0, "", scripts=js)


# ---------------------------------------------------------------- itinerary
def camp_line(cid):
    c = CAMPS.get(cid)
    if not c:
        return "Not chosen yet"
    tag = "" if c["status"] == "booked" else (" <span class=\"tag\">to be confirmed</span>" if not PLANNING
                                             else f' <span class="tag">{e(c["status"])}</span>')
    return f'{e(c["name"])}, {e(c["phone"])}{tag}'


def itinerary_page():
    items = []
    for i, s in enumerate(P["segs"], 1):
        st = STOPS[s["id"]]
        if s["prev"] is None:
            drive = "Rendezvous. Arrive from home on your own schedule."
        elif s["mi"] is None:
            drive = f'From {e(STOPS[s["prev"]]["name"])}; mileage TBD'
        else:
            drive = f'{s["mi"]} mi from {e(STOPS[s["prev"]]["name"])}, about {s["tow_h"]} h towing'
        fixed = "".join(f'<p class="fixedev">{e(f["label"])}, {fmt(f["date"])}</p>' for f in FIXED
                        if s["arrive"] <= f["date"] < s["depart"])
        hi = "".join(f"<li>{e(h)}</li>" for h in st.get("highlights", []))
        tz = f' <span class="tz">{e(st["tz"])} time</span>' if st.get("tz") == "Central" else ""
        items.append(f"""<li class="stop" id="{s['id']}">
<div class="when"><span class="n">{i}</span><b>{short(s['arrive'])}–{short(s['depart'])}</b><span>{plural(s['nights'], 'night')}</span></div>
<div class="what"><h3>{e(st['name'])} <small>{e(st['place'])}</small>{tz}</h3>
<p class="drive">{drive}</p>{fixed}<p>{e(st['blurb'])}</p>
{f'<ul>{hi}</ul>' if hi else ''}<p class="camp">Campground: {camp_line(s['camp'])}</p></div></li>""")
    items.append(f"""<li class="stop k-farewell"><div class="when"><span class="n">★</span><b>{short(FAREWELL)}</b><span>farewell</span></div>
<div class="what"><h3>Farewell</h3><p class="drive">{fmt(FAREWELL, True)}. Venue to be set.</p></div></li>""")
    body = (f'<h1>Itinerary</h1><p class="lede">{TOTAL_NIGHTS} nights at five bases, {P["miles"]:,} towing miles. '
            f'{e(TZ_NOTE)} Day-by-day schedules and directions come later.</p><ol class="stops">{"".join(items)}</ol>')
    return page("Itinerary", body, 1, "itinerary/")


# ---------------------------------------------------------------- map
def route_line():
    pts = []
    segs = P["segs"]
    for a, b in zip(segs, segs[1:]):
        leg = LEGS.get(f"{a['camp']}-{b['camp']}")
        if leg and leg.get("geom"):
            pts += leg["geom"]
        else:
            for c in (a["camp"], b["camp"]):
                if ll(c):
                    pts.append(list(ll(c)))
    return pts


def map_data():
    bases, others, acts, hosp = [], [], [], []
    for i, s in enumerate(P["segs"], 1):
        c = CAMPS.get(s["camp"])
        p = ll(s["camp"])
        if c and p:
            bases.append(dict(n=i, base=s["id"], name=c["name"], stop=STOPS[s["id"]]["name"],
                              dates=f'{short(s["arrive"])}–{short(s["depart"])}', phone=c["phone"], lat=p[0], lon=p[1]))
    if PLANNING:
        for cid, c in CAMPS.items():
            p = ll(cid)
            if p and cid not in {s["camp"] for s in P["segs"]}:
                others.append(dict(name=c["name"], role=c["role"], base=c["base"], phone=c["phone"],
                                   status=c["status"], lat=p[0], lon=p[1]))
    seen = set()
    for it in IDEAS.get("ideas", []):
        pid = it.get("pin")
        if not pid or pid in seen or not ll(pid):
            continue
        if not PLANNING and it["status"] != "scheduled":
            continue
        seen.add(pid)
        p = ll(pid)
        acts.append(dict(name=it["title"], base=it["base"], derby=pid in ("churchilldowns", "keeneland"),
                         status=it["status"], lat=p[0], lon=p[1]))
    for h in CONTACTS.get("hospitals", []):
        p = ll(h["id"])
        if p:
            hosp.append(dict(name=h["name"], phone=h["phone"], address=h["address"], lat=p[0], lon=p[1]))
    return dict(line=route_line(), bases=bases, others=others, acts=acts, hosp=hosp)


def route_page():
    data = map_data()
    btns = '<button data-zoom="all" aria-pressed="true">Whole route</button>' + "".join(
        f'<button data-zoom="{s["id"]}">{e(STOPS[s["id"]]["name"].split(" & ")[0].replace(" horse country", ""))}</button>'
        for s in P["segs"])
    body = f"""<h1>Map</h1>
<div class="zoombar" role="group" aria-label="Zoom to a base">{btns}</div>
<div id="map" aria-label="Route map"></div>
<p class="caption">Green numbered pins are the base campgrounds{"; white pins are other candidates" if PLANNING else ""}. Rose pins are Derby-week events; dark dots are sights; <b>H</b> marks hospitals. Use the layer box (top right) to show or hide each set.</p>
<p class="downloads">Downloads: <a href="springtime-kentucky-2028.kml" download>KML (Google My Maps)</a> <a href="springtime-kentucky-2028.gpx" download>GPX (RV GPS)</a></p>
<p class="caption">KML imports into Google My Maps (Create map → Import). GPX loads into most RV GPS units and apps.</p>"""
    head = '\n<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">'
    js = f"""<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script>
var D={json.dumps(data, ensure_ascii=False)};
var map=L.map('map',{{scrollWheelZoom:false}});
L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{maxZoom:18,attribution:'&copy; OpenStreetMap contributors'}}).addTo(map);
function esc(s){{return String(s).replace(/[&<>"]/g,function(c){{return{{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]}})}}
var gRoute=L.layerGroup(),gBases=L.layerGroup(),gOther=L.layerGroup(),gActs=L.layerGroup(),gHosp=L.layerGroup();
if(D.line.length)L.polyline(D.line,{{color:'#2F5D46',weight:4,opacity:.85}}).addTo(gRoute);
var byBase={{}};
D.bases.forEach(function(b){{
 var m=L.marker([b.lat,b.lon],{{icon:L.divIcon({{className:'pin-base',html:'<span>'+b.n+'</span>',iconSize:[26,26],iconAnchor:[13,13]}}),zIndexOffset:1000}})
 .bindPopup('<b>'+b.n+'. '+esc(b.stop)+'</b><br>'+esc(b.dates)+'<br>'+esc(b.name)+'<br>'+esc(b.phone)).addTo(gBases);
 (byBase[b.base]=byBase[b.base]||[]).push([b.lat,b.lon]);}});
D.others.forEach(function(c){{
 L.circleMarker([c.lat,c.lon],{{radius:6,color:'#2F5D46',weight:2,fillColor:'#fff',fillOpacity:1}})
 .bindPopup('<b>'+esc(c.name)+'</b><br>'+esc(c.role)+' · '+esc(c.status)+'<br>'+esc(c.phone)).addTo(gOther);
 (byBase[c.base]=byBase[c.base]||[]).push([c.lat,c.lon]);}});
D.acts.forEach(function(a){{
 L.circleMarker([a.lat,a.lon],{{radius:a.derby?7:5,color:'#fff',weight:1.5,fillColor:a.derby?'#B0233E':'#38443B',fillOpacity:1}})
 .bindPopup('<b>'+esc(a.name)+'</b><br>'+esc(a.status)).addTo(gActs);
 (byBase[a.base]=byBase[a.base]||[]).push([a.lat,a.lon]);}});
D.hosp.forEach(function(h){{
 L.marker([h.lat,h.lon],{{icon:L.divIcon({{className:'pin-h',html:'H',iconSize:[18,18],iconAnchor:[9,9]}})}})
 .bindPopup('<b>'+esc(h.name)+'</b><br>'+esc(h.address)+'<br>'+esc(h.phone)).addTo(gHosp);}});
[gRoute,gBases,gOther,gActs,gHosp].forEach(function(g){{g.addTo(map)}});
var layers={{'Route':gRoute,'Base campgrounds':gBases,'Sights and events':gActs,'Hospitals':gHosp}};
if(D.others.length)layers['Other campground candidates']=gOther;
L.control.layers(null,layers,{{collapsed:window.innerWidth<640}}).addTo(map);
var all=[].concat(D.line,D.bases.map(function(b){{return[b.lat,b.lon]}}));
function zoom(k){{var pts=k==='all'?all:(byBase[k]||[]);if(pts.length)map.fitBounds(L.latLngBounds(pts),{{padding:[30,30],maxZoom:12}});
 document.querySelectorAll('[data-zoom]').forEach(function(b){{b.setAttribute('aria-pressed',b.dataset.zoom===k)}})}}
document.querySelectorAll('[data-zoom]').forEach(function(b){{b.addEventListener('click',function(){{zoom(b.dataset.zoom)}})}});
if(all.length)zoom('all');else map.fitBounds([[36.5,-89.6],[39.15,-81.9]]);
</script>"""
    return page("Map", body, 1, "route-map/", head_extra=head, scripts=js)


def kml():
    d = map_data()
    coords = " ".join(f"{lon},{lat},0" for lat, lon in d["line"])
    pm = []
    for b in d["bases"]:
        pm.append(f'<Placemark><name>{b["n"]}. {e(b["stop"])} — {e(b["name"])}</name><description>{e(b["dates"])}. '
                  f'{e(b["phone"])}</description><Point><coordinates>{b["lon"]},{b["lat"]},0</coordinates></Point></Placemark>')
    for h in d["hosp"]:
        pm.append(f'<Placemark><name>H: {e(h["name"])}</name><description>{e(h["address"])}. {e(h["phone"])}</description>'
                  f'<Point><coordinates>{h["lon"]},{h["lat"]},0</coordinates></Point></Placemark>')
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>{e(TITLE)}</name>
<Style id="r"><LineStyle><color>ff465d2f</color><width>4</width></LineStyle></Style>
<Placemark><name>Route</name><styleUrl>#r</styleUrl><LineString><tessellate>1</tessellate><coordinates>{coords}</coordinates></LineString></Placemark>
{''.join(pm)}</Document></kml>"""


def gpx():
    d = map_data()
    w = "".join(f'<wpt lat="{b["lat"]}" lon="{b["lon"]}"><name>{b["n"]}. {e(b["name"])}</name><desc>{e(b["stop"])}, '
                f'{e(b["dates"])}</desc></wpt>' for b in d["bases"])
    w += "".join(f'<wpt lat="{h["lat"]}" lon="{h["lon"]}"><name>H {e(h["name"])}</name><desc>{e(h["phone"])}</desc></wpt>'
                 for h in d["hosp"])
    trk = "".join(f'<trkpt lat="{lat}" lon="{lon}"/>' for lat, lon in d["line"])
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="springtime-in-kentucky-2028" xmlns="http://www.topografix.com/GPX/1/1">
{w}<trk><name>{e(TITLE)}</name><trkseg>{trk}</trkseg></trk></gpx>"""


# ---------------------------------------------------------------- campgrounds
ROLE = {"pick": "First call", "backup": "Backup", "alt": "Alternate", "2012": "2012 park"}


def campgrounds_page():
    secs = []
    for s in P["segs"]:
        rows = []
        cands = [(k, c) for k, c in CAMPS.items() if c["base"] == s["id"]]
        cands.sort(key=lambda kc: ["pick", "backup", "alt", "2012"].index(kc[1]["role"]))
        for cid, c in cands:
            if not PLANNING and cid != s["camp"]:
                continue
            link = f' <a href="{e(c["source"])}" rel="noopener">source</a>' if c.get("source") else ""
            rows.append(f"""<article class="cg r-{c['role']} s-{c['status']}">
<header><span class="role">{e(ROLE.get(c['role'], c['role']))}</span>{f'<span class="status">{e(c["status"])}</span>' if PLANNING else ''}
<h3>{e(c['name'])}</h3><p class="ph">{e(c['phone'])}{f' · {e(c["phone2"])}' if c.get('phone2') else ''}</p><p class="addr">{e(c['address'])}</p></header>
<dl><dt>Sites</dt><dd>{e(c['sites'])}</dd><dt>Groups</dt><dd>{e(c['group'])}</dd><dt>Drive</dt><dd>{e(c['drive'])}</dd>
{f'<dt>Reviews</dt><dd>{e(c["reviews"])}</dd>' if PLANNING else ''}{f'<dt>Notes</dt><dd>{e(c["notes"])}{link}</dd>' if (c['notes'] or link) and PLANNING else ''}</dl></article>""")
        secs.append(f'<section class="cgbase" id="{s["id"]}"><h2>{e(STOPS[s["id"]]["name"])} '
                    f'<small>{short(s["arrive"])}–{short(s["depart"])}, {plural(s["nights"], "night")}</small></h2>'
                    f'<div class="cggrid">{"".join(rows)}</div></section>')
    lede = ("Every candidate, first call first. Nothing is booked yet. Status runs candidate → called → quoted → held → booked; "
            "Group size to plan for: "
            f"{TRIP.get('rig_cap', 26)} rigs, trailers up to about 26 ft and 30 A. (I) = our estimate."
            if PLANNING else "Where we park at each base.")
    body = f'<h1>Campgrounds</h1><p class="lede">{lede}</p>{"".join(secs)}'
    return page("Campgrounds", body, 1, "campgrounds/")


# ---------------------------------------------------------------- contacts
def contacts_page():
    secs = []
    for s in P["segs"]:
        st = STOPS[s["id"]]
        c = CAMPS.get(s["camp"], {})
        hs = [h for h in CONTACTS.get("hospitals", []) if h["base"] == s["id"]]
        hrows = "".join(f'<li><b>{e(h["name"])}</b><br>{e(h["phone"])} · {e(h["address"])}'
                        + (f'<br><span class="was">{e(h["was2012"])}</span>' if PLANNING and h.get("was2012") else "")
                        + (f'<br><span class="was">{e(h["note"])}</span>' if PLANNING and h.get("note") else "")
                        + "</li>" for h in hs)
        bk = [b for b in CONTACTS.get("booking", []) if b["base"] == s["id"]] if PLANNING else []
        brows = "".join(f'<li><b>{e(b["name"])}</b><br>{e(" · ".join(x for x in (b["phone"], b["contact"]) if x))}'
                        f'<br><span class="was">{e(b["note"])}</span></li>' for b in bk)
        secs.append(f"""<section class="cbase"><h2>{e(st['name'])} <small>{short(s['arrive'])}–{short(s['depart'])}</small></h2>
<div class="ccols"><div><h3>Campground</h3><ul><li><b>{e(c.get('name', 'Not chosen yet'))}</b><br>{e(c.get('phone', ''))} · {e(c.get('address', ''))}</li></ul></div>
<div><h3>Hospitals</h3><ul>{hrows}</ul></div>{f'<div><h3>Booking contacts</h3><ul>{brows}</ul></div>' if brows else ''}</div></section>""")
    club = ""
    if PLANNING:
        club = "".join(f'<li><b>{e(x["name"])}</b><br><span class="was">{e(x["note"])}</span></li>' for x in CONTACTS.get("club", []))
        club = f'<section class="cbase"><h2>Club</h2><ul>{club}</ul></section>'
    body = (f'<h1>Contacts</h1><p class="lede emergency">In an emergency, call <b>911</b>, then the leaders.</p>'
            + ('<p class="caption">Gray notes show where the 2012 book’s details have changed. Checked October 2026.</p>' if PLANNING else '')
            + "".join(secs) + club)
    return page("Contacts", body, 1, "contacts/")


# ---------------------------------------------------------------- planning: shared
def task_list():
    ts = []
    for t in TASKS.get("tasks", []):
        t = dict(t)
        t["date"] = dt.date.fromisoformat(t["due"])
        ts.append(t)
    return sorted(ts, key=lambda t: (t["date"], t["id"]))


def badge(status):
    return f'<span class="badge b-{e(status)}">{e(status)}</span>'


def task_row(t, show_base=True):
    over = t["status"] != "done" and t["date"] < TODAY
    base = STOPS.get(t.get("base") or "", {}).get("name", "")
    est = ' <span class="est" title="Estimated date; confirm">estimate</span>' if t.get("check") else ""
    kind = "" if t["kind"] == "task" else f'<span class="kind">{e(t["kind"])}</span>'
    return f"""<tr class="{'over' if over else ''} st-{e(t['status'])}"><td class="d">{t['date'].strftime('%b %-d, %Y')}{est}</td>
<td>{kind}{e(t['title'])}{f'<div class="note">{e(t["note"])}</div>' if t.get('note') else ''}</td>
<td>{e(t['owner'])}</td>{f'<td>{e(base)}</td>' if show_base else ''}<td>{badge(t['status'])}</td></tr>"""


# ---------------------------------------------------------------- planning: dashboard
def dashboard_page():
    ts = task_list()
    open_ = [t for t in ts if t["status"] != "done"]
    over = [t for t in open_ if t["date"] < TODAY and t["kind"] == "task"]
    nxt = [t for t in open_ if t["date"] >= TODAY][:6]
    days = (START - TODAY).days
    open_dec = sum(1 for d in DECS if d["status"] == "open")
    rows = "".join(task_row(t) for t in over + nxt)
    book = "".join(f'<tr><td>{e(STOPS[s["id"]]["name"])}</td><td>{e(CAMPS.get(s["camp"], {}).get("name", "—"))}</td>'
                   f'<td>{badge(CAMPS.get(s["camp"], {}).get("status", "none"))}</td></tr>' for s in P["segs"])
    body = f"""<h1>Planning</h1>{subnav(1, 'planning/')}
<div class="tiles">
 <div><b>{days:,}</b><span>days to roll-out</span></div>
 <div><b>{len(open_)}</b><span>open tasks</span></div>
 <div class="{'warn' if over else ''}"><b>{len(over)}</b><span>overdue</span></div>
 <div><b>{open_dec}</b><span>open decisions</span></div>
</div>
<h2>Coming up</h2>
<div class="scroll"><table class="tasks"><thead><tr><th>Due</th><th>What</th><th>Who</th><th>Base</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table></div>
<p><a href="tasks/">All tasks and the calendar →</a></p>
<h2>Campgrounds at each base</h2>
<div class="scroll"><table class="tasks"><thead><tr><th>Base</th><th>First call</th><th>Status</th></tr></thead><tbody>{book}</tbody></table></div>
<p><a href="../campgrounds/">Campground candidates →</a></p>"""
    return page("Planning", body, 1, "planning/")


# ---------------------------------------------------------------- planning: tasks + calendar + ics
def tasks_page():
    ts = task_list()
    groups, cur = [], None
    for t in ts:
        m = t["date"].strftime("%B %Y")
        if m != cur:
            groups.append([m, []])
            cur = m
        groups[-1][1].append(task_row(t))
    tbl = "".join(f'<tr class="month"><th colspan="5">{m}</th></tr>' + "".join(r) for m, r in groups)
    ev = [dict(d=t["due"], t=t["title"], k=t["kind"], s=t["status"], c=bool(t.get("check"))) for t in ts]
    for s in P["segs"]:
        for i in range(s["nights"]):
            d = s["arrive"] + dt.timedelta(i)
            ev.append(dict(d=d.isoformat(), t=STOPS[s["id"]]["name"].split(" & ")[0], k="trip", s="", c=False))
    for f in FIXED:
        ev.append(dict(d=f["date"].isoformat(), t=f["label"], k="derby" if f["kind"] in ("derby", "race") else "trip", s="", c=False))
    ics_url = SITE + "planning/springtime-kentucky-2028.ics"
    webcal = "webcal://" + ics_url.split("://", 1)[-1]
    first = max(TODAY.replace(day=1), dt.date(2026, 10, 1))
    body = f"""<h1>Tasks &amp; calendar</h1>{subnav(2, 'planning/tasks/')}
<p class="lede">Dates marked “estimate” are our best guess and need confirming. Send updates to Steve.</p>
<p class="subscribe"><a class="btn" href="{e(webcal)}">Subscribe in Calendar</a> <a href="springtime-kentucky-2028.ics" download>Download .ics</a>
<span class="caption">Subscribing keeps Apple or Google Calendar in step with this page after each deploy.</span></p>
<div class="tabs" role="tablist"><button role="tab" data-v="cal" aria-selected="true">Calendar</button><button role="tab" data-v="list" aria-selected="false">List</button></div>
<section class="view" data-v="cal">
 <div class="calbar"><button id="prev" aria-label="Previous month">‹</button><h2 id="mlabel"></h2><button id="next" aria-label="Next month">›</button>
 <button id="today">This month</button><button id="trip">Caravan (May 2028)</button></div>
 <div class="cal" id="cal" aria-live="polite"></div>
 <p class="caption">Green = caravan days; rose = race day and Derby; outlined = booking windows and milestones; struck through = done.</p>
</section>
<section class="view" data-v="list" hidden>
 <div class="scroll"><table class="tasks"><thead><tr><th>Due</th><th>What</th><th>Who</th><th>Base</th><th>Status</th></tr></thead><tbody>{tbl}</tbody></table></div>
</section>"""
    js = f"""<script>
var EV={json.dumps(ev, ensure_ascii=False)};
var cur=new Date({first.year},{first.month - 1},1);
function esc(s){{return String(s).replace(/[&<>]/g,function(c){{return{{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c]}})}}
function iso(d){{return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2)}}
function draw(){{
 var y=cur.getFullYear(),m=cur.getMonth(),first=new Date(y,m,1),start=new Date(y,m,1-first.getDay());
 document.getElementById('mlabel').textContent=first.toLocaleDateString('en-US',{{month:'long',year:'numeric'}});
 var h='<div class="dow">Sun</div><div class="dow">Mon</div><div class="dow">Tue</div><div class="dow">Wed</div><div class="dow">Thu</div><div class="dow">Fri</div><div class="dow">Sat</div>';
 var today=iso(new Date());
 for(var i=0;i<42;i++){{var d=new Date(start);d.setDate(start.getDate()+i);var k=iso(d);
  var items=EV.filter(function(e){{return e.d===k}}).map(function(e){{return '<span class="ev k-'+e.k+(e.s==='done'?' done':'')+'">'+esc(e.t)+(e.c?' *':'')+'</span>'}}).join('');
  h+='<div class="day'+(d.getMonth()!==m?' out':'')+(k===today?' now':'')+'"><span class="dn">'+d.getDate()+'</span>'+items+'</div>';}}
 document.getElementById('cal').innerHTML=h;}}
document.getElementById('prev').onclick=function(){{cur.setMonth(cur.getMonth()-1);draw()}};
document.getElementById('next').onclick=function(){{cur.setMonth(cur.getMonth()+1);draw()}};
document.getElementById('today').onclick=function(){{var n=new Date();cur=new Date(n.getFullYear(),n.getMonth(),1);draw()}};
document.getElementById('trip').onclick=function(){{cur=new Date(2028,4,1);draw()}};
document.querySelectorAll('[role=tab]').forEach(function(b){{b.addEventListener('click',function(){{
 document.querySelectorAll('[role=tab]').forEach(function(x){{x.setAttribute('aria-selected',x===b)}});
 document.querySelectorAll('.view').forEach(function(v){{v.hidden=v.dataset.v!==b.dataset.v}});
 try{{localStorage.setItem('ky28view',b.dataset.v)}}catch(e){{}}}})}});
try{{var v=localStorage.getItem('ky28view');if(v)document.querySelector('[role=tab][data-v="'+v+'"]').click()}}catch(e){{}}
draw();
</script>"""
    return page("Tasks & calendar", body, 2, "planning/", scripts=js)


def ics():
    def esc_ics(s):
        return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ev = []

    def add(uid, d0, d1, summary, desc=""):
        ev.append("\r\n".join([
            "BEGIN:VEVENT", f"UID:{uid}@springtime-kentucky-2028", f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{d0.strftime('%Y%m%d')}", f"DTEND;VALUE=DATE:{d1.strftime('%Y%m%d')}",
            f"SUMMARY:{esc_ics(summary)}", f"DESCRIPTION:{esc_ics(desc)}", "TRANSP:TRANSPARENT", "END:VEVENT"]))

    for t in task_list():
        mark = "✓ " if t["status"] == "done" else ""
        desc = f'{t["kind"]} · {t["owner"]} · {t["status"]}' + (" · estimated date" if t.get("check") else "")
        if t.get("note"):
            desc += "\n" + t["note"]
        add(t["id"], t["date"], t["date"] + dt.timedelta(1), f"KY28: {mark}{t['title']}", desc + f"\n{SITE}planning/tasks/")
    for s in P["segs"]:
        add(f"stop-{s['id']}", s["arrive"], s["depart"], f"KY28 caravan: {STOPS[s['id']]['name']}",
            f"{plural(s['nights'], 'night')} at {CAMPS.get(s['camp'], {}).get('name', 'campground TBD')}")
    def fold(line):  # RFC 5545: lines over 75 octets continue with a leading space
        out, cur = [], ""
        for ch in line:
            if len((cur + ch).encode()) > 74:
                out.append(cur)
                cur = " "
            cur += ch
        return "\r\n".join(out + [cur])

    ev = ["\r\n".join(fold(l) for l in x.split("\r\n")) for x in ev]
    return "\r\n".join(["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//snthor-phd//springtime-kentucky-2028//EN",
                        "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:Springtime in Kentucky 2028",
                        "X-WR-TIMEZONE:America/New_York"] + ev + ["END:VCALENDAR"]) + "\r\n"


# ---------------------------------------------------------------- planning: booking windows
def bookings_page():
    ts = [t for t in task_list() if t["kind"] in ("window", "milestone") or t.get("check")]
    rows = "".join(task_row(t) for t in ts)
    bk = "".join(f'<tr><td>{e(STOPS.get(b["base"], {}).get("name", ""))}</td><td><b>{e(b["name"])}</b></td>'
                 f'<td>{e(" · ".join(x for x in (b["phone"], b["contact"]) if x))}</td><td>{e(b["note"])} '
                 f'<a href="{e(b["source"])}" rel="noopener">source</a></td></tr>' for b in CONTACTS.get("booking", []))
    body = f"""<h1>Booking windows</h1>{subnav(2, 'planning/bookings/')}
<p class="lede">When things open and how to book them. Dates marked “estimate” come from patterns in 2025–26 and need confirming.</p>
<h2>Dates</h2>
<div class="scroll"><table class="tasks"><thead><tr><th>Date</th><th>What</th><th>Who</th><th>Base</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>How to book</h2>
<div class="scroll"><table class="tasks"><thead><tr><th>Base</th><th>What</th><th>Contact</th><th>Notes</th></tr></thead><tbody>{bk}</tbody></table></div>"""
    return page("Booking windows", body, 2, "planning/")


# ---------------------------------------------------------------- planning: ideas
def ideas_page():
    secs = []
    for s in P["segs"]:
        its = [i for i in IDEAS.get("ideas", []) if i["base"] == s["id"]]
        order = {"scheduled": 0, "shortlist": 1, "idea": 2, "dropped": 3}
        its.sort(key=lambda i: (order.get(i["status"], 9), bool(i.get("did2012"))))
        def idea_li(i):
            did = ' <span class="tag">2012 did</span>' if i.get("did2012") else ""
            note = '<div class="note">' + e(i["note"]) + "</div>" if i.get("note") else ""
            src = ' <a href="' + e(i["source"]) + '" rel="noopener">source</a>' if i.get("source") else ""
            return (f'<li class="idea st-{e(i["status"])}">{badge(i["status"])}{did} <b>{e(i["title"])}</b>'
                    f'{note}{src}</li>')
        lis = "".join(idea_li(i) for i in its)
        secs.append(f'<section><h2>{e(STOPS[s["id"]]["name"])} <small>{short(s["arrive"])}–{short(s["depart"])}</small></h2>'
                    f'<ul class="ideas">{lis}</ul></section>')
    body = (f'<h1>Ideas</h1>{subnav(2, "planning/ideas/")}<p class="lede">Activities for each base. Status runs idea → '
            'shortlist → scheduled; “2012 did” marks repeats from the 2012 caravan.</p>'
            + "".join(secs))
    return page("Ideas", body, 2, "planning/")


# ---------------------------------------------------------------- planning: budget
def budget_page():
    lines = BUDGET.get("lines", [])
    groups, known, unknown, total = {}, 0, 0, 0
    for ln in lines:
        groups.setdefault(ln["group"], []).append(ln)
    rows = []
    for g, ls in groups.items():
        rows.append(f'<tr class="month"><th colspan="4">{e(g)}</th></tr>')
        for ln in ls:
            if ln["amount"] is None:
                unknown += 1
                amt, sub = '<span class="todo">to find</span>', '<span class="todo">—</span>'
            else:
                known += 1
                v = ln["amount"] * ln["qty"]
                total += v
                amt, sub = f'${ln["amount"]:,}', f'${v:,}'
            unit = {"night": "per night", "person": "per person", "rig": "per rig"}[ln["per"]]
            src = f' <a href="{e(ln["source"])}" rel="noopener">source</a>' if ln.get("source") else ""
            rows.append(f'<tr><td>{e(ln["label"])}<div class="note">{e(ln.get("note", ""))}{src}</div></td>'
                        f'<td class="num">{amt}</td><td>{unit} × {ln["qty"]}</td><td class="num">{sub}</td></tr>')
    bench = "".join(f'<tr><td>{e(b["label"])}</td><td class="num">${b["amount"]:,}</td>'
                    f'<td><a href="{e(b["source"])}" rel="noopener">listing</a></td></tr>' for b in BUDGET.get("benchmarks", []))
    body = f"""<h1>Budget</h1>{subnav(2, 'planning/budget/')}
<p class="lede">Per rig, two people. So far we know {known} of {known + unknown} costs (${total:,} per rig); the rest need quotes.</p>
<h2>What recent runs charged</h2>
<table class="tasks narrow"><tbody>{bench}</tbody></table>
<p class="caption">The kitty covers camping, group meals and most tours. It's run at cost; anything unspent is refunded.</p>
<h2>Our estimate</h2>
<div class="scroll"><table class="tasks budget"><thead><tr><th>Item</th><th class="num">Rate</th><th>Basis</th><th class="num">Per rig</th></tr></thead>
<tbody>{''.join(rows)}<tr class="total"><th>Known so far</th><td></td><td>{unknown} items still to price</td><td class="num">${total:,}</td></tr></tbody></table></div>"""
    return page("Budget", body, 2, "planning/")


# ---------------------------------------------------------------- planning: decisions
def decisions_page():
    items = "".join(f"""<li class="{e(d['status'])}"><h3>{e(d['q'])}</h3><p class="who">{e(d['who'])}, {e(d['status'])}</p>
{f"<p>{e(d['note'])}</p>" if d['note'] else ''}</li>""" for d in DECS)
    body = (f'<h1>Decisions</h1>{subnav(2, "planning/decisions/")}<p class="lede">What’s settled and what’s still open. '
            f'</p><ul class="decisions">{items}</ul>')
    return page("Decisions", body, 2, "planning/")


# ---------------------------------------------------------------- write
GENERATED = ["index.html", "itinerary", "route-map", "campgrounds", "contacts", "planning", "decisions"]


def write(rel, text):
    f = ROOT / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text)


if __name__ == "__main__":
    for sid, _ in TRIP["stops"]:
        assert sid in STOPS, f"trip.json lists '{sid}' but stops.json has no such stop"
    assert P["planned"] <= TOTAL_NIGHTS, f"{P['planned']} nights planned but the caravan has {TOTAL_NIGHTS}"
    for g in GENERATED:  # clear old output so removed pages don't linger
        p = ROOT / g
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()
    write("index.html", index_page())
    write("itinerary/index.html", itinerary_page())
    write("route-map/index.html", route_page())
    write("route-map/springtime-kentucky-2028.kml", kml())
    write("route-map/springtime-kentucky-2028.gpx", gpx())
    write("campgrounds/index.html", campgrounds_page())
    write("contacts/index.html", contacts_page())
    if PLANNING:
        write("planning/index.html", dashboard_page())
        write("planning/tasks/index.html", tasks_page())
        write("planning/tasks/springtime-kentucky-2028.ics", ics())
        write("planning/springtime-kentucky-2028.ics", ics())
        write("planning/bookings/index.html", bookings_page())
        write("planning/ideas/index.html", ideas_page())
        write("planning/budget/index.html", budget_page())
        write("planning/decisions/index.html", decisions_page())
    missing = [k for k in list(CAMPS) + [h["id"] for h in CONTACTS.get("hospitals", [])] if k not in PLACES]
    print(f"{TITLE} [{TRIP.get('mode', 'planning')}]: {P['planned']}/{TOTAL_NIGHTS} nights, {len(P['segs'])} bases, "
          f"{P['miles']} mi; {len(TASKS.get('tasks', []))} tasks" + (f"; no coordinates for: {', '.join(missing)}" if missing else ""))
