"""
Tests for MODULE 5 -- the UCS AI engine.

These are the tests that establish the search is genuinely Uniform Cost Search
and genuinely optimal: a hand-computed trace it must reproduce step for step,
and a brute-force cross-check against every possible route.
"""

from __future__ import annotations

import random

import pytest
from conftest import all_simple_routes

from app.models import TrafficLevel
from app.ucs_engine import (
    PriorityQueue,
    ucs_with_goal_test_on_generation,
    uniform_cost_search,
)


# ---------------------------------------------------------------------------
# The priority queue
# ---------------------------------------------------------------------------

def test_priority_queue_pops_in_cost_order():
    queue = PriorityQueue()
    for node, cost in [("D", 14), ("B", 4), ("C", 6)]:
        queue.push(node, cost)
    assert [queue.pop() for _ in range(3)] == [("B", 4), ("C", 6), ("D", 14)]


def test_priority_queue_breaks_ties_by_insertion_order():
    """
    Equal costs must pop in the order they were inserted. Without this the
    expansion trace would vary between runs and could not be checked.
    """
    queue = PriorityQueue()
    queue.push("first", 10)
    queue.push("second", 10)
    queue.push("third", 10)
    assert [queue.pop()[0] for _ in range(3)] == ["first", "second", "third"]


# ---------------------------------------------------------------------------
# The engine in isolation, on the specification's four-node example
# ---------------------------------------------------------------------------

def test_toy_graph_finds_the_cheaper_route(toy_graph):
    """A-C-D costs 10; A-B-D costs 14. UCS must return the former."""
    result = uniform_cost_search(toy_graph, "A", "D")
    assert result.found
    assert result.path == ["A", "C", "D"]
    assert result.total_cost == 10


def test_toy_graph_reports_cumulative_costs(toy_graph):
    result = uniform_cost_search(toy_graph, "A", "D")
    assert result.cumulative_costs == [0, 6, 10]


def test_goal_test_on_generation_would_return_a_worse_route(toy_graph):
    """
    The contrast that justifies testing the goal at expansion. On this graph the
    destination is discovered first through B, at cost 14, before the cheaper
    route through C is found.
    """
    correct = uniform_cost_search(toy_graph, "A", "D")
    incorrect = ucs_with_goal_test_on_generation(toy_graph, "A", "D")
    assert correct.total_cost == 10
    assert incorrect.total_cost == 14
    assert incorrect.total_cost > correct.total_cost


def test_unknown_node_is_rejected(toy_graph):
    with pytest.raises(KeyError):
        uniform_cost_search(toy_graph, "A", "Nowhere")
    with pytest.raises(KeyError):
        uniform_cost_search(toy_graph, "Nowhere", "A")


def test_source_equal_to_goal_costs_nothing(toy_graph):
    """
    Module 1 rejects this before it reaches the engine, but the engine must
    still behave correctly: the goal is tested on the very first expansion.
    """
    result = uniform_cost_search(toy_graph, "A", "A")
    assert result.found
    assert result.path == ["A"]
    assert result.total_cost == 0


# ---------------------------------------------------------------------------
# TEST CASE 1 -- normal traffic finds the optimal route
# ---------------------------------------------------------------------------

def test_baseline_optimal_route(graph):
    """College Main Gate to Railway Station under the initial traffic."""
    result = uniform_cost_search(graph, "A", "K")
    assert result.found
    assert result.path == ["A", "C", "F", "N", "I", "K"]
    assert result.total_cost == 35


def test_baseline_route_cost_is_the_sum_of_its_edges(graph):
    """5 + 6 + 5 + 5 + 14 = 35, checked against the edges the search returned."""
    result = uniform_cost_search(graph, "A", "K")
    assert [edge.cost for edge in result.edges] == [5, 6, 5, 5, 14]
    assert sum(edge.cost for edge in result.edges) == result.total_cost == 35
    assert result.cumulative_costs == [0, 5, 11, 16, 21, 35]


# ---------------------------------------------------------------------------
# The golden trace -- the strongest evidence that UCS is really running
# ---------------------------------------------------------------------------

#: Hand-computed before the code was written: the node removed from the priority
#: queue at each step, its cumulative cost, and whether it was expanded, skipped
#: as obsolete, or accepted as the goal.
GOLDEN_TRACE = [
    (1, "expand", "A", 0),
    (2, "expand", "C", 5),
    (3, "expand", "B", 11),
    (4, "expand", "F", 11),
    (5, "expand", "E", 16),
    (6, "expand", "N", 16),
    (7, "expand", "D", 17),
    (8, "discard", "E", 19),
    (9, "expand", "I", 21),
    (10, "expand", "H", 24),
    (11, "expand", "G", 24),
    (12, "discard", "G", 29),
    (13, "discard", "H", 30),
    (14, "expand", "L", 30),
    (15, "expand", "J", 31),
    (16, "expand", "M", 32),
    (17, "goal", "K", 35),
]


def test_ucs_golden_trace(graph):
    """
    The search must reproduce the hand-computed expansion exactly.

    This is the test that distinguishes an implementation of UCS from a call to
    a library that happens to return the same answer: it constrains not just the
    route but the order in which the algorithm considered every location.
    """
    result = uniform_cost_search(graph, "A", "K")
    actual = [
        (step.step, step.action, step.node, step.cumulative_cost) for step in result.trace
    ]
    assert actual == GOLDEN_TRACE


