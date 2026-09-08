"""
MODULE 4 -- WEIGHTED GRAPH
==========================

Input   : the road network, base travel time, traffic delay, road status
Process : represent locations as nodes and roads as edges, give every edge a
          cost, exclude roads that are not traversable, and rebuild affected
          edges whenever traffic changes
Output  : a weighted graph carrying current road costs

    EDGE COST = BASE TRAVEL TIME + TRAFFIC DELAY

This module is where the two halves of the problem meet: the static network
(Module 2) and the dynamic environment (Module 3) combine into the single
structure the search runs on (Module 5).

A blocked road is not given a large cost -- it is left out of the adjacency
structure entirely. The distinction is not cosmetic. A very expensive edge is
still an available action, and a search would take it if nothing else existed;
a blocked road is not an available action at all. Modelling closure as absence
from the state space is what lets the system correctly report "No route
available" instead of quietly routing traffic down a closed road.
"""

from __future__ import annotations

from .models import Edge, Node
from .road_network import RoadNetwork
from .traffic_data import TrafficData, TrafficUpdate


class WeightedGraph:
    """
    The weighted, directed adjacency structure searched by UCS.

    Each bidirectional road contributes two directed edges of equal cost. The
    graph subscribes to traffic updates, so a change to a road's congestion is
    reflected in its edges before the next search runs -- no caller has to
    remember to rebuild anything.
    """

    def __init__(self, network: RoadNetwork, traffic: TrafficData):
        self.network = network
        self.traffic = traffic
        self._adjacency: dict[str, list[Edge]] = {}
        self.rebuild_count = 0

        self.rebuild()
        traffic.subscribe(self._on_traffic_change)

    # -- construction -------------------------------------------------------

    def rebuild(self) -> None:
        """Rebuild every edge from the current road network and traffic state."""
        self._adjacency = {node_id: [] for node_id in self.network.node_ids}
        for road in self.network.roads:
            if not road.is_traversable:
                continue                              # blocked: not an available action
            cost = road.cost                          # base travel time + traffic delay
            self._adjacency[road.from_node].append(
                Edge(road.id, road.from_node, road.to_node, cost)
            )
            self._adjacency[road.to_node].append(
                Edge(road.id, road.to_node, road.from_node, cost)
            )
        for edges in self._adjacency.values():
            edges.sort(key=lambda e: e.to_node)       # keeps expansion order stable
        self.rebuild_count += 1

    def _on_traffic_change(self, update: TrafficUpdate) -> None:
        """
        Called by TrafficData whenever a road's condition changes.

        Only the two directed edges belonging to that road are touched; the rest
        of the graph is left alone. This keeps the update proportional to the
        change, and makes it easy to show in the demonstration that exactly one
        road's cost moved.
        """
        if not update.changed:
            return
        self._rebuild_road(update.road_id)

    def _rebuild_road(self, road_id: str) -> None:
        road = self.network.get_road(road_id)

        for endpoint in (road.from_node, road.to_node):
            self._adjacency[endpoint] = [
                edge for edge in self._adjacency[endpoint] if edge.road_id != road_id
            ]

        if road.is_traversable:
            cost = road.cost
            self._adjacency[road.from_node].append(
                Edge(road.id, road.from_node, road.to_node, cost)
            )
            self._adjacency[road.to_node].append(
                Edge(road.id, road.to_node, road.from_node, cost)
            )
            for endpoint in (road.from_node, road.to_node):
                self._adjacency[endpoint].sort(key=lambda e: e.to_node)

        self.rebuild_count += 1

    # -- the interface the search uses --------------------------------------

    def neighbours(self, node_id: str) -> list[Edge]:
        """
        The traversable, costed edges leaving `node_id`.

        This is the transition model of the search problem: the actions
        available in a state, and what each of them costs.
        """
        if node_id not in self._adjacency:
            raise KeyError(f"Unknown location: {node_id!r}")
        return self._adjacency[node_id]

    def has_node(self, node_id: str) -> bool:
        return node_id in self._adjacency

    # -- queries ------------------------------------------------------------

    @property
    def nodes(self) -> list[Node]:
        return self.network.nodes

    def edges(self) -> list[Edge]:
        """Every directed edge currently in the graph."""
        return [edge for edges in self._adjacency.values() for edge in edges]

    def edge_count(self) -> int:
        """Number of *roads* currently traversable (not directed edges)."""
        return sum(1 for road in self.network.roads if road.is_traversable)

    def cost_of_road(self, road_id: str) -> int | None:
        road = self.network.get_road(road_id)
        return road.cost if road.is_traversable else None

    def cost_between(self, a: str, b: str) -> int | None:
        """The cost of travelling directly from `a` to `b`, if a road allows it."""
        for edge in self.neighbours(a):
            if edge.to_node == b:
                return edge.cost
        return None

    def edge_between(self, a: str, b: str) -> Edge | None:
        for edge in self.neighbours(a):
            if edge.to_node == b:
                return edge
        return None

    def path_cost(self, path: list[str]) -> int | None:
        """
        Total cost of walking `path` under *current* conditions, or None if any
        step is no longer possible.

        The navigation module uses this to re-price the route a user is already
        following after traffic changes. Comparing a fresh search result against
        a route's remembered cost would be meaningless -- the old number was
        computed under the old conditions.
        """
        if len(path) < 2:
            return 0
        total = 0
        for current, following in zip(path, path[1:]):
            step = self.cost_between(current, following)
            if step is None:
                return None
            total += step
        return total

    def is_path_valid(self, path: list[str]) -> bool:
        return self.path_cost(path) is not None

    # -- reporting ----------------------------------------------------------

    def cost_table(self) -> list[dict]:
        """Every road with the arithmetic behind its current cost, for display."""
        table = []
        for road in self.network.roads:
            traversable = road.is_traversable
            table.append(
                {
                    "roadId": road.id,
                    "from": road.from_node,
                    "to": road.to_node,
                    "distance": road.distance,
                    "baseTravelTime": road.base_travel_time,
                    "traffic": road.traffic.value,
                    "roadStatus": road.road_status.value,
                    "trafficDelay": road.traffic_delay if traversable else None,
                    "cost": road.cost if traversable else None,
                    "traversable": traversable,
                }
            )
        return table

    def summary(self) -> str:
        available = self.edge_count()
        blocked = len(self.network.roads) - available
        lines = [
            f"Weighted graph: {len(self._adjacency)} nodes, {available} traversable roads"
            + (f" ({blocked} blocked)" if blocked else ""),
            "",
            "  edge cost = base travel time + traffic delay",
            "",
        ]
        for node_id in sorted(self._adjacency):
            edges = self._adjacency[node_id]
            if edges:
                shown = ", ".join(f"{edge.to_node}:{edge.cost}" for edge in edges)
            else:
                shown = "(isolated -- no traversable road)"
            lines.append(f"  {node_id} -> {shown}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"WeightedGraph(nodes={len(self._adjacency)}, "
            f"traversableRoads={self.edge_count()})"
        )


def build_graph(path: str | None = None) -> tuple[RoadNetwork, TrafficData, WeightedGraph]:
    """Convenience wiring of Modules 2, 3 and 4 in dependency order."""
    network = RoadNetwork.from_json_file(path)
    traffic = TrafficData(network)
    graph = WeightedGraph(network, traffic)
    return network, traffic, graph


if __name__ == "__main__":  # pragma: no cover - Phase 6 verification helper
    _network, _traffic, _graph = build_graph()
    print(_graph.summary())
