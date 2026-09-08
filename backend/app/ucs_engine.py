"""
MODULE 5 -- UCS AI ENGINE
=========================

Input   : a weighted graph, a source, a destination
Process : Uniform Cost Search
Output  : the least-cost route, its total cost, the nodes explored, and the
          path-reconstruction information

This is the core AI module of the project. Uniform Cost Search is implemented
here from first principles -- no shortest-path library is called, and no
heuristic is used anywhere.

AI PROBLEM FORMULATION
----------------------
    Initial state    the user's source location
    Goal state       the destination location
    States           locations / junctions in the road network
    Actions          move along a road to a connected location
    Transition model traversing a road changes the current location
    Path cost        the sum of edge costs along the path taken
    Goal test        current location == destination
    Strategy         expand the frontier node with the lowest cumulative cost g(n)

WHY THIS IS UNIFORM COST SEARCH
-------------------------------
UCS is the uninformed search that orders its frontier by cumulative path cost
g(n) alone. Two properties in the code below are what make it UCS and what make
it correct, and both are worth pointing at directly:

1. `priority = g(n)`, with no heuristic term. Adding an estimate h(n) of the
   remaining distance would turn this into A*. There is no such term here; the
   node coordinates in the data are used for drawing only.

2. The goal test happens when a node is *expanded* (popped), not when it is
   *generated* (first discovered). This is the subtle part. The first time the
   goal is discovered, the path to it is merely the first one found -- not
   necessarily the cheapest. Only when the goal reaches the front of the
   priority queue do we know that no cheaper path to it can remain, because
   every remaining frontier entry already costs at least as much and all edge
   costs are positive. See `demo_cli.py`, which shows a case where testing at
   generation would return a worse route.

RELATIONSHIP TO DIJKSTRA'S ALGORITHM
------------------------------------
Stated plainly, because it is a fair question: on a finite graph with
non-negative edge weights, UCS and Dijkstra's algorithm explore nodes in the
same order and are of the same algorithmic family. The difference is one of
formulation and purpose. UCS is posed as a *state-space search* for a single
goal: it terminates as soon as the goal is expanded and never computes the full
shortest-path tree. Dijkstra's is normally posed as a single-source
shortest-path computation over the whole graph. This project implements the
search formulation, per Russell & Norvig, "Artificial Intelligence: A Modern
Approach".
"""

from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass, field
from typing import Iterable, Protocol

from .models import Edge


# ---------------------------------------------------------------------------
# What UCS needs from a graph
# ---------------------------------------------------------------------------

class SearchableGraph(Protocol):
    """
    The only thing UCS requires of a graph: the ability to list the traversable
    edges leaving a node, each already priced under current conditions.

    Keeping this narrow is deliberate. The search engine knows nothing about
    traffic levels, road closures or minutes -- it sees numbers on edges. That
    is what lets traffic become dynamic without the algorithm changing at all.
    """

    def neighbours(self, node_id: str) -> Iterable[Edge]:
        ...

    def has_node(self, node_id: str) -> bool:
        ...


# ---------------------------------------------------------------------------
# Priority queue
# ---------------------------------------------------------------------------

class PriorityQueue:
    """
    A minimum priority queue keyed on cumulative path cost g(n).

    Written out explicitly rather than used inline, because "initialise a
    priority queue" is step 1 of the algorithm and the ordering rule is what
    makes the search uniform-cost.

    Ties are broken by insertion order (first in, first out among equal costs).
    Without a deterministic tie-break, two runs on the same graph could expand
    equal-cost nodes in different orders and produce different -- though equally
    optimal -- routes. Reproducibility matters here because the expansion trace
    is checked against a hand-computed one in the tests.
    """

    def __init__(self) -> None:
        self._heap: list[tuple[int, int, str]] = []
        self._counter = itertools.count()

    def push(self, node_id: str, cost: int) -> None:
        heapq.heappush(self._heap, (cost, next(self._counter), node_id))

    def pop(self) -> tuple[str, int]:
        cost, _sequence, node_id = heapq.heappop(self._heap)
        return node_id, cost

    def entries(self) -> list[tuple[str, int]]:
        """Contents in pop order -- used for the visualisation, not the search."""
        return [(node_id, cost) for cost, _seq, node_id in sorted(self._heap)]

    def __len__(self) -> int:
        return len(self._heap)

    def __bool__(self) -> bool:
        return bool(self._heap)


