# Springtime in Kentucky 2028

Planning site for a spring 2028 Airstream caravan through Kentucky, led by Colleen and Steve Thorsen.

- **Caravan:** Sat April 29 – Sat May 20, 2028 (22 nights)
- **Kentucky Derby:** Sat May 6, 2028, day 8 of the trip
- **Farewell:** Sun May 21, 2028

Skeleton only so far: dates and Derby Day are set; stops, campgrounds and routes are still to be chosen.

## Editing
All content lives in `data/`:
- `trip.json`: dates, leaders, fixed events, and the stop order as `[stop_id, nights]`
- `stops.json`: places, activities, campground candidates (copy the `_example` entry)
- `decisions.json`: settled and open questions
- `routes.json`: road mileage and geometry between stops (optional; missing legs show "TBD")

Then run `./deploy.sh "message"`. It rebuilds and pushes. `python3 build.py` alone rebuilds locally.

## Pages
Overview (calendar strip with Derby Day), Itinerary, Route map (KML/GPX downloads once stops exist), Campgrounds, Decisions.

Not indexed by search engines (`robots.txt` + `noindex`); share the link directly. Leaders are the only names on the site.
