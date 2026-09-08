"""
Tests for MODULE 2 (road network), MODULE 3 (traffic data) and MODULE 4
(weighted graph) -- the structure, the cost model, and the link between them.
"""

from __future__ import annotations

import pytest

from app.models import RoadStatus, TrafficLevel, traffic_delay
from app.ucs_engine import uniform_cost_search


# ---------------------------------------------------------------------------
# Module 2 -- the road network
# ---------------------------------------------------------------------------

def test_network_size(network):
    assert len(network.nodes) == 16
    assert len(network.roads) == 24


def test_expected_node_degrees(network):
    expected = {
        "A": 3, "B": 3, "C": 3, "D": 3, "E": 5, "F": 3, "G": 4, "H": 4,
        "I": 3, "J": 4, "K": 3, "L": 4, "M": 1, "N": 3, "Y": 1, "Z": 1,
    }
    assert {node_id: network.degree(node_id) for node_id in expected} == expected


def test_network_has_two_components(network):
    """A mainland of fourteen locations, and a two-location island."""
    components = network.components(traversable_only=False)
    assert len(components) == 2
    assert sorted(len(component) for component in components) == [2, 14]
    assert {"Y", "Z"} in components


def test_roads_are_bidirectional(network, graph):
    """Every road must be usable in both directions at the same cost."""
    for road in network.roads:
        if not road.is_traversable:
            continue
        forward = graph.cost_between(road.from_node, road.to_node)
        backward = graph.cost_between(road.to_node, road.from_node)
        assert forward == backward == road.cost


def test_locations_resolve_by_name_and_by_id(network):
    assert network.resolve("K") == "K"
    assert network.resolve("k") == "K"
    assert network.resolve("Railway Station") == "K"
    assert network.resolve("  railway station  ") == "K"
    assert network.resolve("Nowhere") is None
    assert network.resolve("") is None


def test_every_road_has_a_positive_base_travel_time(network):
    """Zero-cost edges would allow cost-free cycles; the loader rejects them."""
    assert all(road.base_travel_time > 0 for road in network.roads)


# ---------------------------------------------------------------------------
# Module 3 -- the traffic delay model
# ---------------------------------------------------------------------------

def test_traffic_delay_model():
    assert traffic_delay(TrafficLevel.LOW) == 0
    assert traffic_delay(TrafficLevel.MEDIUM) == 5
    assert traffic_delay(TrafficLevel.HIGH) == 12


def test_blocked_traffic_has_no_delay_value():
    """
    A blocked road must be excluded from the graph, not given a large cost, so
    asking for its delay is a programming error rather than a number.
    """
    with pytest.raises(ValueError):
        traffic_delay(TrafficLevel.BLOCKED)


def test_edge_cost_is_base_time_plus_delay(network):
    """The cost formula, checked on a road of each traffic level."""
    for road_id, expected in [("R02", 5), ("R01", 11), ("R03", 19)]:
        road = network.get_road(road_id)
        assert road.cost == road.base_travel_time + road.traffic_delay == expected


def test_initial_traffic_mix(traffic):
    """A realistic spread, with no road closed at the start."""
    counts = traffic.counts_by_level()
    assert counts == {"low": 13, "medium": 8, "high": 3, "blocked": 0}
    assert sum(counts.values()) == 24


def test_blocked_road_has_no_cost(network, traffic):
    traffic.apply_update("R02", traffic=TrafficLevel.BLOCKED)
    road = network.get_road("R02")
    assert not road.is_traversable
    assert traffic.cost_of("R02") is None
    with pytest.raises(ValueError):
        _ = road.cost


def test_traffic_and_road_status_are_separate_concerns(network, traffic):
    """
    A road can be closed while its congestion level stays low -- closure is a
    physical fact, congestion is a measurement. Either makes the road unusable.
    """
    traffic.apply_update("R02", road_status=RoadStatus.BLOCKED)
    road = network.get_road("R02")
    assert road.traffic is TrafficLevel.LOW
    assert road.road_status is RoadStatus.BLOCKED
    assert not road.is_traversable


def test_selecting_blocked_traffic_also_closes_the_road(network, traffic):
    """What a user means by choosing 'Blocked' in the interface."""
    traffic.apply_update("R02", traffic=TrafficLevel.BLOCKED)
    road = network.get_road("R02")
    assert road.road_status is RoadStatus.BLOCKED
    assert not road.is_traversable


def test_setting_a_normal_level_reopens_a_closed_road(network, traffic):
    traffic.apply_update("R02", traffic=TrafficLevel.BLOCKED)
    traffic.apply_update("R02", traffic=TrafficLevel.MEDIUM)
    road = network.get_road("R02")
    assert road.is_traversable
    assert road.cost == road.base_travel_time + 5


def test_setting_the_level_already_in_force_changes_nothing(traffic):
    """Should be a no-op, not a spurious change that triggers a reroute."""
    update = traffic.apply_update("R02", traffic=TrafficLevel.LOW)
    assert not update.changed
    assert update.previous_cost == update.new_cost