# ---------------------------------------------------------------------------
# Trace records (for the UCS visualisation panel)
# ---------------------------------------------------------------------------

@dataclass
class SuccessorRecord:
    """One neighbour considered during an expansion."""

    node: str
    edge_cost: int
    new_cost: int
    accepted: bool
    reason: str


@dataclass
class UCSStep:
    """
    A snapshot of the search at one removal from the priority queue.

    The trace is produced by the algorithm itself while it runs, so the panel in
    the user interface displays what the search actually did rather than a
    reconstruction of what it probably did.
    """

    step: int
    action: str                       # "expand" | "discard" | "goal"
    node: str
    cumulative_cost: int
    path: list[str]
    frontier_before: list[dict]
    frontier_after: list[dict]
    explored: list[str]
    successors: list[SuccessorRecord] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "action": self.action,
            "node": self.node,
            "cumulativeCost": self.cumulative_cost,
            "path": self.path,
            "frontierBefore": self.frontier_before,
            "frontierAfter": self.frontier_after,
            "explored": self.explored,
            "successors": [
                {
                    "node": s.node,
                    "edgeCost": s.edge_cost,
                    "newCost": s.new_cost,
                    "accepted": s.accepted,
                    "reason": s.reason,
                }
                for s in self.successors
            ],
            "note": self.note,
        }


@dataclass
class UCSResult:
    """The outcome of one Uniform Cost Search."""

    found: bool
    source: str
    destination: str
    path: list[str] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    total_cost: int = 0
    cumulative_costs: list[int] = field(default_factory=list)
    nodes_expanded: list[str] = field(default_factory=list)
    trace: list[UCSStep] = field(default_factory=list)
    parent_map: dict[str, str | None] = field(default_factory=dict)
    best_costs: dict[str, int] = field(default_factory=dict)
    pops: int = 0
    stale_discards: int = 0
    failure_reason: str = ""

    @property
    def explored_count(self) -> int:
        return len(self.nodes_expanded)

    def path_string(self, arrow: str = " -> ") -> str:
        return arrow.join(self.path) if self.path else "(no route)"

    def to_dict(self) -> dict:
        return {
            "found": self.found,
            "source": self.source,
            "destination": self.destination,
            "path": self.path,
            "edges": [
                {
                    "roadId": e.road_id,
                    "from": e.from_node,
                    "to": e.to_node,
                    "cost": e.cost,
                }
                for e in self.edges
            ],
            "totalCost": self.total_cost,
            "cumulativeCosts": self.cumulative_costs,
            "nodesExpanded": self.nodes_expanded,
            "exploredCount": self.explored_count,
            "pops": self.pops,
            "staleDiscards": self.stale_discards,
            "trace": [step.to_dict() for step in self.trace],
            "failureReason": self.failure_reason,
        }


# ---------------------------------------------------------------------------
# The algorithm
# ---------------------------------------------------------------------------