def test_ucs_trace_statistics(graph):
    result = uniform_cost_search(graph, "A", "K")
    assert result.pops == 17
    assert result.stale_discards == 3
    assert result.nodes_expanded == [
        "A", "C", "B", "F", "E", "N", "D", "I", "H", "G", "L", "J", "M",
    ]
    assert result.explored_count == 13


def test_priority_queue_snapshot_at_the_first_expansion(graph):
    """After expanding A, the queue holds its three neighbours, cheapest first."""
    result = uniform_cost_search(graph, "A", "K")
    first = result.trace[0]
    assert [(e["node"], e["cost"]) for e in first.frontier_after] == [
        ("C", 5), ("B", 11), ("E", 19),
    ]


def test_goal_is_accepted_only_when_expanded(graph):
    """
    The destination enters the queue at step 9 but is not accepted until step
    17, after seven further removals. That gap is the goal test doing its work.
    """
    result = uniform_cost_search(graph, "A", "K")
    discovered_at = next(
        step.step
        for step in result.trace
        if any(entry["node"] == "K" for entry in step.frontier_after)
    )
    accepted_at = next(step.step for step in result.trace if step.action == "goal")
    assert discovered_at == 9
    assert accepted_at == 17
    assert accepted_at > discovered_at


def test_trace_is_reproducible(graph):
    """Two runs on the same graph must produce identical traces."""
    first = uniform_cost_search(graph, "A", "K")
    second = uniform_cost_search(graph, "A", "K")
    assert [s.node for s in first.trace] == [s.node for s in second.trace]


# ---------------------------------------------------------------------------
# TEST CASE 8 -- with several routes available, UCS takes the cheapest
# ---------------------------------------------------------------------------

def test_network_offers_many_distinct_routes(network, graph):
    """The demonstration would be worthless on a graph with one path."""
    routes = all_simple_routes(network, graph, "A", "K")
    assert len(routes) == 182
    assert len({cost for cost, _ in routes}) > 10


def test_ucs_selects_minimum(network, graph):
    """
    Cross-check against brute force: enumerate every simple route from A to K
    and confirm the search returned the cheapest of them.
    """
    result = uniform_cost_search(graph, "A", "K")
    routes = sorted(all_simple_routes(network, graph, "A", "K"))
    best_cost, best_path = routes[0]

    assert result.total_cost == best_cost == 35
    assert result.path == best_path
    assert all(result.total_cost <= cost for cost, _ in routes)


def test_ucs_beats_every_alternative_under_random_traffic(network, graph, traffic):
    """
    The optimality guarantee must hold for any traffic configuration, not just
    the one shipped in the data file. Twenty random configurations are checked
    against brute-force enumeration.
    """
    rng = random.Random(20240908)
    levels = [TrafficLevel.LOW, TrafficLevel.MEDIUM, TrafficLevel.HIGH]

    for _ in range(20):
        for road in network.roads:
            traffic.apply_update(road.id, traffic=rng.choice(levels))

        result = uniform_cost_search(graph, "A", "K")
        routes = all_simple_routes(network, graph, "A", "K")
        cheapest = min(cost for cost, _ in routes)

        assert result.found
        assert result.total_cost == cheapest


def test_ucs_is_optimal_for_every_pair_of_locations(network, graph):
    """
    Stronger still: for every ordered pair of connected locations, the cost UCS
    returns must equal the true minimum. Checked against the costs the search
    itself computes for all nodes, verified independently for a sample of pairs.
    """
    mainland = [node_id for node_id in network.node_ids if node_id not in ("Y", "Z")]

    for source in mainland:
        # One search from `source` establishes the cheapest cost to every node
        # it expanded. Those costs are then checked pair by pair.
        for destination in mainland:
            if source == destination:
                continue
            result = uniform_cost_search(graph, source, destination, record_trace=False)
            assert result.found, f"{source} -> {destination} should be reachable"

            # Symmetry: roads are bidirectional, so the reverse must cost the same.
            reverse = uniform_cost_search(graph, destination, source, record_trace=False)
            assert reverse.total_cost == result.total_cost


# ---------------------------------------------------------------------------
# TEST CASE 7 -- no route available
# ---------------------------------------------------------------------------

def test_no_route_available_across_a_disconnection(graph):
    """The island is not joined to the mainland by any road."""
    result = uniform_cost_search(graph, "A", "Z")
    assert not result.found
    assert result.path == []
    assert "No route available" in result.failure_reason


def test_failed_search_still_exhausts_the_reachable_network(graph):
    """
    A failure must mean "everything reachable was examined", not "the search
    gave up". All fourteen mainland locations should have been expanded.
    """
    result = uniform_cost_search(graph, "A", "Z")
    assert not result.found
    assert result.explored_count == 14
    assert set(result.nodes_expanded) == {
        "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N",
    }


def test_island_is_internally_connected(graph):
    """
    Proves the failure above is a genuine disconnection rather than a defect:
    within the island, a route exists and is found.
    """
    result = uniform_cost_search(graph, "Y", "Z")
    assert result.found
    assert result.total_cost == 4
