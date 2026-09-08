"""Shared fixtures for the test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make the `app` package importable when pytest is run from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models import Edge                       # noqa: E402
from app.navigation import NavigationSession      # noqa: E402
from app.weighted_graph import build_graph        # noqa: E402


@pytest.fixture
def system():
    """A freshly loaded network, traffic model and weighted graph."""
    network, traffic, graph = build_graph()
    return network, traffic, graph


@pytest.fixture
def network(system):
    return system[0]


@pytest.fixture
def traffic(system):
    return system[1]


@pytest.fixture
def graph(system):
    return system[2]


@pytest.fixture
def session(system):
    """A navigation session over a freshly loaded system."""
    return NavigationSession(*system)


class ToyGraph:
    """
    A minimal hand-built graph, used to test the search engine in isolation from
    the road network and traffic modules.
    """

    def __init__(self, roads: list[tuple[str, str, str, int]]):
        self.adjacency: dict[str, list[Edge]] = {}
        for road_id, a, b, cost in roads:
            self.adjacency.setdefault(a, []).append(Edge(road_id, a, b, cost))
            self.adjacency.setdefault(b, []).append(Edge(road_id, b, a, cost))

    def neighbours(self, node_id: str) -> list[Edge]:
        return self.adjacency.get(node_id, [])

    def has_node(self, node_id: str) -> bool:
        return node_id in self.adjacency


@pytest.fixture
def toy_graph():
    """
    The four-node example from the project specification.

        A = College, B = Junction 1, C = Junction 2, D = Railway Station

    Costs are chosen so that the cheaper route (A-C-D = 10) is discovered after
    the more expensive one (A-B-D = 14), which is what makes it a useful test of
    where the goal test is performed.
    """
    return ToyGraph(
        [
            ("r1", "A", "B", 4),
            ("r2", "A", "C", 6),
            ("r3", "B", "D", 10),
            ("r4", "C", "D", 4),
        ]
    )


def all_simple_routes(network, graph, source: str, destination: str):
    """
    Every simple route between two locations, with its cost under current
    conditions -- an independent check on what the search returns.
    """
    adjacency = {
        node_id: [edge.to_node for edge in graph.neighbours(node_id)]
        for node_id in network.node_ids
    }

    found = []
    stack = [(source, [source], {source})]
    while stack:
        current, path, seen = stack.pop()
        if current == destination:
            found.append((graph.path_cost(path), list(path)))
            continue
        for neighbour in adjacency[current]:
            if neighbour not in seen:
                stack.append((neighbour, path + [neighbour], seen | {neighbour}))
    return found