def uniform_cost_search(
    graph: SearchableGraph,
    source: str,
    destination: str,
    *,
    record_trace: bool = True,
) -> UCSResult:
    """
    Find the least-cost route from `source` to `destination` by Uniform Cost Search.

    The numbered comments correspond to the twelve steps of the algorithm as
    stated in the project specification.
    """
    if not graph.has_node(source):
        raise KeyError(f"Unknown source location: {source!r}")
    if not graph.has_node(destination):
        raise KeyError(f"Unknown destination location: {destination!r}")

    # 1. Initialise the priority queue, ordered by cumulative path cost.
    frontier = PriorityQueue()

    # 2. Insert the source node with cost 0.
    frontier.push(source, 0)

    best_cost: dict[str, int] = {source: 0}       # cheapest known cost to each node
    parent: dict[str, str | None] = {source: None}
    parent_edge: dict[str, Edge] = {}             # the road used to reach each node
    explored: set[str] = set()                    # the closed set
    expansion_order: list[str] = []
    trace: list[UCSStep] = []
    pops = 0
    stale_discards = 0

    def snapshot() -> list[dict]:
        """Frontier contents, flagging entries that a later pop will discard."""
        return [
            {
                "node": node_id,
                "cost": cost,
                "stale": node_id in explored or cost > best_cost.get(node_id, cost),
            }
            for node_id, cost in frontier.entries()
        ]

    def reconstruct(target: str) -> tuple[list[str], list[Edge], list[int]]:
        """
        11. Rebuild the path by following parent pointers back from the goal,
            then reversing. The parent map is what makes this possible; the
            search itself never carries whole paths around.
        """
        nodes: list[str] = []
        edges: list[Edge] = []
        cursor: str | None = target
        while cursor is not None:
            nodes.append(cursor)
            edge = parent_edge.get(cursor)
            if edge is not None:
                edges.append(edge)
            cursor = parent.get(cursor)
        nodes.reverse()
        edges.reverse()

        running = 0
        costs = [0]
        for edge in edges:
            running += edge.cost
            costs.append(running)
        return nodes, edges, costs

    while frontier:
        frontier_before = snapshot() if record_trace else []

        # 3. Remove the node with the lowest cumulative cost.
        node, cost = frontier.pop()
        pops += 1

        # A node may appear in the queue more than once, because a cheaper route
        # to it was found after an earlier entry was queued. The obsolete entry
        # cannot simply be deleted from a binary heap, so it is skipped here.
        if node in explored or cost > best_cost.get(node, cost):
            stale_discards += 1
            if record_trace:
                trace.append(
                    UCSStep(
                        step=pops,
                        action="discard",
                        node=node,
                        cumulative_cost=cost,
                        path=[],
                        frontier_before=frontier_before,
                        frontier_after=snapshot(),
                        explored=list(expansion_order),
                        note=(
                            f"Obsolete queue entry: {node} was already expanded"
                            if node in explored
                            else f"Obsolete queue entry: a cheaper path to {node} "
                                 f"(cost {best_cost[node]}) was found later"
                        ),
                    )
                )
            continue

        # 4. Goal test -- performed on EXPANSION, not on generation.
        #    Reaching this line means every other frontier entry costs at least
        #    `cost`, so no cheaper route to this node can still be found.
        if node == destination:
            path, edges, cumulative = reconstruct(node)
            if record_trace:
                trace.append(
                    UCSStep(
                        step=pops,
                        action="goal",
                        node=node,
                        cumulative_cost=cost,
                        path=path,
                        frontier_before=frontier_before,
                        frontier_after=snapshot(),
                        explored=list(expansion_order),
                        note=(
                            f"Goal reached on expansion with cumulative cost {cost}. "
                            f"Every remaining queue entry costs at least this much, "
                            f"so no cheaper route exists."
                        ),
                    )
                )
            # 12. Return the least-cost path and its total cost.
            return UCSResult(
                found=True,
                source=source,
                destination=destination,
                path=path,
                edges=edges,
                total_cost=cost,
                cumulative_costs=cumulative,
                nodes_expanded=expansion_order,
                trace=trace,
                parent_map=parent,
                best_costs=dict(best_cost),
                pops=pops,
                stale_discards=stale_discards,
            )

        explored.add(node)
        expansion_order.append(node)

        # 5. Expand the node: consider every traversable road leaving it.
        #    Neighbours are taken in a fixed (alphabetical) order so that the
        #    expansion trace is reproducible run to run.
        successors: list[SuccessorRecord] = []
        for edge in sorted(graph.neighbours(node), key=lambda e: e.to_node):
            neighbour = edge.to_node

            if neighbour in explored:
                successors.append(
                    SuccessorRecord(neighbour, edge.cost, cost + edge.cost, False,
                                    "already expanded")
                )
                continue

            # 6. Cumulative cost of reaching the neighbour through this node.
            new_cost = cost + edge.cost
            known = best_cost.get(neighbour)

            # 7. Keep it only if it improves on the cheapest route known so far.
            if known is None or new_cost < known:
                best_cost[neighbour] = new_cost
                # 8. Record the parent, for path reconstruction later.
                parent[neighbour] = node
                parent_edge[neighbour] = edge
                # 9. Insert the improved entry into the priority queue.
                frontier.push(neighbour, new_cost)
                successors.append(
                    SuccessorRecord(
                        neighbour, edge.cost, new_cost, True,
                        "first route found" if known is None
                        else f"cheaper than the known cost of {known}",
                    )
                )
            else:
                successors.append(
                    SuccessorRecord(neighbour, edge.cost, new_cost, False,
                                    f"not cheaper than the known cost of {known}")
                )

        if record_trace:
            path_here, _, _ = reconstruct(node)
            trace.append(
                UCSStep(
                    step=pops,
                    action="expand",
                    node=node,
                    cumulative_cost=cost,
                    path=path_here,
                    frontier_before=frontier_before,
                    frontier_after=snapshot(),
                    explored=list(expansion_order),
                    successors=successors,
                )
            )
        # 10. Continue until the destination is expanded, or the queue empties.

    # The frontier is empty and the goal was never expanded: with every reachable
    # state examined, no route exists.
    return UCSResult(
        found=False,
        source=source,
        destination=destination,
        nodes_expanded=expansion_order,
        trace=trace,
        parent_map=parent,
        best_costs=dict(best_cost),
        pops=pops,
        stale_discards=stale_discards,
        failure_reason=(
            f"No route available from {source} to {destination}. The search "
            f"exhausted every location reachable from {source} "
            f"({len(expansion_order)} expanded) without reaching the destination."
        ),
    )


