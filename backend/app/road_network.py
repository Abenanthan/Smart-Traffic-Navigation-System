"""
MODULE 2 -- ROAD NETWORK
========================

Input   : locations, junctions, roads, connections, distance, base travel time
Process : represent every location/junction as a node, every road as an edge,
          store distance and base travel time, maintain connections between
          nodes, and support roads being open or blocked
Output  : a structured road network

This module is the *static* description of the city. It knows nothing about
congestion (that is Module 3) and nothing about search (that is Module 5). It
answers structural questions only: which locations exist, which roads exist, and
what connects to what.
"""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

from .models import Node, Road, RoadStatus, TrafficLevel

#: Default location of the network description, relative to backend/
DEFAULT_NETWORK_FILE = Path(__file__).resolve().parent.parent / "data" / "road_network.json"


class RoadNetwork:
    """
    The structured road network: nodes (locations) and roads (connections).

    The network is stored as an adjacency map so that neighbour lookup -- the
    operation UCS performs most often -- is O(degree) rather than a scan of
    every road.
    """

    def __init__(self, nodes: list[Node], roads: list[Road], metadata: dict | None = None):
        self.metadata = metadata or {}

        self._nodes: dict[str, Node] = {}
        for node in nodes:
            if node.id in self._nodes:
                raise ValueError(f"Duplicate node id in network data: {node.id!r}")
            self._nodes[node.id] = node

        self._roads: dict[str, Road] = {}
        #: node id -> list of road ids touching that node (either direction)
        self._adjacency: dict[str, list[str]] = {node_id: [] for node_id in self._nodes}

        for road in roads:
            self._register_road(road)

        #: name lookup for Module 1, so a user may type "Railway Station" or "K"
        self._by_name: dict[str, str] = {
            node.name.strip().casefold(): node.id for node in self._nodes.values()
        }

    # -- construction -------------------------------------------------------

    def _register_road(self, road: Road) -> None:
        if road.id in self._roads:
            raise ValueError(f"Duplicate road id in network data: {road.id!r}")
        for endpoint in (road.from_node, road.to_node):
            if endpoint not in self._nodes:
                raise ValueError(
                    f"Road {road.id} refers to unknown location {endpoint!r}. "
                    f"Every road endpoint must be a declared node."
                )
        if road.from_node == road.to_node:
            raise ValueError(f"Road {road.id} is a self-loop at {road.from_node!r}")
        if road.base_travel_time <= 0:
            raise ValueError(
                f"Road {road.id} has base travel time {road.base_travel_time}. "
                f"Travel times must be positive, otherwise zero-cost cycles become "
                f"possible and the search could stall."
            )

        self._roads[road.id] = road
        # Roads are bidirectional, so each road appears in both endpoints' lists.
        self._adjacency[road.from_node].append(road.id)
        self._adjacency[road.to_node].append(road.id)

    @classmethod
    def from_json_file(cls, path: str | Path | None = None) -> "RoadNetwork":
        """Load a road network from a JSON description on disk."""
        path = Path(path) if path is not None else DEFAULT_NETWORK_FILE
        if not path.exists():
            raise FileNotFoundError(f"Road network file not found: {path}")
        with path.open("r", encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))

    @classmethod
    def from_dict(cls, data: dict) -> "RoadNetwork":
        """Build a road network from an already-parsed JSON structure."""
        nodes = [
            Node(
                id=entry["id"],
                name=entry.get("name", entry["id"]),
                x=float(entry.get("x", 0.0)),
                y=float(entry.get("y", 0.0)),
            )
            for entry in data.get("nodes", [])
        ]
        roads = [
            Road(
                id=entry["id"],
                from_node=entry["from"],
                to_node=entry["to"],
                distance=float(entry.get("distance", 0.0)),
                base_travel_time=int(entry["baseTravelTime"]),
                traffic=TrafficLevel(entry.get("traffic", "low")),
                road_status=RoadStatus(entry.get("roadStatus", "open")),
            )
            for entry in data.get("roads", [])
        ]
        if not nodes:
            raise ValueError("Road network contains no locations.")
        if not roads:
            raise ValueError("Road network contains no roads.")
        return cls(nodes, roads, metadata=data.get("metadata", {}))

    # -- node queries -------------------------------------------------------

    @property
    def nodes(self) -> list[Node]:
        return list(self._nodes.values())

    @property
    def node_ids(self) -> list[str]:
        return list(self._nodes.keys())

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def get_node(self, node_id: str) -> Node:
        if node_id not in self._nodes:
            raise KeyError(f"Unknown location: {node_id!r}")
        return self._nodes[node_id]

    def resolve(self, text: str) -> str | None:
        """
        Turn user text into a node id, accepting either the id ("K") or the
        full location name ("Railway Station"), case- and space-insensitively.

        Returns None if the text matches nothing -- Module 1 turns that into a
        user-facing validation error.
        """
        if text is None:
            return None
        cleaned = text.strip()
        if not cleaned:
            return None
        if cleaned in self._nodes:                     # exact id, e.g. "K"
            return cleaned
        upper = cleaned.upper()
        if upper in self._nodes:                       # lowercase id, e.g. "k"
            return upper
        return self._by_name.get(cleaned.casefold())   # location name

    # -- road queries -------------------------------------------------------

    @property
    def roads(self) -> list[Road]:
        return list(self._roads.values())

    def has_road(self, road_id: str) -> bool:
        return road_id in self._roads

    def get_road(self, road_id: str) -> Road:
        if road_id not in self._roads:
            raise KeyError(f"Unknown road: {road_id!r}")
        return self._roads[road_id]

    def roads_at(self, node_id: str) -> list[Road]:
        """Every road touching `node_id`, regardless of traffic or status."""
        if node_id not in self._adjacency:
            raise KeyError(f"Unknown location: {node_id!r}")
        return [self._roads[road_id] for road_id in self._adjacency[node_id]]

    def road_between(self, a: str, b: str) -> Road | None:
        """The road joining `a` and `b`, if one exists."""
        for road in self.roads_at(a):
            if road.connects(a, b):
                return road
        return None

    def degree(self, node_id: str) -> int:
        return len(self._adjacency[node_id])

    # -- structural analysis ------------------------------------------------

    def is_connected(self, source: str, destination: str, *, traversable_only: bool = True) -> bool:
        """
        Breadth-first reachability check used by Module 1 to answer "could a
        route possibly exist?" before UCS is ever invoked.

        This is a structural test, not a search for the best route: it ignores
        cost entirely. With `traversable_only=True` it respects current traffic
        and road status; with False it asks whether the roads exist at all.
        """
        if source not in self._nodes or destination not in self._nodes:
            return False
        if source == destination:
            return True

        seen = {source}
        queue = deque([source])
        while queue:
            current = queue.popleft()
            for road in self.roads_at(current):
                if traversable_only and not road.is_traversable:
                    continue
                neighbour = road.other_end(current)
                if neighbour == destination:
                    return True
                if neighbour not in seen:
                    seen.add(neighbour)
                    queue.append(neighbour)
        return False

    def reachable_from(self, source: str, *, traversable_only: bool = True) -> set[str]:
        """Every location reachable from `source` (including `source` itself)."""
        seen = {source}
        queue = deque([source])
        while queue:
            current = queue.popleft()
            for road in self.roads_at(current):
                if traversable_only and not road.is_traversable:
                    continue
                neighbour = road.other_end(current)
                if neighbour not in seen:
                    seen.add(neighbour)
                    queue.append(neighbour)
        return seen

    def components(self, *, traversable_only: bool = True) -> list[set[str]]:
        """
        The connected components of the network. Used in the demonstration to
        show that "No route available" is a genuine disconnection rather than a
        failure of the search.
        """
        unassigned = set(self._nodes)
        found: list[set[str]] = []
        while unassigned:
            start = min(unassigned)
            component = self.reachable_from(start, traversable_only=traversable_only)
            found.append(component)
            unassigned -= component
        return found

    # -- reporting ----------------------------------------------------------

    def summary(self) -> str:
        """Human-readable structural summary, printed by the Phase 1/2 checks."""
        lines = [
            f"Road network: {len(self._nodes)} locations, {len(self._roads)} roads",
            "",
            "LOCATIONS",
        ]
        for node in self._nodes.values():
            neighbours = sorted(
                road.other_end(node.id) for road in self.roads_at(node.id)
            )
            lines.append(
                f"  {node.id}  {node.name:<24} degree {self.degree(node.id)}  "
                f"-> {', '.join(neighbours)}"
            )

        lines += ["", "ROADS"]
        for road in self._roads.values():
            lines.append(f"  {road}")

        components = self.components(traversable_only=False)
        lines += ["", f"CONNECTED COMPONENTS ({len(components)})"]
        for index, component in enumerate(components, start=1):
            lines.append(f"  {index}. {{{', '.join(sorted(component))}}}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"RoadNetwork(nodes={len(self._nodes)}, roads={len(self._roads)})"


if __name__ == "__main__":  # pragma: no cover - Phase 1/2 verification helper
    print(RoadNetwork.from_json_file().summary())
