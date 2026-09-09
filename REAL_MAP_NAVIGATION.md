# Real Map Navigation extension

The original **AI Simulation** is still at `/`. The new **Real Map Navigation**
page is at `/real-map`. Use the navigation links at the top of either page.
They are ordinary page links: switching pages stops that page's automatic traffic
timer, while each backend mode retains its independent in-memory traffic and route.

## What is preserved

The existing `App.jsx`, simulation components, simulation CSS, fictional
`road_network.json`, six backend modules, UCS implementation, and original tests
are unchanged. Integration is limited to a frontend entry-point wrapper, one
FastAPI router registration, and the Leaflet dependency. No existing API endpoint
is replaced. No additional route-selection algorithm or routing service is used.

## Running both pages

The existing run instructions and launch scripts still apply. Install the updated
frontend dependencies with `npm install` inside `frontend`, then start the Python
backend on port 8000 and Vite on port 5173. Restart the backend if it was started
without `--reload`, so it registers the additional API router.

If using a local virtual environment on Windows:

```powershell
# From the repository root, after creating backend/.venv and installing requirements:
cd backend
.venv/Scripts/python.exe -m uvicorn app.api:app --reload --port 8000

# In another terminal, from the repository root:
cd frontend
npm install
npm run dev
```

No API key, paid mapping service, geocoding service, or GPS permission is required.
Browser internet access is needed for the OpenStreetMap background tiles. The
bundled road graph, routing, and traffic controls remain usable without tiles;
the page shows a clear background-map error in that case. A production web host
must serve `index.html` for `/real-map` and proxy `/api` to FastAPI, as Vite does.

## Road-data provenance and coverage

