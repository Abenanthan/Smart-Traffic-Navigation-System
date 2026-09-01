# Smart Traffic Navigation System

An academic project for **Foundations of Artificial Intelligence**.

The system represents a road network as a weighted graph and uses **Uniform Cost Search**
to find the least-cost route between two locations. When traffic conditions change, edge
costs change, the graph updates, the search runs again, and navigation is updated.

```
ROAD NETWORK + TRAFFIC CONDITIONS
            ↓
      WEIGHTED GRAPH
            ↓
   UNIFORM COST SEARCH
            ↓
    LEAST-COST ROUTE
            ↓
   DYNAMIC REROUTING
            ↓
  OPTIMAL NAVIGATION
```

> **Traffic data is simulated.** This system does not receive live traffic from Google Maps
> or any other commercial service, and does not claim to. Traffic levels are set from a data
> file and changed by the user. The architecture keeps traffic behind a single interface
> (`TrafficData`) so that a real feed could be introduced later without altering the search;
> that is listed under Future Enhancements, not as something already built.

---

## Running it

### The AI core, on its own — no interface, no dependencies

Two windows. On Windows, double-click `run_backend.bat`, then `run_frontend.bat`.
Otherwise:

```bash
# The routing engine
cd backend
pip install -r requirements.txt
python -m uvicorn app.api:app --reload --port 8000

# The dashboard
cd frontend
npm install
npm run dev
```

Then open **http://localhost:5173**.

---

## The six modules

Each module in the specification is one file. All six work without the interface.

| # | Module | File | Responsibility |
|---|--------|------|----------------|
| 1 | Input Processing | [`backend/app/input_processing.py`](backend/app/input_processing.py) | Validate the source and destination before any search runs |
| 2 | Road Network | [`backend/app/road_network.py`](backend/app/road_network.py) | The static network: locations, roads, connections |
| 3 | Traffic Data | [`backend/app/traffic_data.py`](backend/app/traffic_data.py) | Simulated congestion, the delay model, road closures |
| 4 | Weighted Graph | [`backend/app/weighted_graph.py`](backend/app/weighted_graph.py) | Network + traffic → costed edges |
| 5 | **UCS AI Engine** | [`backend/app/ucs_engine.py`](backend/app/ucs_engine.py) | **Uniform Cost Search — the core AI module** |
| 6 | Optimal Navigation | [`backend/app/navigation.py`](backend/app/navigation.py) | Route presentation and the rerouting decision |

`api.py` and the whole of `frontend/` are presentation. They contain no routing logic:
every decision is made in Python and arrives at the browser already decided.

---

## The cost model

```
edge cost = base travel time + traffic delay
```

| Traffic level | Delay added |
|---------------|-------------|
| Low | +0 min |
| Medium | +5 min |
| High | +12 min |
| Blocked | road removed from the graph |

A blocked road is **not** given a large cost — it is excluded from the graph entirely. An
expensive road is still an available action and a search would take it if nothing else
existed; a closed road is not an available action at all. This is why the system can report
"No route available" correctly rather than routing traffic down a closed road.

---

## The road network

16 locations and 24 bidirectional roads, defined in
[`backend/data/road_network.json`](backend/data/road_network.json).

There are **182 distinct simple routes** from College Main Gate to Railway Station, so the
demonstration is not a graph with one obvious path. Two locations — Pelican Island Jetty and
Island Fishing Village — form a separate component reachable only by ferry, which gives a
permanent "no route" case; and Hilltop Observatory is served by a single road, so blocking it
creates a second, dynamic one.

---

## Demonstration script for a viva

1. **Baseline.** College Main Gate → Railway Station. The route is
   `A → C → F → N → I → K` at **35 min**. The route table shows the arithmetic leg by leg,
   and every number on it matches a number drawn on the map.

2. **Show the search.** Step through the UCS panel. At each step the node being expanded
   lights up on the map, nodes still in the priority queue are labelled with their
   cumulative cost, and obsolete queue entries are struck through. Note that the destination
   K enters the queue at step 9 but is not accepted until step 17 — that gap is the goal test
   doing its work.

3. **Congestion.** Set road **R18** (Old Town Square – Railway Station) to **High**. The
   route being followed would now cost 42 min; the search finds `A → C → E → H → J → K` at
   **39 min** and reroutes, showing the 42 → 39 comparison.

4. **Blockage.** Set road **R02** (College Main Gate – Market Junction) to **Blocked**. The
   road disappears from the graph and the route becomes `A → B → D → L → K` at **40 min**.

5. **No route.** Choose Island Fishing Village as the destination — no road joins it to the
   mainland. For contrast, Pelican Island Jetty → Island Fishing Village succeeds at 4 min,
   which shows the failure is a genuine disconnection rather than a defect in the search.

6. **The point about the goal test.** Run `python demo_cli.py 3`. On College Main Gate →
   Sports Stadium, testing the goal at generation instead of at expansion returns a route
   6 minutes worse. The two versions disagree on 31 of the 182 ordered location pairs.

---

## A note on UCS and Dijkstra's algorithm

On a finite graph with non-negative edge weights, UCS and Dijkstra's algorithm expand nodes
in the same order and belong to the same algorithmic family. The difference is one of
formulation. UCS is posed as a **state-space search** for a single goal: it terminates as
soon as the goal is expanded and never builds the full shortest-path tree. Dijkstra's is
normally posed as a single-source shortest-path computation over the whole graph.

This project implements the search formulation, per Russell & Norvig, *Artificial
Intelligence: A Modern Approach* — an explicit priority queue ordered on g(n), no heuristic,
the goal test performed on expansion, and no shortest-path library anywhere. Stating the
relationship honestly is a better answer than pretending the two are unrelated.

---

## Project layout

```
Smart Traffic Navigation Sysytem/
├── README.md
├── run_backend.bat  /  run_frontend.bat
├── docs/
│   └── PROJECT_REPORT.md          full report (21 sections)
├── backend/
│   ├── requirements.txt
│   ├── demo_cli.py                the whole system, in the terminal
│   ├── data/road_network.json     16 locations, 24 roads
│   ├── app/                       the six modules + the HTTP layer
│   └── tests/                     71 tests
└── frontend/                      React + Vite dashboard
    └── src/components/            graph, panels, UCS visualisation
```

Full documentation, including the AI problem formulation, pseudocode, activity diagrams,
test results and limitations, is in [`docs/PROJECT_REPORT.md`](docs/PROJECT_REPORT.md).