def test_unknown_road_is_rejected(traffic):
    with pytest.raises(KeyError):
        traffic.apply_update("R99", traffic=TrafficLevel.HIGH)


def test_reset_restores_the_original_conditions(network, traffic):
    original = {road.id: (road.traffic, road.road_status) for road in network.roads}
    traffic.apply_update("R02", traffic=TrafficLevel.BLOCKED)
    traffic.apply_update("R18", traffic=TrafficLevel.HIGH)
    traffic.reset()
    assert {road.id: (road.traffic, road.road_status) for road in network.roads} == original


# ---------------------------------------------------------------------------
# Module 4 -- the weighted graph, and its link to traffic
# ---------------------------------------------------------------------------

def test_graph_costs_match_the_reference_table(graph):
    """The hand-computed edge costs under the initial traffic conditions."""
    expected = {
        "R01": 11, "R02": 5,  "R03": 19, "R04": 6,  "R05": 10, "R06": 11,
        "R07": 6,  "R08": 7,  "R09": 13, "R10": 13, "R11": 8,  "R12": 19,
        "R13": 5,  "R14": 11, "R15": 21, "R16": 7,  "R17": 9,  "R18": 14,
        "R19": 11, "R20": 8,  "R21": 13, "R22": 10, "R23": 5,  "R24": 4,
    }
    assert {road_id: graph.cost_of_road(road_id) for road_id in expected} == expected


def test_traffic_change_updates_the_graph_automatically(traffic, graph):
    """
    The chain the project is built around: a traffic change re-costs the edge
    without any caller having to rebuild the graph.
    """
    assert graph.cost_of_road("R18") == 14
    traffic.apply_update("R18", traffic=TrafficLevel.HIGH)
    assert graph.cost_of_road("R18") == 21          # 9 base + 12 delay


def test_traffic_change_affects_only_the_road_that_changed(traffic, graph):
    before = {road_id: graph.cost_of_road(road_id) for road_id in
              [row["roadId"] for row in graph.cost_table()]}
    traffic.apply_update("R18", traffic=TrafficLevel.HIGH)
    after = {road_id: graph.cost_of_road(road_id) for road_id in before}

    changed = {road_id for road_id in before if before[road_id] != after[road_id]}
    assert changed == {"R18"}


def test_blocked_road_is_removed_from_the_graph(traffic, graph):
    """Not made expensive -- removed. A closed road is not an available action."""
    assert graph.cost_between("A", "C") == 5
    traffic.apply_update("R02", traffic=TrafficLevel.BLOCKED)
    assert graph.cost_between("A", "C") is None
    assert graph.cost_between("C", "A") is None
    assert "R02" not in {edge.road_id for edge in graph.edges()}


def test_reopening_a_road_restores_both_directions(traffic, graph):
    traffic.apply_update("R02", traffic=TrafficLevel.BLOCKED)
    traffic.apply_update("R02", traffic=TrafficLevel.LOW)
    assert graph.cost_between("A", "C") == 5
    assert graph.cost_between("C", "A") == 5


def test_path_cost_prices_a_route_under_current_conditions(graph, traffic):
    route = ["A", "C", "F", "N", "I", "K"]
    assert graph.path_cost(route) == 35
    traffic.apply_update("R18", traffic=TrafficLevel.HIGH)
    assert graph.path_cost(route) == 42          # the same route, re-priced


def test_path_cost_is_none_when_a_route_is_broken(graph, traffic):
    route = ["A", "C", "F", "N", "I", "K"]
    traffic.apply_update("R02", traffic=TrafficLevel.BLOCKED)
    assert graph.path_cost(route) is None
    assert not graph.is_path_valid(route)


# ---------------------------------------------------------------------------
# TEST CASE 3 -- blocking a road makes UCS avoid it
# ---------------------------------------------------------------------------

def test_ucs_avoids_a_blocked_road(network, traffic, graph):
    before = uniform_cost_search(graph, "A", "K")
    assert "R02" in {edge.road_id for edge in before.edges}

    traffic.apply_update("R02", traffic=TrafficLevel.BLOCKED)
    after = uniform_cost_search(graph, "A", "K")

    assert after.found
    assert "R02" not in {edge.road_id for edge in after.edges}
    assert after.path == ["A", "B", "D", "L", "K"]
    assert after.total_cost == 40


def test_blocking_the_only_road_to_a_location_isolates_it(network, traffic, graph):
    """R19 is the sole road serving Hilltop Observatory."""
    before = uniform_cost_search(graph, "A", "M")
    assert before.found and before.total_cost == 32

    traffic.apply_update("R19", traffic=TrafficLevel.BLOCKED)
    after = uniform_cost_search(graph, "A", "M")

    assert not after.found
    assert network.degree("M") == 1
    assert graph.neighbours("M") == []