- Area: **Besant Nagar, Chennai, India**.
- Supported bounds: south **12.995**, west **80.260**, north **13.010**, east **80.278**.
- File: `backend/data/besant_nagar.osm.json` (approximately 184 KiB).
- Source: **© OpenStreetMap contributors**, licensed under the
  [Open Database License (ODbL)](https://www.openstreetmap.org/copyright).
- Retrieved on **2026-09-09** from the public
  [Kumi Overpass endpoint](https://overpass.kumi.systems/api/interpreter).
- The response reports a source-data timestamp of **2026-07-15T15:22:01Z**.
  The page displays this snapshot date; it does not claim fresh/live road data.
- The saved response contains 294 ways. After access filtering, clipping, and
  splitting, it produces **369 junctions and 472 graph road segments**.

The exact data query was:

```text
[out:json][timeout:25];
way["highway"~"^(primary|secondary|tertiary|residential|unclassified|living_street|service|primary_link|secondary_link|tertiary_link)$"]
(12.995,80.260,13.010,80.278);
out geom;
```

This fetches road data only. Overpass does not select a route. The snapshot is
loaded locally, so opening the page never downloads a city's road network or
depends on Overpass availability. Keep its attribution and licence information
when redistributing it or derived road data.

## How the same UCS engine is reused

```text
Saved OSM ways and node coordinates
  → access filtering and bounded road geometry
  → junctions + road segments
  → existing RoadNetwork and TrafficData
  → GeographicGraph (a small WeightedGraph direction adapter)
  → existing NavigationSession
  → existing uniform_cost_search in app/ucs_engine.py
  → road IDs and node path
  → matching road geometry, oriented in route direction
  → Leaflet polyline
```

Connectivity comes from shared **OSM node IDs**, not from roads appearing to cross
on a map. Shared junctions and way endpoints become graph nodes. Intermediate
shape vertices stay in road geometry, so a route follows the actual road curves.
Segments outside the bounds are excluded without joining across missing sections.
Restrictions for motorcars/motor vehicles/vehicles/access are checked; private,
destination-only, conditional, and other unsupported access values are omitted.

Explicit one-way directions, reverse one-way (`-1`) and roundabout defaults are
respected by filtering the inherited weighted adjacency entries. Parallel roads
are given distinct intermediate nodes where necessary, ensuring the existing
path-repricing function refers to an unambiguous road. No heuristic or external
shortest-path result is introduced.

The existing input validator retains its undirected structural reachability
precheck. This precheck never chooses a route: **UCS searches the directed graph**
and returns no-route where one-way restrictions prevent travel.

## Costs and simulated traffic

Every graph cost is in **whole minutes**, preserving the existing model:

```text
distance = sum of haversine distances along the road geometry, in km
base time = max(1, ceil(distance / 30 km/h × 60)) minutes
effective cost = base time + simulated traffic delay
```

| Traffic | Additional cost |
|---|---:|
| Low | 0 min |
| Medium | 5 min |
| High | 12 min |
| Blocked | Excluded from traversable adjacency |

The 30 km/h speed is an explicit modelling assumption, not a measured speed.
The minimum minute and upward rounding apply **per graph road segment**, including
segments split to distinguish parallel roads. This deliberately simple model can
inflate costs on dense junction networks; displayed values are **model travel
costs**, not live ETAs. The UI reports geographic road distance separately.

All roads start at low traffic. You can select any supported segment, apply any
of the four traffic states, trigger one random non-blocking change, or turn on
automatic changes every five seconds. A change goes through the existing
TrafficData observer mechanism and invokes UCS again from the **original selected
source**. There is no vehicle position or GPS tracking.

The old route is repriced under the updated traffic before comparing costs. A
cheaper route or a necessary alternative around a blockage replaces it. A small
real-map-only navigation subclass retains the previous UCS-selected route when a
fresh UCS search proves an alternative has exactly the same cost. It does not
implement another routing algorithm. The real-map service remembers selected
endpoints after a no-route result so reopening/resetting roads can recover a route.

## New API namespace

| Endpoint | Purpose |
|---|---|
| `GET /api/real-map/network` | Local road geometry, selectable junctions, costs, metadata, active route |
| `POST /api/real-map/route` | `{source, destination}` → validation and UCS |
| `POST /api/real-map/traffic` | `{roadId, traffic}` → update, graph change, UCS, comparison |
| `POST /api/real-map/simulate` | `{allowBlocking: false}` → random simulated change and rerouting |
| `POST /api/real-map/reset` | Restore low traffic and recalculate selected route |

One independently locked real-map session is held in memory. Requests serialize
traffic changes and route computation so a search sees a consistent set of costs.
The original `/api/network`, `/api/route`, `/api/traffic`, `/api/simulate`, and
`/api/reset` still use only their original fictional-network session. Like the
existing prototype, browser users of the same mode share its session; there are
no accounts, persistence, or per-user sessions. Restarting the backend resets it.

## Demonstrating it

1. Open **AI Simulation** and demonstrate the original College Main Gate → Railway
   Station route, UCS replay, traffic changes, and blockage exactly as before.
2. Open **Real Map Navigation**. The page starts with two named road-junction
   selections in Besant Nagar. Use the dropdowns or **Pick on map**. A click must
   be within 80 m of a supported junction; selection snaps to that junction.
3. Select **Find optimal route**. Inspect the blue route, geographic distance,
   cumulative model cost, and road-by-road arithmetic.
4. The traffic dropdown automatically selects the route's first road. Apply
   **High** traffic to demonstrate the repriced-old versus new UCS cost comparison.
5. Reset traffic, select **Blocked** on a route road, and apply it. UCS finds an
   alternative if one exists, or reports no route and removes the displayed route.
6. Reopen roads with **Low**, or reset traffic, to recover the selected route.
7. Try **Simulate change** and **Auto-simulate**. Some random changes leave the
   optimal route unchanged; this is an expected result, not a failure.
8. Return to **AI Simulation**: its traffic and active route were not changed by
   real-map operations. The full UCS trace/replay remains on that page.

## Validation

Run `backend/.venv/Scripts/python.exe -m pytest backend/tests -q` from the root,
or use `python -m pytest tests -q` in an activated backend environment.
Run `npm run build` in `frontend`.

The 71 original tests pass unchanged. The extension adds 26 tests covering the
actual snapshot, existing-UCS invocation, cost units, geometry reconstruction,
one-way directions, parallel roads, traffic updates, blocked/no-route recovery,
equal-cost route retention, unsupported inputs and data, API errors, and isolation
between both modes. New test-only geographic fixtures are explicitly synthetic;
the actual page loads the attributed OpenStreetMap snapshot.

## Boundaries and future work

This remains an academic navigation prototype. Routing is limited to the saved
area and filtered roads, even when other streets appear in the background tiles.
Turn restrictions, lane restrictions, temporary real closures, elevation, speed
profiles, live traffic feeds, global search/geocoding, GPS tracking, and continuous
vehicle-position rerouting are not implemented. The route can therefore differ
from a production driving route. None of these limitations change the role of UCS.

The renderer is [Leaflet 1.9.4](https://leafletjs.com/reference). OSM tiles use the
standard HTTPS URL, visible attribution, and normal browser caching/referrer
behaviour. There is no bulk tile download or offline tile archive. See the
[OpenStreetMap tile usage policy](https://operations.osmfoundation.org/policies/tiles/).
