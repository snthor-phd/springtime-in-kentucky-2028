# Springtime in Kentucky 2028

Planning site for a spring 2028 Airstream Club International caravan through Kentucky, led by Colleen and Steve Thorsen.

- **Caravan:** Sat April 29 – Sat May 20, 2028 (22 nights)
- **Kentucky Derby:** Sat May 6, 2028, day 8 of the trip
- **Farewell:** Sun May 21, 2028

Route: Bowling Green & Mammoth Cave (3 nights) → Louisville (2, race day at Churchill Downs Wed May 3) → Frankfort (3, Buffalo Trace; Derby Day at Keeneland) → Lexington (6) → Berea & Renfro Valley (8).

## Two modes
`data/trip.json` → `"mode"`:
- `"planning"` (now): everything, including the **Planning** section — dashboard, tasks & calendar (with a subscribable .ics feed), booking windows, ideas, budget and decisions — plus every campground candidate.
- `"participants"`: the caravan version. Drops the Planning section and the campgrounds we didn't choose; keeps itinerary, map, campgrounds and contacts.

## Editing
All content lives in `data/`:
- `trip.json`: mode, dates, leaders, fixed events (race day, Derby, farewell), stop order as `[stop_id, nights]`
- `stops.json`: each base: name, chosen campground, highlights
- `campgrounds.json`: every candidate with phone, sites, group notes, reviews, role (pick/backup/alt/2012) and status (candidate → called → quoted → held → booked)
- `contacts.json`: hospitals by base (with what changed since the 2012 book) and booking contacts
- `tasks.json`: tasks, booking windows and milestones (owner, due date, status; `check: true` = estimated date)
- `ideas.json`: activity ideas by base (idea → shortlist → scheduled)
- `budget.json`: per-rig cost lines and kitty benchmarks
- `decisions.json`: settled and open questions
- `places.json`, `routes.json`: map coordinates and road legs between base campgrounds (OpenStreetMap routing)

Then run `./deploy.sh "message"`. It rebuilds and pushes. `python3 build.py` alone rebuilds locally.

## Pages
Overview, Itinerary, Map (layers, zoom by base, KML/GPX), Campgrounds, Contacts, and in planning mode the Planning section.

Calendar feed: `planning/springtime-kentucky-2028.ics` — subscribe with webcal:// so Apple or Google Calendar updates after each deploy.

Not indexed by search engines (`robots.txt` + `noindex`); share the link directly. Leaders are the only names on the site.

Airstream is a registered trademark of Airstream, Inc. All rights reserved.
