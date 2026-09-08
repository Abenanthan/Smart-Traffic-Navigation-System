# Smart Traffic Navigation System

### A Uniform Cost Search approach to least-cost route selection under changing traffic conditions

**Course:** Foundations of Artificial Intelligence
**Project type:** Academic demonstration of state-space search

---

> **Scope statement.** Traffic conditions in this system are **simulated**. The system does
> not receive live traffic data from Google Maps or any other commercial service, and makes
> no claim to. The architecture isolates traffic behind a single interface so that a real
> feed could be introduced later without changing the search algorithm; that possibility is
> recorded in *Future Enhancements* (§20), not presented as implemented work.

---

## Table of contents

1. [Problem Statement](#1-problem-statement)
2. [Objectives](#2-objectives)
3. [Existing System](#3-existing-system)
4. [Literature Survey](#4-literature-survey)
5. [Proposed System](#5-proposed-system)
6. [System Architecture](#6-system-architecture)
7. [Module Description](#7-module-description)
8. [Input–Process–Output for Every Module](#8-inputprocessoutput-for-every-module)
9. [Activity Diagrams](#9-activity-diagrams)
10. [Flowcharts](#10-flowcharts)
11. [AI Problem Formulation](#11-ai-problem-formulation)
12. [The UCS Algorithm](#12-the-ucs-algorithm)
13. [UCS Pseudocode](#13-ucs-pseudocode)
14. [Cost Function](#14-cost-function)
15. [Traffic Simulation](#15-traffic-simulation)
16. [Dynamic Rerouting](#16-dynamic-rerouting)
17. [Test Cases](#17-test-cases)
18. [Results](#18-results)
19. [Limitations](#19-limitations)
20. [Future Enhancements](#20-future-enhancements)
21. [Conclusion](#21-conclusion)

---

## 1. Problem Statement

A traveller wishing to go from one place in a city to another usually has many possible
routes. The shortest route by distance is often not the fastest, because travel time depends
on congestion as much as on length. Congestion is not static: it builds and clears during a
journey, and roads close without warning. A route chosen at departure may no longer be the
best route ten minutes later.

The problem this project addresses is therefore:

> Given a road network in which each road has a travel cost that depends on current traffic
> conditions, find the route of least total cost between a source and a destination; and when
> those conditions change, recognise whether the route being followed is still the best one
> and replace it if it is not.

Stated in the vocabulary of artificial intelligence, this is a **least-cost path problem in a
state space with non-uniform, time-varying action costs**. It is a natural application of
uninformed search: the road network is the state space, moving along a road is an action, the
cost of that action is a travel time, and the task is to find the minimum-cost sequence of
actions from an initial state to a goal state.

---

## 2. Objectives

**Primary objective.** To design and implement an AI-based navigation system that represents
a road network as a weighted graph and applies **Uniform Cost Search** to find the least-cost
route between a source and a destination.

**Specific objectives.**

1. Represent a road network as a weighted graph in which locations are nodes and roads are
   edges.
2. Formulate route selection as a state-space search problem with a clearly stated initial
   state, goal test, transition model and path cost function.
3. Define a cost function that combines base travel time with a traffic-dependent delay.
4. Implement Uniform Cost Search explicitly, from first principles, with no heuristic and no
   shortest-path library.
5. Demonstrate that the route returned is genuinely of minimum cumulative cost, by checking
   it against an exhaustive enumeration of all possible routes.
6. Simulate changing traffic conditions and propagate their effect through edge costs into
   the graph.
7. Recalculate the route when conditions change, and update navigation when the previous
   route is no longer optimal or has become unusable.
8. Make the search itself observable, so that an evaluator can see the priority queue, the
   expansion order and the reasoning behind the chosen route.

**Explicit non-objectives.** This is not a mapping product. It does not use real geography,
real-time traffic, satellite positioning, or turn-by-turn guidance. Adding those would
increase the apparent sophistication of the system while contributing nothing to the AI
content, which is the point of the exercise.

---

## 3. Existing System

**Manual route selection.** A traveller chooses a route from memory or habit. This requires
no system at all, but cannot account for conditions the traveller cannot see, and does not
scale to unfamiliar networks.

**Static shortest-path systems.** Early routing software computed the shortest route by
distance from a fixed map. These systems are deterministic and fast, but a route optimal in
distance may be far from optimal in time, and they cannot respond to changing conditions at
all.

**Commercial navigation services.** Modern services combine map data with live traffic
estimates derived from aggregated device positions and historical models, and re-route
continuously. They are highly effective, but from an academic standpoint they have three
drawbacks as objects of study:

- their routing algorithms and cost models are proprietary and not inspectable;
- their decisions cannot be reproduced or verified independently;
- the search is entirely hidden, so nothing can be learned from watching one operate.

**The gap this project fills.** What is missing is a system in which the *entire* decision
process is visible and checkable: the cost of every road, the state of the priority queue at
every step, the order in which locations were examined, and the arithmetic that makes the
chosen route cheapest. That is the system built here. Its value is not that it routes better
than a commercial service — it does not — but that every step of its reasoning can be
inspected and verified by hand.

---

## 4. Literature Survey

**Russell, S. and Norvig, P., *Artificial Intelligence: A Modern Approach*.**
The standard treatment of problem-solving agents and uninformed search. Uniform Cost Search
is presented as best-first search with the evaluation function f(n) = g(n), the cumulative
path cost. Two properties are established that this project depends on directly: UCS is
**complete** when every edge cost is bounded below by some ε > 0, and **optimal**, because it
expands nodes in non-decreasing order of path cost. The text is explicit that the goal test
must be applied when a node is *selected for expansion* rather than when it is *generated*,
and gives the standard counter-example showing that testing at generation forfeits
optimality. This project follows that formulation exactly, and reproduces the counter-example
on its own network (§18).

**Dijkstra, E. W. (1959), "A note on two problems in connexion with graphs."**
The original single-source shortest-path algorithm. On a finite graph with non-negative
weights, UCS and Dijkstra's algorithm expand vertices in the same order; the difference is
one of formulation and termination, discussed in §12. This project implements the search
formulation.

**Hart, P. E., Nilsson, N. J. and Raphael, B. (1968), "A Formal Basis for the Heuristic
Determination of Minimum Cost Paths."**
Introduces A*, which extends UCS with an admissible heuristic h(n), evaluating
f(n) = g(n) + h(n). A* expands fewer nodes when a good heuristic exists. It is deliberately
**not** used here: the project's purpose is to demonstrate uninformed search, and adding a
heuristic would change the algorithm being demonstrated. A comparison with A* is listed as
future work (§20).

**Traffic-aware and time-dependent routing.** A body of work addresses shortest paths where
edge weights vary with time, showing that the standard label-setting approach remains valid
under a "first-in, first-out" assumption on travel times. The model used in this project is
simpler: costs are static during any single search and change only between searches, so each
individual search is an ordinary least-cost path problem. This is a real simplification and
is recorded as such in §19.

**What the survey establishes for this project.** UCS is the correct algorithm for a
least-cost path problem with varying, non-negative action costs and no reliable heuristic;
its optimality depends on the placement of the goal test; and its treatment of a changing
environment by recomputation is sound provided costs are constant within a single search.

---

## 5. Proposed System

The proposed system treats navigation as a search problem over a weighted graph whose edge
weights are supplied by an environment that changes.

**The chain of reasoning.**

```
traffic condition  →  traffic delay  →  edge cost  →  weighted graph
                                                            ↓
                                                  Uniform Cost Search
                                                            ↓
                                                    route decision
```

**What is, and is not, intelligent here.** The system does not predict traffic; traffic is
environmental input. The intelligence lies in the search: given a state space with costed
actions, UCS determines the optimal action sequence to reach the goal. Traffic changes the
costs; the search re-derives the optimal plan. This division — environment supplies costs,
search supplies decisions — is the standard structure of a problem-solving agent, and keeping
it clean is what allows the traffic source to be replaced later without touching the search.

**What makes the system dynamic.**

```
traffic changes  →  edge costs change  →  graph updates  →  UCS runs again
                                                                  ↓
                                                    navigation is updated
```

**Distinguishing features.**

- The search is implemented from first principles, not delegated to a library.
- The search emits a complete trace of its own execution, so its reasoning is observable.
- Its output is verified against exhaustive enumeration of all possible routes.
- Blocked roads are removed from the state space rather than made expensive, so
  unreachability is reported correctly.
- Rerouting compares the current route re-priced under *new* conditions against the new
  search result, rather than against a stale figure.

---

## 6. System Architecture

```
                        ┌──────────────────┐
                        │       USER       │
                        └────────┬─────────┘
                                 │ source, destination, traffic changes
                                 ▼
                  ╔══════════════════════════════╗
                  ║  MODULE 1  INPUT PROCESSING   ║
                  ║  validate before searching    ║
                  ╚══════════════┬═══════════════╝
                                 │ validated route request
                                 ▼
      ╔══════════════════╗              ╔══════════════════╗
      ║ MODULE 2         ║              ║ MODULE 3         ║
      ║ ROAD NETWORK     ║              ║ TRAFFIC DATA     ║
      ║ locations, roads,║              ║ simulated levels,║
      ║ base travel time ║              ║ delays, closures ║
      ╚════════┬═════════╝              ╚════════┬═════════╝
               │  structure                      │  conditions
               └───────────────┬─────────────────┘
                               ▼
                  ╔══════════════════════════════╗
                  ║  MODULE 4  WEIGHTED GRAPH     ║
                  ║  cost = base time + delay     ║
                  ║  blocked roads excluded       ║
                  ╚══════════════┬═══════════════╝
                                 │ costed adjacency
                                 ▼
                  ╔══════════════════════════════╗
                  ║  MODULE 5  UCS AI ENGINE      ║
                  ║  priority queue on g(n)       ║
                  ║  goal test on expansion       ║
                  ╚══════════════┬═══════════════╝
                                 │ least-cost path, cost, trace
                                 ▼
                  ╔══════════════════════════════╗
                  ║  MODULE 6  OPTIMAL NAVIGATION ║
                  ║  present route, decide on     ║
                  ║  rerouting                    ║
                  ╚══════════════┬═══════════════╝
                                 ▼
                        ┌──────────────────┐
                        │       USER       │
                        └──────────────────┘

        ┌───────────────────────────────────────────────────┐
        │  Feedback loop: a traffic change in Module 3      │
        │  notifies Module 4, which re-costs the affected   │
        │  edges; Module 6 then re-invokes Module 5 and     │
        │  decides whether to change route.                 │
        └───────────────────────────────────────────────────┘
```

**Implementation architecture.**

| Layer | Technology | Responsibility |
|-------|-----------|----------------|
| AI core | Python 3 (standard library only) | All six modules; fully usable without any interface |
| Service layer | FastAPI | Exposes the modules over HTTP; contains no logic |
| Interface | React + Vite, hand-written SVG | Displays the graph, the route and the search trace |
| Data | JSON | The road network definition |

The dependency direction is strictly one-way: the interface depends on the service layer,
which depends on the core; the core depends on nothing. `demo_cli.py` exercises the entire
system with no web server and no browser, which is the practical proof of that separation.

---

## 7. Module Description

### Module 1 — Input Processing
**File:** `backend/app/input_processing.py`

The gate in front of the search. Everything downstream may assume that the source and
destination are real, distinct locations, and that assumption is established here and nowhere
else. Accepts either a location id (`K`) or its full name (`Railway Station`),
case-insensitively.

Its final check deserves emphasis: before any search runs, a breadth-first reachability test
asks whether a route could exist *at all*. This separates two outcomes that look identical to
a user but differ entirely in nature — "the destination cannot be reached", a property of the
network, versus "the search failed", a property of the algorithm. It also distinguishes two
causes of unreachability, and says which applies: the locations are in separate parts of the
network, or the roads exist but are all currently blocked.

### Module 2 — Road Network
**File:** `backend/app/road_network.py`

The static description of the city: locations as nodes, roads as edges, with distance and
base travel time. It knows nothing about congestion and nothing about search. Stored as an
adjacency map so that neighbour lookup — the operation the search performs most often — costs
O(degree) rather than a scan of every road. Also provides the structural analysis used
elsewhere: reachability, connected components, and node degrees.

Roads are **bidirectional**: one road produces two directed adjacency entries of equal cost.
The loader rejects self-loops, unknown endpoints, duplicate identifiers, and non-positive
travel times — the last because a zero-cost edge would permit cost-free cycles.

### Module 3 — Traffic Data
**File:** `backend/app/traffic_data.py`

The authoritative and *only* source of congestion information. Converts a traffic level into
a delay in minutes, detects blocked roads, applies user updates, and notifies dependent
structures when a road's condition changes.

Congestion (`TrafficLevel`) and physical closure (`RoadStatus`) are modelled as separate
fields on purpose — a road can be jammed but usable, or empty but shut for repairs. Either
being "blocked" makes the road untraversable.

Because every other module asks this one rather than deciding for itself, replacing simulated
traffic with a live feed means changing the source of update calls and nothing else. That is
the concrete content of the claim that the design admits future integration.

### Module 4 — Weighted Graph
**File:** `backend/app/weighted_graph.py`

Where the static network and the dynamic environment combine into the single structure the
search runs on. Each traversable road contributes two directed edges carrying
`base travel time + traffic delay`. The graph subscribes to traffic updates at construction,
so a congestion change is reflected in the affected edges before the next search runs, and
only those two edges are rebuilt.

A blocked road is **omitted from the adjacency structure**, not given a large cost. The
distinction is not cosmetic: an expensive edge is still an available action and a search
would take it if nothing else existed, whereas a blocked road is not an available action at
all. Modelling closure as absence from the state space is what allows the system to report
unreachability correctly.

This module also provides `path_cost`, which prices an arbitrary path under current
conditions and returns nothing if any step has become impossible. Module 6 depends on it for
the rerouting comparison.

### Module 5 — UCS AI Engine
**File:** `backend/app/ucs_engine.py` — **the core AI module**

Uniform Cost Search, implemented from first principles. No shortest-path library is called
and no heuristic appears anywhere. Its only requirement of a graph is the ability to list the
traversable edges leaving a node, each already priced — so the search knows nothing about
minutes, congestion or closures. It sees numbers on edges. That narrowness is what allows
traffic to become dynamic without the algorithm changing at all.

The engine records a complete trace of its own execution while it runs: at every removal from
the priority queue, the node removed, its cumulative cost, the queue contents, the set of
locations already expanded, and every neighbour considered with the reason it was kept or
rejected. The visualisation displays this trace directly, so what is shown is what the search
actually did rather than a reconstruction.

The module also contains `ucs_with_goal_test_on_generation` — a deliberately incorrect
variant, kept solely for demonstration, which returns as soon as the goal is first
*discovered*. Running the two side by side turns an abstract point about algorithm design
into a concrete pair of routes with different costs (§18).

### Module 6 — Optimal Navigation
**File:** `backend/app/navigation.py`

Presents the route — path, cost, distance, per-leg arithmetic, worst congestion encountered,
locations explored — and holds the route currently being followed. On any traffic change it
re-prices that route under the new conditions, re-runs the search, compares the two, and
classifies the outcome as one of: initial route, unchanged, a cheaper route found, the route
blocked, or no route available. It is the only place in the system where the decision to
change route is made.

---

## 8. Input–Process–Output for Every Module

### Module 1 — Input Processing

| | |
|---|---|
| **Input** | Source location; destination location (as an id or a name) |
| **Process** | 1. Accept the source. 2. Accept the destination. 3. Check neither is empty. 4. Check the source exists in the network. 5. Check the destination exists. 6. Check they are not the same location. 7. Check by breadth-first search that a route could exist. 8. On failure, report which field to correct and why. 9. On success, build a route request. 10. Forward it to the routing system. |
| **Output** | A validated source and destination, or a specific error |

### Module 2 — Road Network

| | |
|---|---|
| **Input** | Locations, junctions, roads, connections, distances, base travel times |
| **Process** | Represent each location as a node; each road as an edge; store distance and base travel time; maintain the adjacency between nodes; support roads being open or blocked; reject malformed data |
| **Output** | A structured road network supporting neighbour, reachability and component queries |

### Module 3 — Traffic Data

| | |
|---|---|
| **Input** | The traffic condition of each road; road status; traffic updates from the user or the simulator |
| **Process** | Determine each road's traffic level; convert the level into a delay in minutes; detect blocked roads; apply updates; notify the graph that a road's condition has changed |
| **Output** | The current traffic cost and status of every road |

### Module 4 — Weighted Graph

| | |
|---|---|
| **Input** | The road network; base travel times; traffic delays; road statuses |
| **Process** | Map locations to nodes and roads to edges; compute `cost = base travel time + traffic delay`; give each bidirectional road two directed edges; exclude untraversable roads; rebuild affected edges when notified of a traffic change |
| **Output** | A weighted graph carrying current road costs |

### Module 5 — UCS AI Engine

| | |
|---|---|
| **Input** | The weighted graph; the source; the destination |
| **Process** | The twelve steps of Uniform Cost Search (§12), with priority equal to cumulative path cost and the goal test performed on expansion |
| **Output** | The least-cost route; its total cost; the locations explored, in order; the parent map for path reconstruction; the full expansion trace |

### Module 6 — Optimal Navigation

| | |
|---|---|
| **Input** | The route returned by UCS; its total cost; current traffic information |
| **Process** | Display the route and highlight it on the graph; show total cost, travel time and traffic conditions; on a traffic change, re-price the active route under new conditions, re-run UCS, compare, and switch route if the new one is cheaper or the old one is unusable |
| **Output** | The optimal navigation route; the updated route after a change; route statistics; a rerouting notification with its reason |

---

## 9. Activity Diagrams

### Activity 1 — Finding a route

```
      ( start )
          │
          ▼
   ┌─────────────────┐
   │ accept source & │
   │  destination    │
   └────────┬────────┘
            ▼
      ╱───────────╲          no    ┌──────────────────┐
     ╱ both fields  ╲───────────── │ report empty     │──┐
     ╲  provided?   ╱              │ field            │  │
      ╲───────────╱                └──────────────────┘  │
            │ yes                                        │
            ▼                                            │
      ╱───────────╲          no    ┌──────────────────┐  │
     ╱ both exist   ╲───────────── │ report unknown   │──┤
     ╲ in network?  ╱              │ location         │  │
      ╲───────────╱                └──────────────────┘  │
            │ yes                                        │
            ▼                                            │
      ╱───────────╲         yes    ┌──────────────────┐  │
     ╱ source ==    ╲───────────── │ report same      │──┤
     ╲ destination? ╱              │ location         │  │
      ╲───────────╱                └──────────────────┘  │
            │ no                                         │
            ▼                                            │
      ╱───────────╲          no    ┌──────────────────┐  │
     ╱ reachable    ╲───────────── │ report "no route │──┤
     ╲ (BFS check)? ╱              │ available"       │  │
      ╲───────────╱                └──────────────────┘  │
            │ yes                                        │
            ▼                                            ▼
   ┌─────────────────┐                          ┌────────────────┐
   │ build weighted  │                          │ ask user to    │
   │ graph from      │                          │ correct input  │
   │ network+traffic │                          └────────┬───────┘
   └────────┬────────┘                                   │
            ▼                                            │
   ┌─────────────────┐                                   │
   │ run UCS         │                                   │
   └────────┬────────┘                                   │
            ▼                                            │
      ╱───────────╲          no    ┌──────────────────┐  │
     ╱ route found? ╲───────────── │ "no route        │──┤
     ╲             ╱               │  available"      │  │
      ╲───────────╱                └──────────────────┘  │
            │ yes                                        │
            ▼                                            │
   ┌─────────────────┐                                   │
   │ display route,  │                                   │
   │ cost, trace     │                                   │
   └────────┬────────┘                                   │
            ▼                                            ▼
        ( end )                                      ( end )
```

### Activity 2 — Reacting to a traffic change

```
      ( start: user changes a road's traffic level )
                        │
                        ▼
            ┌────────────────────────┐
            │ Module 3 records the   │
            │ new level and status   │
            └───────────┬────────────┘
                        ▼
                  ╱───────────╲       no     ┌──────────────┐
                 ╱ did anything ╲──────────── │ do nothing   │──┐
                 ╲   change?    ╱             └──────────────┘  │
                  ╲───────────╱                                 │
                        │ yes                                   │
                        ▼                                       │
            ┌────────────────────────┐                          │
            │ Module 3 notifies      │                          │
            │ Module 4               │                          │
            └───────────┬────────────┘                          │
                        ▼                                       │
            ┌────────────────────────┐                          │
            │ re-cost the two edges  │                          │
            │ of that road only      │                          │
            └───────────┬────────────┘                          │
                        ▼                                       │
                  ╱───────────╲       no     ┌──────────────┐   │
                 ╱ is a route   ╲──────────── │ report the   │───┤
                 ╲ being        ╱             │ change only  │   │
                  ╲ followed?  ╱              └──────────────┘   │
                        │ yes                                    │
                        ▼                                        │
            ┌────────────────────────┐                           │
            │ RE-PRICE the active    │  ◄── the step that makes  │
            │ route under NEW costs  │      the comparison valid │
            └───────────┬────────────┘                           │
                        ▼                                        │
            ┌────────────────────────┐                           │
            │ run UCS again          │                           │
            └───────────┬────────────┘                           │
                        ▼                                        │
                  ╱───────────╲       no     ┌──────────────┐    │
                 ╱ route found? ╲──────────── │ "no route    │────┤
                 ╲             ╱              │  available"  │    │
                  ╲───────────╱               └──────────────┘    │
                        │ yes                                     │
                        ▼                                         │
                  ╱─────────────╲     yes    ┌───────────────┐    │
                 ╱ old route now  ╲───────── │ "Route Updated│    │
                 ╲  impassable?   ╱          │ — road blocked│────┤
                  ╲─────────────╱            └───────────────┘    │
                        │ no                                      │
                        ▼                                         │
                  ╱─────────────╲     no     ┌───────────────┐    │
                 ╱ new cost <     ╲───────── │ "Route        │────┤
                 ╲ re-priced old? ╱          │  unchanged"   │    │
                  ╲─────────────╱            └───────────────┘    │
                        │ yes                                     │
                        ▼                                         │
            ┌────────────────────────┐                            │
            │ "Route Updated" +      │                            │
            │ show old → new cost    │                            │
            └───────────┬────────────┘                            │
                        ▼                                         ▼
                    ( end )                                   ( end )
```

---

## 10. Flowcharts

### Flowchart 1 — Uniform Cost Search

```
                    ( start )
                        │
                        ▼
        ┌───────────────────────────────┐
        │ frontier ← empty priority queue│
        │ push (source, cost 0)          │
        │ best[source] ← 0               │
        │ parent[source] ← none          │
        │ explored ← { }                 │
        └───────────────┬───────────────┘
                        │
                        ▼
                  ╱───────────╲     yes   ┌──────────────────────┐
                 ╱ frontier     ╲───────► │ return FAILURE:      │
                 ╲   empty?     ╱         │ "no route available" │
                  ╲───────────╱           └──────────┬───────────┘
                        │ no                         │
                        ▼                            ▼
        ┌───────────────────────────────┐        ( end )
        │ (node, g) ← remove the entry  │
        │ with the LOWEST cumulative    │
        │ cost from the frontier        │
        └───────────────┬───────────────┘
                        ▼
                  ╱───────────────╲    yes   ┌──────────────────┐
                 ╱ node already     ╲──────► │ discard this     │──┐
                 ╲ expanded, or g >  ╱       │ obsolete entry   │  │
                  ╲ best[node]?     ╱        └──────────────────┘  │
                        │ no                                       │
                        ▼                                          │
                  ╱───────────────╲    yes   ┌──────────────────┐  │
                 ╱ node ==          ╲──────► │ reconstruct path │  │
                 ╲ destination?     ╱        │ via parent map;  │  │
                  ╲───────────────╱          │ return path, g   │  │
                        │ no                 └────────┬─────────┘  │
                        ▼                             ▼            │
        ┌───────────────────────────────┐         ( end )          │
        │ add node to explored          │                          │
        └───────────────┬───────────────┘                          │
                        ▼                                          │
        ┌───────────────────────────────┐                          │
        │ for each traversable edge     │                          │
        │ (node → neighbour):           │                          │
        │                               │                          │
        │   if neighbour explored: skip │                          │
        │   new_g ← g + edge cost       │                          │
        │   if new_g < best[neighbour]: │                          │
        │       best[neighbour] ← new_g │                          │
        │       parent[neighbour] ← node│                          │
        │       push (neighbour, new_g) │                          │
        └───────────────┬───────────────┘                          │
                        │                                          │
                        └──────────────────────────────────────────┘
                                    (loop)
```

**The decision that matters.** The goal test sits *after* the node has been removed from the
queue, not inside the loop that generates neighbours. Moving it into that loop would produce
a search that returns the first path it finds to the destination rather than the cheapest —
see §18 for what that costs on this network.

### Flowchart 2 — Overall system flow

```
   USER
     │  selects source and destination
     ▼
   INPUT PROCESSING ──── invalid ────► show the error, ask again
     │  valid
     ▼
   ROAD NETWORK  +  TRAFFIC DATA
     │            (structure)  (conditions)
     ▼
   WEIGHTED GRAPH        cost = base travel time + traffic delay
     │                   blocked roads excluded from the graph
     ▼
   UCS AI ENGINE         priority queue ordered on g(n)
     │                   goal test on expansion
     ▼
   OPTIMAL NAVIGATION    route, cost, statistics, trace
     │
     ▼
   USER
     │
     │  ◄──────────────────────────────────────────────┐
     │  changes a road's traffic level                  │
     ▼                                                  │
   UPDATE TRAFFIC COST ──► UPDATE WEIGHTED GRAPH        │
                                    │                   │
                                    ▼                   │
                              RUN UCS AGAIN             │
                                    │                   │
                                    ▼                   │
                        NEW LEAST-COST ROUTE            │
                                    │                   │
                                    ▼                   │
                          UPDATE NAVIGATION ────────────┘
```

---

## 11. AI Problem Formulation

The routing task is formulated as a classical search problem.

| Component | Definition in this system |
|-----------|---------------------------|
| **Initial state** | The user's selected source location, e.g. `A` (College Main Gate) |
| **Goal state** | The destination location, e.g. `K` (Railway Station) |
| **State space** | The set of locations and junctions in the road network — 16 states |
| **Actions** | From a location, travel along any traversable road to a directly connected location. The actions available in state *s* are exactly the open roads at *s* |
| **Transition model** | `RESULT(s, travel road r) = the location at the other end of r`. Traversing a road changes the current location and nothing else |
| **Action cost** | `c(s, r, s') = base travel time of r + traffic delay on r`, always > 0 |
| **Path cost** | `g(n)` = the sum of the action costs along the path from the initial state to *n*; additive, and non-decreasing along any path |
| **Goal test** | `current location == destination`, applied when a node is selected for expansion |
| **Solution** | A sequence of roads leading from source to destination |
| **Optimal solution** | The such sequence of minimum total cost |
| **Search strategy** | **Uniform Cost Search** — expand the frontier node of lowest g(n); no heuristic |
| **Environment** | Partially dynamic: costs are fixed during any single search but change between searches as traffic conditions change |

**Properties of the environment,** in the standard classification:

- **Fully observable** — the agent can see every road's current cost.
- **Deterministic** — traversing a road always leads to the same location at the stated cost.
- **Sequential** — each move determines what is available next.
- **Dynamic** — conditions change between decisions, which is what forces recalculation.
- **Discrete** — finitely many locations and roads.
- **Single-agent** — no other vehicle is modelled (see §19).

**Why UCS and not another uninformed strategy.**

| Strategy | Why it is not used |
|----------|-------------------|
| Breadth-first search | Optimal only when every action costs the same. Here costs range from 4 to 21 minutes, so BFS would return the route with the fewest roads, not the fastest |
| Depth-first search | Neither optimal nor complete on a graph with cycles; would return an arbitrary route |
| A* | Optimal, and would expand fewer nodes — but it is *informed* search. Adding a heuristic would change the algorithm being demonstrated. Listed as future work |
| Greedy best-first | Not optimal; ignores the cost already incurred |

UCS is the correct choice: the costs vary, no admissible heuristic is available without
introducing geographic assumptions, and optimality is required.

---

## 12. The UCS Algorithm

Uniform Cost Search is best-first search with the evaluation function **f(n) = g(n)**, where
g(n) is the cumulative cost of the path from the initial state to n. It maintains a priority
queue of frontier nodes and repeatedly expands the cheapest.

**The twelve steps, as implemented.**

1. Initialise a priority queue ordered by cumulative path cost.
2. Insert the source node with cost 0.
3. Remove the node with the lowest cumulative cost.
4. Test whether it is the destination.
5. If not, expand it — consider every traversable road leaving it.
6. Compute the cumulative cost of reaching each neighbour through this node.
7. If that is cheaper than the best route known to that neighbour, keep it.
8. Record the parent, for path reconstruction.
9. Insert the improved entry into the priority queue.
10. Repeat until the destination is expanded or the queue empties.
11. Reconstruct the path by following parent pointers back from the goal.
12. Return the least-cost path and its total cost.

### Why the algorithm is optimal

The argument rests on a single invariant: **nodes are expanded in non-decreasing order of
path cost.** When a node is removed from the queue, every remaining entry has a cost at least
as large, and since every action cost is strictly positive, any path continuing through those
entries can only grow. Therefore, at the moment a node is expanded, the cost recorded for it
is the cheapest possible.

Applying the goal test at that moment — on expansion — makes the returned path optimal.

### Why the placement of the goal test is essential

Suppose instead the goal test were applied when a node is *generated*. The destination would
be accepted the first time any path reached it. But the first path to reach a node is merely
the first discovered, not the cheapest: a cheaper route may still be waiting in the queue
behind more expensive frontier entries.

This is not a theoretical concern. On the network used here, the two versions disagree for
**31 of the 182 ordered pairs of connected locations**, by up to 10 minutes. §18 gives a
worked example.

### Completeness and complexity

- **Complete** — provided every action cost is at least some ε > 0. The data loader enforces
  this by rejecting non-positive travel times.
- **Optimal** — by the argument above.
- **Time and space** — O(b^(1 + ⌊C*/ε⌋)) in the general formulation, where C* is the optimal
  cost and b the branching factor. On an explicit finite graph, as here, this reduces to
  O(E log V): each edge can cause at most one insertion, and each queue operation costs
  O(log V). For this network — 16 locations, 24 roads — the search completes in well under a
  millisecond.

### Relationship to Dijkstra's algorithm

Stated plainly, because it is a fair question. On a finite graph with non-negative edge
weights, UCS and Dijkstra's algorithm expand nodes in the same order and belong to the same
algorithmic family. Two differences of formulation distinguish them:

| | Uniform Cost Search | Dijkstra's algorithm |
|---|---|---|
| Posed as | A state-space search for a single goal | Single-source shortest paths to all vertices |
| Termination | As soon as the goal is expanded | When every vertex has been settled |
| Output | One path and its cost | A complete shortest-path tree |
| State space | May be generated lazily, and may be infinite | An explicit, finite graph |

This project implements the search formulation, per Russell & Norvig: an explicit priority
queue on g(n), no heuristic, the goal test on expansion, early termination, and no
shortest-path library. Acknowledging the relationship is more defensible than denying it.

---

## 13. UCS Pseudocode

```
function UNIFORM-COST-SEARCH(graph, source, destination) returns a path and its cost,
                                                          or failure

    frontier  ← a priority queue ordered by cumulative cost g,
                 ties broken by insertion order
    INSERT(frontier, source, g = 0)

    best      ← a map from node to its cheapest known cost;  best[source] ← 0
    parent    ← a map from node to its predecessor;          parent[source] ← none
    explored  ← an empty set

    while frontier is not empty do

        (node, g) ← POP-MIN(frontier)

        // A node can appear more than once, because a cheaper route to it was
        // found after an earlier entry was queued. A binary heap cannot delete
        // the obsolete entry, so it is skipped here instead.
        if node ∈ explored or g > best[node] then
            continue

        // GOAL TEST ON EXPANSION.
        // Every remaining entry costs at least g, and all action costs are
        // positive, so no cheaper route to this node can still be found.
        if node = destination then
            return RECONSTRUCT-PATH(parent, destination), g

        add node to explored

        for each traversable edge (node → neighbour) with cost c do

            if neighbour ∈ explored then
                continue

            new_g ← g + c

            if neighbour ∉ best or new_g < best[neighbour] then
                best[neighbour]   ← new_g
                parent[neighbour] ← node
                INSERT(frontier, neighbour, new_g)

    return failure                      // "No route available"


function RECONSTRUCT-PATH(parent, target) returns a sequence of locations
    path ← empty list
    node ← target
    while node ≠ none do
        prepend node to path
        node ← parent[node]
    return path
```

**Notes on the implementation.**

- *Tie-breaking.* Entries of equal cost are removed in the order they were inserted.
  Without a deterministic rule, two runs on the same graph could expand equal-cost nodes in
  different orders. Both answers would be optimal, but the expansion trace would not be
  reproducible — and the trace is asserted against a hand-computed one in the tests.
- *Neighbour ordering.* Neighbours are generated in alphabetical order of location id, for
  the same reason.
- *Lazy deletion.* Rather than searching the heap for an obsolete entry to remove — an O(n)
  operation — the improved entry is pushed and the obsolete one skipped when it surfaces.
  The trace records these skips explicitly, and the visualisation shows them struck through.

---

## 14. Cost Function

The single formula on which the entire system rests:

```
edge cost = base travel time + traffic delay
```

**Base travel time** is the free-flow time in minutes, a property of the road: its length and
class. It does not change.

**Traffic delay** is the additional time imposed by current congestion, obtained from the
traffic level by a fixed table:

| Traffic level | Delay | Interpretation |
|---------------|-------|----------------|
| Low | +0 min | Free-flowing |
| Medium | +5 min | Moderate congestion |
| High | +12 min | Heavy congestion |
| Blocked | — | The road is not traversable and is excluded from the graph |

**Worked example.** Road R18 joins Old Town Square and Railway Station. Its base travel time
is 9 minutes. Under medium traffic its cost is 9 + 5 = **14**. Raise the level to high and
the cost becomes 9 + 12 = **21**.

**Traversability.** A road may be used only if

```
road status = open   AND   traffic level ≠ blocked
```

Congestion and closure are separate fields because they are separate facts: a road can be
jammed but passable, or empty but shut for repairs. Either makes it unusable.

**Why a blocked road is excluded rather than made expensive.** Assigning a very large cost —
"infinity" — would leave the road in the state space as an available action, and a search
would take it if no alternative existed. That would produce a route down a closed road
instead of an honest report that no route exists. Removing the edge models the situation
correctly: the action is not available.

**Path cost.** The cost of a route is the sum of its edges. For `A → C → F → N → I → K` under
the initial conditions:

| Leg | Road | Base | Traffic | Delay | Cost | Running total |
|-----|------|-----:|---------|------:|-----:|--------------:|
| A → C | R02 | 5 | low | +0 | 5 | 5 |
| C → F | R07 | 6 | low | +0 | 6 | 11 |
| F → N | R13 | 5 | low | +0 | 5 | 16 |
| N → I | R23 | 5 | low | +0 | 5 | 21 |
| I → K | R18 | 9 | medium | +5 | 14 | **35** |

30 minutes of base travel plus 5 minutes of traffic delay: **35 minutes**.

**Properties that matter for the search.** Every cost is a positive integer, so UCS is
complete and optimal, and no zero-cost cycle can exist. Costs are symmetric, since roads are
bidirectional. Distance in kilometres is carried for display but plays no part in the cost —
the system optimises for time, not distance, which is why the route it chooses is sometimes
not the shortest one on the map.

---

## 15. Traffic Simulation

> Traffic in this system is **simulated**. No live traffic service is contacted.

**Initial conditions** come from `backend/data/road_network.json`, which assigns each of the
24 roads a starting traffic level: 13 low, 8 medium, 3 high, none blocked. The mix is chosen
so that several routes are genuinely competitive rather than one being obviously best.

**Changing conditions.** Traffic changes in two ways, both routed through `TrafficData`:

1. **Manual** — the user selects a road and a level and applies it. This is the primary mode:
   deterministic and reproducible, so a demonstration can be repeated exactly.
2. **Automatic** — an optional switch changes one randomly chosen road every five seconds, so
   rerouting can be shown continuously without clicking. It makes no attempt to be a traffic
   model. Blocking is excluded from random changes by default, so an unattended demonstration
   cannot strand the network.

**Propagation.** When a level changes, the sequence is automatic:

```
TrafficData.apply_update(road, level)
        │
        ├── records the new level and status
        ├── notifies its subscribers
        │
        ▼
WeightedGraph rebuilds that road's two directed edges
        │
        ▼
the next search sees the new cost
```

The graph subscribes at construction, so no caller has to remember to rebuild anything, and
only the two edges of the changed road are touched — a property the tests assert directly.

**How a real feed would be introduced.** Every other module asks `TrafficData` for congestion
rather than deciding for itself. A live feed would therefore be a new source of
`apply_update` calls — a polling client, or a stream handler — with no change to the graph,
the search, or the navigation logic. That is the concrete content of the claim that the
design admits future integration, and it remains future work (§20).

**What this simulation is not.** It does not model traffic flow, vehicle interactions, signal
timing, rush-hour patterns, or the effect of rerouted vehicles on the roads they move to. It
is a mechanism for changing edge costs so that the search's response can be demonstrated —
which is the aspect this project is about.

---

## 16. Dynamic Rerouting

When conditions change, the system must decide whether the route being followed is still the
right one.

**The comparison that makes it correct.** It is not enough to re-run the search and see
whether the answer differs. The route currently being followed must first be **re-priced
under the new conditions**. Its stored cost was computed under the old ones and is now
meaningless: comparing a fresh search result against a stale number would announce reroutes
that save nothing and miss ones that matter.

Concretely: the baseline route costs 35 minutes. Raising traffic on road R18 — which lies on
that route — makes the same route cost 42. The search finds an alternative at 39. The
decision must compare **42 against 39**, not 35 against 39. Compared against the stale 35,
the new route would appear 4 minutes *worse* and no reroute would occur, leaving the traveller
on a route that is genuinely 3 minutes slower.

**The sequence.**

1. Apply the traffic change; the graph re-costs the affected edges automatically.
2. Re-price the active route under the new conditions. A result of "impossible" means one of
   its roads is no longer traversable.
3. Run UCS again from the same source and destination.
4. Compare, and classify the outcome.

**The four outcomes.**

| Condition | Decision | Shown to the user |
|-----------|----------|-------------------|
| The active route contains a road that is now blocked | `ROUTE_BLOCKED` | **"Route Updated"** — a road on your route is blocked; here is the new route |
| The search returns a different, strictly cheaper route | `CHEAPER_ROUTE_FOUND` | **"Route Updated"** — with the old cost, the new cost and the saving |
| The search returns the same route | `UNCHANGED` | **"Route unchanged"** — still the best option, with its updated cost if congestion has made it slower |
| No route exists any more | `NO_ROUTE` | **"No route available"** |

**Two causes of a reroute, reported separately.** When a cheaper route is found, the
explanation distinguishes whether the route being followed got *worse* ("Heavy traffic
detected on the previous route, which has risen from 35 to 42 min") or whether another route
got *better* ("Traffic has eased elsewhere in the network"). Both produce the same decision
but mean different things to a traveller.

**Rerouting is recomputation, not repair.** The system does not attempt to patch the existing
route around a problem. It re-solves the search problem from scratch under the new costs. On
a network this size that costs well under a millisecond, and it guarantees the new route is
globally optimal rather than merely locally repaired.

---

## 17. Test Cases

The eight cases required by the specification, all automated. Run with:

```bash
cd backend && python -m pytest tests -v
```

| # | Test case | Expected | Implemented as |
|---|-----------|----------|----------------|
| 1 | Normal traffic → find the optimal route | `A→C→F→N→I→K`, cost 35 | `test_baseline_optimal_route` |
| 2 | Traffic rises on the current route → recalculate | R18 → high; reroute to `A→C→E→H→J→K`, cost 39 | `test_reroute_on_congestion` |
| 3 | Block a road → UCS avoids it | R02 blocked; route becomes `A→B→D→L→K`, cost 40, R02 absent from the graph | `test_ucs_avoids_a_blocked_road` |
| 4 | Invalid source → display an error | `unknown_source`, no search run | `test_invalid_source` |
| 5 | Invalid destination → display an error | `unknown_destination`, no search run | `test_invalid_destination` |
| 6 | Source = destination → display an error | `same_location` | `test_same_source_and_destination` |
| 7 | No possible route → "No route available" | A → Z rejected; search exhausts all 14 mainland locations | `test_no_route_available`, `test_no_route_available_across_a_disconnection` |
| 8 | Several routes of differing cost → UCS picks the minimum | Checked against all 182 enumerated routes | `test_ucs_selects_minimum` |

**Additional tests, beyond the eight required.**

| Test | What it establishes |
|------|--------------------|
| `test_ucs_golden_trace` | The search reproduces a 17-step expansion computed by hand *before* the code was written. This constrains not just the answer but the order in which the algorithm considered every location — which is what distinguishes an implementation of UCS from a library call that happens to agree |
| `test_goal_is_accepted_only_when_expanded` | The destination enters the queue at step 9 and is accepted at step 17 — the gap is the goal test doing its work |
| `test_goal_test_on_generation_would_return_a_worse_route` | The incorrect variant returns 14 instead of 10 on the specification's own four-node example |
| `test_ucs_beats_every_alternative_under_random_traffic` | Optimality holds for 20 randomised traffic configurations, each checked against brute-force enumeration |
| `test_repeated_changes_keep_the_route_optimal` | After each of 25 random traffic changes, the active route still equals the brute-force minimum |
| `test_reroute_compares_against_the_repriced_old_route` | The comparison uses 42 (re-priced), not 35 (stale) |
| `test_traffic_change_affects_only_the_road_that_changed` | A traffic update re-costs exactly two directed edges |
| `test_blocked_road_is_removed_from_the_graph` | Blocking removes the edge rather than inflating its cost |
| `test_island_is_internally_connected` | Y → Z succeeds at cost 4, proving the A → Z failure is a genuine disconnection and not a defect |
| `test_no_route_when_every_connecting_road_is_blocked` | The second cause of unreachability is detected and reported differently |
| `test_blocking_the_only_road_to_a_location_isolates_it` | A → M costs 32; blocking R19 makes it unreachable |
| `test_source_equal_to_goal_costs_nothing` | The engine remains correct in a case Module 1 rejects earlier |
| `test_priority_queue_breaks_ties_by_insertion_order` | Equal-cost entries pop deterministically, making the trace reproducible |
| `test_every_road_has_a_positive_base_travel_time` | Guards the ε > 0 condition on which completeness depends |

---

## 18. Results

### The road network

16 locations and 24 bidirectional roads. Node degrees: A 3, B 3, C 3, D 3, E 5, F 3, G 4,
H 4, I 3, J 4, K 3, L 4, M 1, N 3, Y 1, Z 1. Two connected components — a mainland of 14
locations and a two-location island — verified by breadth-first search.

There are **182 distinct simple routes** from College Main Gate to Railway Station, so the
demonstration is genuinely a choice among alternatives.

### Result 1 — Baseline (Test 1, Test 8)

Source `A` College Main Gate → destination `K` Railway Station, under initial traffic.

**Route returned:** `A → C → F → N → I → K` — College Main Gate → Market Junction → Lake View
Circle → Green Park Chowk → Old Town Square → Railway Station
**Total cost: 35 minutes** (30 base + 5 delay), 17.8 km, 13 locations expanded.

The six cheapest of the 182 routes, computed by exhaustive enumeration independently of the
search:

| Route | Cost |
|-------|-----:|
| **A–C–F–N–I–K** | **35** ← returned by UCS |
| A–C–E–H–J–K | 39 |
| A–B–D–L–K | 40 |
| A–C–F–N–H–J–K | 40 |
| A–E–H–J–K | 42 |
| A–B–D–G–J–K | 43 |

UCS returned the true minimum, and it wins by a clear 4-minute margin.

### Result 2 — The expansion trace

The full sequence of removals from the priority queue, reproduced exactly by the
implementation and asserted in `test_ucs_golden_trace`. An asterisk marks an obsolete entry.

| Step | Action | Node | g(n) | Priority queue after the step |
|-----:|--------|------|-----:|-------------------------------|
| 1 | expand | A | 0 | C:5, B:11, E:19 |
| 2 | expand | C | 5 | B:11, F:11, E:16, E:19\* |
| 3 | expand | B | 11 | F:11, E:16, D:17, E:19\* |
| 4 | expand | F | 11 | E:16, N:16, D:17, E:19\*, H:30 |
| 5 | expand | E | 16 | N:16, D:17, E:19\*, H:24, G:29, H:30\* |
| 6 | expand | N | 16 | D:17, E:19\*, I:21, H:24, G:29, H:30\* |
| 7 | expand | D | 17 | E:19\*, I:21, H:24, G:24, G:29\*, H:30\*, L:30 |
| 8 | *skip* | E | 19 | I:21, H:24, G:24, G:29\*, H:30\*, L:30 |
| 9 | expand | I | 21 | H:24, G:24, G:29\*, H:30\*, L:30, M:32, K:35 |
| 10 | expand | H | 24 | G:24, G:29\*, H:30\*, L:30, J:31, M:32, K:35 |
| 11 | expand | G | 24 | G:29\*, H:30\*, L:30, J:31, M:32, K:35 |
| 12 | *skip* | G | 29 | H:30\*, L:30, J:31, M:32, K:35 |
| 13 | *skip* | H | 30 | L:30, J:31, M:32, K:35 |
| 14 | expand | L | 30 | J:31, M:32, K:35 |
| 15 | expand | J | 31 | M:32, K:35 |
| 16 | expand | M | 32 | K:35 |
| 17 | **goal** | **K** | **35** | (empty) |

17 removals: 13 expansions, 3 obsolete entries skipped, and the goal accepted on the 17th.

**The point to notice.** The destination K enters the queue at step 9, with cost 35. It is
not accepted until step 17, after seven further removals. Those seven steps are the algorithm
confirming that nothing cheaper remains — which is exactly what the goal test on expansion is
for.

### Result 3 — Goal test placement

College Main Gate → Sports Stadium, on the same graph, with the same costs:

| Version | Route | Cost |
|---------|-------|-----:|
| Goal test on **expansion** (correct UCS) | A → C → E → H | **24 min** |
| Goal test on **generation** (incorrect) | A → C → F → H | 30 min |

The destination H is first discovered at step 4, through F, at cost 30, and enters the queue
as H:30. A search that stopped on discovery would return that. The correct search continues,
reaches H again through E at cost 24 — replacing the earlier entry — and accepts H only at
step 10, when H itself reaches the front of the queue.

Across the 14 connected locations there are 14 × 13 = 182 ordered pairs, and the two versions
disagree on **31 of them**, by up to 10 minutes. The placement of one line of code is the
whole difference between a search that is guaranteed optimal and one that is not.

### Result 4 — Rerouting on congestion (Test 2)

Road R18 (Old Town Square – Railway Station), which lies on the active route, goes from
medium to high traffic. Its cost rises from 9 + 5 = 14 to 9 + 12 = **21**.

| | Route | Cost |
|---|-------|-----:|
| Before | A → C → F → N → I → K | 35 |
| The same route, re-priced | A → C → F → N → I → K | **42** |
| After rerouting | **A → C → E → H → J → K** | **39** |

Decision: `CHEAPER_ROUTE_FOUND`. Saving 3 minutes against the re-priced route. The system
abandons the southern lakeside corridor for the Bus Terminus–Stadium–Mall corridor.

Had the comparison used the stale figure of 35, no reroute would have occurred and the
traveller would have stayed on a route 3 minutes slower.

### Result 5 — Rerouting on a blockage (Test 3)

Road R02 (College Main Gate – Market Junction), the first leg of the active route, is
blocked. It is removed from the graph, destroying 71 of the 182 possible routes.

| | Route | Cost |
|---|-------|-----:|
| Before | A → C → F → N → I → K | 35 |
| The same route | **impossible** | — |
| After rerouting | **A → B → D → L → K** | **40** |

Decision: `ROUTE_BLOCKED`. R02 does not appear in the new route, and `cost_of_road("R02")`
returns nothing — the road is absent from the graph, not merely expensive.

### Result 6 — No route available (Test 7)

**Permanent.** College Main Gate → Island Fishing Village. The island is served by ferry; no
road joins it to the mainland. The request is rejected with: *"No route available … These
locations are in separate parts of the network and are not joined by any road."*

For contrast, Pelican Island Jetty → Island Fishing Village succeeds at 4 minutes. The island
is internally connected, so the failure is a genuine disconnection rather than a defect in
the search. Run without the reachability pre-check, the search expands all 14 mainland
locations, exhausts the frontier and reports failure — it does not give up early.

**Caused by a blockage.** Road R19 is the only road serving Hilltop Observatory. Before
blocking, A → M costs 32 minutes. After blocking, M has no traversable edge and the request
fails. Reopening the road restores the route.

**All roads out of the source blocked.** Blocking R01, R02 and R03 isolates the source, and
the message distinguishes this cause: *"Every road that could connect them is currently
blocked."*

### Result 7 — Invalid input (Tests 4, 5, 6)

| Input | Error code | Message |
|-------|-----------|---------|
| Source "Airport" | `unknown_source` | 'Airport' is not a location in this road network. Please choose a source from the list. |
| Destination "Moon Base" | `unknown_destination` | 'Moon Base' is not a location in this road network. Please choose a destination from the list. |
| Both "College Main Gate" | `same_location` | Source and destination are both College Main Gate. Please choose two different locations. |
| Empty source | `empty_source` | Please select a source location. |

In every case no search is run. `"A"` and `"College Main Gate"` are correctly recognised as
the same place written two ways.

### Result 8 — The complete dynamic cycle

Five successive traffic changes applied to a single journey:

| Change | Decision | Route | Cost |
|--------|----------|-------|-----:|
| *(initial)* | initial route | A → C → F → N → I → K | 35 |
| R18 medium → high | Route Updated | A → C → E → H → J → K | 39 |
| R16 low → high | Route Updated | A → B → D → L → K | 40 |
| R02 blocked | Route unchanged | A → B → D → L → K | 40 |
| R02 reopened (low) | Route unchanged | A → B → D → L → K | 40 |
| R18 high → low | Route Updated | A → C → F → N → I → K | 30 |

The third change is worth noting: R02 was blocked while the active route did not use it, so
the correct decision was to leave the route alone. The last is the other reported cause of a
reroute — the active route did not get worse, another route got better, and the explanation
says so.

### Test summary

```
71 passed in 0.50s
```

All eight required cases pass, together with the golden trace, the brute-force cross-checks
under randomised traffic, and the structural and cost-model tests.

---

## 19. Limitations

Stated plainly, since knowing what a system does not do is part of understanding what it
does.

**Traffic is simulated.** Levels come from a data file and from user input. The system has no
knowledge of actual conditions on any real road. This is the most significant limitation and
is stated wherever the system reports a result.

**The network is fixed and fictional.** 16 locations with hand-assigned coordinates and
travel times. It is designed to make the search's behaviour visible, not to model a real
place.

**Costs are static within a search.** A road's cost is fixed for the duration of one search
and changes only between searches. Real journeys encounter conditions that change while they
are in progress; this is the time-dependent shortest-path problem noted in §4, and it is not
modelled.

**No partial-journey rerouting.** When conditions change, the system re-solves from the
original source rather than from wherever the traveller has reached. A deployed system would
reroute from the current position.

**Roads are bidirectional.** Every road is usable both ways at equal cost. One-way streets
and asymmetric costs are not represented.

**The traffic-delay model is a step function.** Three levels mapping to fixed delays of 0, 5
and 12 minutes. Real congestion is continuous, and its effect scales with road length rather
than being a constant. A 2-km road and a 10-km road at "high" traffic receive the same
12-minute penalty here.

**Single-agent.** No other vehicles exist. In particular, the system does not model the fact
that rerouting many vehicles onto an alternative road would itself congest that road.

**A single shared session.** The web layer keeps one in-memory session, so two browsers
pointed at the same server would share one route. This is appropriate for a single-user
demonstration and is the reason no database is needed.

**No persistence.** Traffic changes are lost when the server restarts; the network reloads
from the data file.

**Scale.** The implementation is O(E log V) per search, which is entirely adequate here but
has not been tested on a city-scale network of hundreds of thousands of nodes. At that scale,
plain UCS would be too slow and techniques such as A* with landmarks, contraction hierarchies
or bidirectional search would be required.

---

## 20. Future Enhancements

The following are **not implemented**. They are directions the architecture would support.

**Real-time traffic APIs.** The natural next step, and the one the design most directly
anticipates. Because `TrafficData` is the single source of congestion, a live feed would be a
new source of `apply_update` calls — a polling client or a stream handler — with no change to
the weighted graph, the search, or the navigation logic.

**GPS integration.** Tracking the traveller's position would allow rerouting from where they
actually are rather than from the original source, which is the main practical shortcoming
noted in §19.

**Live map data.** Replacing the hand-built network with a real one, for example from
OpenStreetMap, would exercise the system at realistic scale and require the performance work
noted below.

**Accident detection and road-closure APIs.** Automatic sources of the blocking that must
currently be applied by hand.

**Weather-based costs.** Rain, fog or flooding as an additional term in the cost function —
a straightforward extension, since the cost function is one formula in one place.

**Machine-learning traffic prediction.** Predicting future congestion from historical
patterns, so the cost of a road could reflect conditions expected *at the time the traveller
will arrive there* rather than conditions now. This would turn the problem into a
time-dependent shortest-path problem and is the most substantial extension listed here.

**Comparison with A\*.** Implementing A* with an admissible heuristic and comparing the two
on the same network would show the same optimal route from far fewer expansions, and would
demonstrate concretely what a heuristic buys. Given the trace infrastructure already present,
this is the most natural academic extension of the project.

**Multi-vehicle traffic simulation.** Modelling many vehicles so that rerouting decisions
affect the congestion other vehicles experience — moving from a single-agent to a multi-agent
setting.

**Performance work for city-scale networks.** Bidirectional search, contraction hierarchies
or landmark-based heuristics, none of which are necessary at this scale.

---

## 21. Conclusion

This project set out to demonstrate that route selection under changing traffic conditions is
naturally expressed as a state-space search problem, and that Uniform Cost Search solves it
correctly.

**What was built.** A complete system in six modules: input validation, a road network of 16
locations and 24 roads, a simulated traffic model, a weighted graph in which
`cost = base travel time + traffic delay`, an implementation of Uniform Cost Search written
from first principles, and a navigation layer that reroutes when conditions change. The AI
core runs entirely from the terminal with no interface and no third-party libraries; a
dashboard with a graph visualisation and a step-by-step view of the search sits on top of it.

**What was demonstrated.**

- Route selection formulated as search: states, actions, a transition model, a path cost and
  a goal test (§11).
- UCS finding the optimal route — `A → C → F → N → I → K` at 35 minutes — and that route
  confirmed as the true minimum against exhaustive enumeration of all 182 alternatives.
- The algorithm's reasoning made visible: a 17-step expansion trace, computed by hand before
  the code was written and reproduced exactly by the implementation.
- Why the goal test belongs at expansion, shown not as an assertion but as a measured
  difference: 24 minutes against 30 on one pair of locations, and disagreement on 31 of 182
  pairs.
- Traffic changes propagating into edge costs, into the graph, into a fresh search, and into
  an updated route — including the subtlety that the route being followed must be re-priced
  under new conditions before any comparison is meaningful.
- Unreachability reported correctly, because blocked roads are removed from the state space
  rather than made expensive.

**What was learned.** Two things stand out. The first is how much rests on the placement of a
single line: moving the goal test from expansion to generation leaves a program that still
runs, still returns routes, and is quietly wrong. Only a test that constrains the *order of
expansion*, not merely the answer, catches that reliably. The second is that a correct
algorithm is not sufficient for a correct system: the search was right long before the
rerouting logic was, because comparing a fresh result against a stale cost is a defect that
lives entirely outside the algorithm.

**Honest scope.** Traffic here is simulated, the network is fictional, and the system routes
no better than a commercial service. That was never the aim. Its value is that every step of
its reasoning — every road cost, every queue state, every expansion, and the arithmetic
making the chosen route cheapest — can be inspected and checked by hand. For a project whose
subject is how search works, that transparency is the point.