# ---------------------------------------------------------------------------
# Contrast: the same search with the goal test in the wrong place
# ---------------------------------------------------------------------------

def ucs_with_goal_test_on_generation(
    graph: SearchableGraph, source: str, destination: str
) -> UCSResult:
    """
    A deliberately INCORRECT variant, kept for the demonstration only.

    It is identical to `uniform_cost_search` except that it returns as soon as
    the destination is first *generated* rather than when it is *expanded*. That
    single change loses the optimality guarantee: the first path discovered to
    the goal is whatever the search happened to stumble upon, not the cheapest.

    `demo_cli.py` runs both on the same graph so the difference is visible as a
    concrete pair of routes and costs. Never use this for real routing.
    """
    frontier = PriorityQueue()
    frontier.push(source, 0)
    best_cost = {source: 0}
    parent: dict[str, str | None] = {source: None}
    parent_edge: dict[str, Edge] = {}
    explored: set[str] = set()
    expansion_order: list[str] = []

    def reconstruct(target: str):
        nodes, edges = [], []
        cursor: str | None = target
        while cursor is not None:
            nodes.append(cursor)
            if cursor in parent_edge:
                edges.append(parent_edge[cursor])
            cursor = parent.get(cursor)
        nodes.reverse()
        edges.reverse()
        return nodes, edges

    while frontier:
        node, cost = frontier.pop()
        if node in explored or cost > best_cost.get(node, cost):
            continue
        explored.add(node)
        expansion_order.append(node)

        for edge in sorted(graph.neighbours(node), key=lambda e: e.to_node):
            neighbour = edge.to_node
            if neighbour in explored:
                continue
            new_cost = cost + edge.cost
            known = best_cost.get(neighbour)
            if known is None or new_cost < known:
                best_cost[neighbour] = new_cost
                parent[neighbour] = node
                parent_edge[neighbour] = edge
                frontier.push(neighbour, new_cost)

                # THE BUG, stated plainly: returning here accepts the first path
                # found to the goal instead of waiting for the cheapest.
                if neighbour == destination:
                    path, edges_used = reconstruct(neighbour)
                    return UCSResult(
                        found=True,
                        source=source,
                        destination=destination,
                        path=path,
                        edges=edges_used,
                        total_cost=new_cost,
                        nodes_expanded=expansion_order,
                        parent_map=parent,
                        best_costs=dict(best_cost),
                    )

    return UCSResult(
        found=False,
        source=source,
        destination=destination,
        nodes_expanded=expansion_order,
        failure_reason="No route available.",
    )
