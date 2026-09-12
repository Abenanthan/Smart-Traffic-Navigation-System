# Real Map Navigation

The original Graphical Simulation remains at `/`; the search-based map is at
`/real-map`. The original simulation UI, data, API behavior, core modules, UCS
implementation and teaching trace remain unchanged.

## Using the map

1. Search for a start and destination by name, address or city. Press Enter or
   Search, then select a result. Search is worldwide; results can be biased toward
   your location without being restricted to that area.
2. Alternatively, click Use my location to request a single browser position.
   Nearby areas, stations, hospitals and educational destinations appear by
   distance. Select one to set your destination. Without location permission,
   nearby suggestions use your selected start. Map picking is also supported.
3. Find optimal route downloads OSM roads around both selected coordinates and
   builds a new graph. UCS calculates the route and the map draws its road geometry.
4. Use the traffic panel to change road delays, block roads, or simulate changes.
   The same UCS engine reruns against that graph. Loading another trip starts a
   new traffic simulation. Rerouting uses the selected source, not a moving vehicle.

The interface starts with empty search fields rather than a fixed list of areas.
Each newly selected place hides the previous route until a new route is calculated.
Provider failures preserve selections and display an actionable error.

## Running

The existing launch scripts still apply: FastAPI on port 8000 and Vite on 5173.
Restart a backend that was started without `--reload` to register new endpoints.
No new dependencies or API keys are required. Backend internet access is required
for place search, nearby suggestions and new road downloads; browser internet
access is required for tiles. Once loaded, the graph supports local simulated
traffic/routing without another road download. The preserved Besant Nagar snapshot
continues to support legacy endpoints and regression tests, but does not populate
the new search fields or constrain new trips.

Location permission requires HTTPS or localhost. Denial, unavailable positions and
timeouts leave manual search and map selection usable. The browser requests a
fresh one-time location per click; no continuous GPS tracking is implemented.

## Providers and resource limits

- Search: [Photon](https://photon.komoot.io/), based on OpenStreetMap data.
- Roads and nearby places: [Overpass](https://wiki.openstreetmap.org/wiki/Overpass_API).
- Tiles/attribution: [OpenStreetMap contributors, ODbL](https://www.openstreetmap.org/copyright).

Search requests run only on an explicit Search/Enter action, never on each keypress.
Provider requests are serialized at least 1.1 seconds apart and cached in memory
for 15 minutes, capped at 32 entries / 24 MB of raw responses. There is no disk
cache or bulk tile download. A response is limited to 12 MB. A failed Overpass call
can try one alternate server. Public services may throttle requests and do not
provide an availability guarantee; use a dedicated provider for larger deployments.
Configuration is read at backend startup:

| Environment variable | Default |
| --- | --- |
| `PHOTON_URL` | `https://photon.komoot.io` |
| `OVERPASS_URL` | `https://overpass-api.de/api/interpreter` |
| `OVERPASS_FALLBACK_URL` | `https://overpass.kumi.systems/api/interpreter` |

Set the fallback to an empty string to disable it. Use a single backend worker for
this in-memory academic demo. Provider throttling, cache, and the active real-map
session are process-local. This is not a multi-user navigation server.

Search works worldwide. Road loading supports local/regional trips in arbitrary
areas, subject to 100 km straight-line separation, 2,500 km² bounding-box area,
30,000 OSM ways, 15,000 graph junctions, and 25,000 graph road segments. Very dense
areas may reach the graph limit sooner. Polar/date-line crossing trips are rejected.
The graph includes a 2 km margin around the selected pair. A detour outside it can
be missed; optimality is only over the downloaded graph, not every road worldwide.
No route is manufactured for missing roads, disconnected endpoints, or large trips.

## UCS integration

`POST /api/real-map/search` accepts `{query, bias?}` and returns named coordinates.
`POST /api/real-map/nearby` accepts `{latitude, longitude}` and returns nearby places.
`POST /api/real-map/trip` accepts `{source: {latitude, longitude}, destination: {...}}`.

The trip endpoint downloads road geometry only, builds the existing RoadNetwork,
TrafficData and WeightedGraph adapter, and calls the original `uniform_cost_search`.
No external directions service, A*, or alternative pathfinding implementation is
used. `DynamicNavigation` disables only the engine's existing optional trace
recording (`record_trace=False`) to avoid huge teaching snapshots for city graphs.
The original simulation retains full trace recording. Route construction, traffic
updates and cost comparisons reuse the existing navigation methods.

Shared OSM node IDs determine connectivity. Shape vertices near selected places
become endpoints so snapping does not require a distant junction. Raw selected
coordinates are matched to a usable departure/arrival node within 500 m. Snap
distances are shown explicitly. The route starts/ends at those road points; travel
between the place and snapped point is excluded. One-way direction, roundabouts
and conservative access filtering apply. Turn restrictions are not modeled.

Approximate trip times use distance / 30 km/h, stored in fractional minutes without
rounding individual road segments. Traffic multiplies each affected road's normal
time: low 1×, medium 1.5×, high 2.5×. Thus 1 km takes approximately 2, 3 or 5 minutes
respectively when the entire kilometre has that traffic level. Only display values
are rounded; UCS searches using the full positive travel-time weights. Blocked
roads remain excluded. The original fictional simulation and legacy saved-snapshot
endpoints retain their teaching costs. These are approximate estimates: signals,
stops, actual road speeds and live congestion are not included. Voice guidance and
continuous vehicle navigation are not implemented.

## Changes and validation

New: `backend/app/real_map/providers.py`, `dynamic_navigation.py`,
`backend/tests/test_dynamic_map.py`, and `frontend/src/components/RealMap/PlaceSearch.jsx`.
Updated: the real-map API, graph adapter, service, transport, page, scoped styles,
and Leaflet renderer. Original simulation files are unchanged.

Run `backend/.venv/Scripts/python.exe -m pytest backend/tests -q` from the root and
`npm run build` inside `frontend`. The suite includes the 71 original tests and
62 real-map tests. Tests cover new-region UCS reuse, coordinate snapping, one-way
roads, traffic, blocking/reopening, graph isolation, input limits, provider caching,
fallback, and nearby ordering. A live Bengaluru smoke check loaded 6,122 junctions
and 7,899 roads and routed between Cubbon Park and MG Road metro stations using UCS.

## Transport modes

Choose **Car**, **Two-wheeler** (motorcycle/scooter), or **Walking** before finding
a route. Mode is submitted as `transportMode` (`car`, `two_wheeler`, `walk`) to
`POST /api/real-map/trip`, validated by the backend and retained by the graph,
route and traffic updates. Car remains the default for older callers.

Assumed average speeds are 30, 35 and 5 km/h respectively. These are configurable
model constants in `travel_time.py`, not measured speeds or guarantees. For the
same 1 km route in low traffic this means 2 minutes, about 1.71 minutes and
12 minutes. Motor vehicles keep 1×/1.5×/2.5× traffic multipliers; walking has no
motor-congestion delay. Blocked ways remain unavailable for every mode.

Changing mode hides the prior estimate and pauses auto-simulation until Find
optimal route is selected. The graph is rebuilt for that mode and UCS searches
with its travel-time weights. Walking includes footways, pedestrian streets,
paths, tracks and steps; motorways and trunk roads are conservatively excluded.
OSM foot permissions and pedestrian one-way rules apply independently of vehicle
one-way rules. Motorcycles use motorcycle access overrides instead of motorcar
permissions. Conditional ways are conservatively excluded. Terrain, barriers,
turn restrictions and jurisdiction-specific defaults are not fully modeled.

Sources for access tagging: [OSM foot](https://wiki.openstreetmap.org/wiki/Key:foot),
[OSM oneway:foot](https://wiki.openstreetmap.org/wiki/Key:oneway:foot), and
[OSM motorcycle](https://wiki.openstreetmap.org/wiki/Key:motorcycle).

Validation: 147 backend tests pass, including mode-specific ETA, access,
one-way behavior, pedestrian traffic/blocking, provider queries and API contracts.
Browser checks use deterministic test fixtures generated by the actual service.

## Provider loading recovery

Provider downloads no longer hold the shared cache lock. Requests are serialized
per provider host, with at most a 4-second local queue wait, so a slow nearby lookup
cannot hold all route downloads and search requests. Overpass queries ask for a
15-second execution budget; HTTP connect/read limits are 5/22 seconds. The UI stops
waiting for a trip after 65 seconds and restores the controls with a retry message.

All server caches are checked before downloads. The last successful Overpass host
is preferred for new requests; failed servers cool down for 60 seconds. An occupied
host is revisited once after the alternate attempt, without marking it as failed.
Oversized downloads do not trigger a duplicate download from the alternate server.
Provider outages can still prevent uncached trips, but selections are retained.
Only raw successful provider responses are cached; UCS still calculates each route.
