"""
Tests for MODULE 1 (input processing) and MODULE 6 (optimal navigation),
including the eight test cases required by the project specification.

    Test 1  normal traffic finds the optimal route     -> test_ucs_engine.py
    Test 2  traffic rises, the system recalculates     -> here
    Test 3  a blocked road is avoided                  -> test_traffic_and_graph.py
    Test 4  invalid source                             -> here
    Test 5  invalid destination                        -> here
    Test 6  source equals destination                  -> here
    Test 7  no possible route                          -> here and test_ucs_engine.py
    Test 8  the cheapest of several routes is chosen   -> test_ucs_engine.py
"""

from __future__ import annotations

import random

from app.input_processing import ValidationError
from app.models import TrafficLevel
from app.navigation import RerouteDecision


# ---------------------------------------------------------------------------
# MODULE 1 -- input validation
# ---------------------------------------------------------------------------

# TEST CASE 4 -- invalid source
def test_invalid_source(session):
    result = session.find_route("Airport", "Railway Station")
    assert not result.success
    assert result.validation.error is ValidationError.UNKNOWN_SOURCE
    assert result.validation.field == "source"
    assert "not a location" in result.validation.message
    assert result.search is None, "no search should run on invalid input"


# TEST CASE 5 -- invalid destination
def test_invalid_destination(session):
    result = session.find_route("College Main Gate", "Moon Base")
    assert not result.success
    assert result.validation.error is ValidationError.UNKNOWN_DESTINATION
    assert result.validation.field == "destination"
    assert result.search is None


# TEST CASE 6 -- source equals destination
def test_same_source_and_destination(session):
    result = session.find_route("College Main Gate", "College Main Gate")
    assert not result.success
    assert result.validation.error is ValidationError.SAME_LOCATION
    assert "different locations" in result.validation.message


def test_same_location_detected_across_id_and_name(session):
    """"A" and "College Main Gate" are the same place written two ways."""
    result = session.find_route("A", "College Main Gate")
    assert result.validation.error is ValidationError.SAME_LOCATION


def test_empty_inputs_are_rejected(session):
    assert session.find_route("", "K").validation.error is ValidationError.EMPTY_SOURCE
    assert session.find_route("   ", "K").validation.error is ValidationError.EMPTY_SOURCE
    assert session.find_route("A", "").validation.error is ValidationError.EMPTY_DESTINATION
    assert session.find_route("A", None).validation.error is ValidationError.EMPTY_DESTINATION
    assert session.find_route(None, "K").validation.error is ValidationError.EMPTY_SOURCE


# TEST CASE 7 -- no possible route
def test_no_route_available(session):
    result = session.find_route("College Main Gate", "Island Fishing Village")
    assert not result.success
    assert result.validation.error is ValidationError.NO_POSSIBLE_ROUTE
    assert "No route available" in result.validation.message
    assert "not joined by any road" in result.validation.message


def test_no_route_when_every_connecting_road_is_blocked(session, traffic):
    """
    A different cause of the same outcome, and the message distinguishes them:
    the roads exist but are all closed.
    """
    for road_id in ("R01", "R02", "R03"):        # every road out of A
        traffic.apply_update(road_id, traffic=TrafficLevel.BLOCKED)

    result = session.find_route("College Main Gate", "Railway Station")
    assert not result.success
    assert result.validation.error is ValidationError.NO_POSSIBLE_ROUTE
    assert "currently blocked" in result.validation.message


def test_valid_request_is_accepted(session):
    result = session.find_route("College Main Gate", "Railway Station")
    assert result.success
    assert result.validation.valid
    assert result.validation.request.source == "A"
    assert result.validation.request.destination == "K"


def test_locations_are_listed_for_the_interface(session):
    locations = session.input_processing.available_locations()
    assert len(locations) == 16
    assert {"id": "K", "name": "Railway Station"} in locations


# ---------------------------------------------------------------------------
# MODULE 6 -- presenting a route
# ---------------------------------------------------------------------------

def test_route_presentation_is_complete(session):
    route = session.find_route("College Main Gate", "Railway Station").route

    assert route.path == ["A", "C", "F", "N", "I", "K"]
    assert route.path_names[0] == "College Main Gate"
    assert route.path_names[-1] == "Railway Station"
    assert route.total_cost == 35
    assert route.base_time == 30
    assert route.total_delay == 5
    assert route.base_time + route.total_delay == route.total_cost
    assert route.road_ids == ["R02", "R07", "R13", "R23", "R18"]
    assert route.worst_traffic == "medium"
    assert route.nodes_explored == 13


def test_route_steps_accumulate_to_the_total(session):
    route = session.find_route("College Main Gate", "Railway Station").route
    assert [step.cumulative_cost for step in route.steps] == [5, 11, 16, 21, 35]
    assert route.steps[-1].cumulative_cost == route.total_cost
    for step in route.steps:
        assert step.cost == step.base_travel_time + step.traffic_delay


# ---------------------------------------------------------------------------
# TEST CASE 2 -- traffic rises on the active route, the system recalculates
# ---------------------------------------------------------------------------

def test_reroute_on_congestion(session):
    first = session.find_route("College Main Gate", "Railway Station")
    assert first.route.total_cost == 35
    assert "R18" in first.route.road_ids

    result = session.update_traffic("R18", TrafficLevel.HIGH)

    assert result.decision is RerouteDecision.CHEAPER_ROUTE_FOUND
    assert result.headline == "Route Updated"
    assert result.route.path == ["A", "C", "E", "H", "J", "K"]
    assert result.route.total_cost == 39
    assert result.previous_cost_now == 42
    assert result.saving == 3


def test_reroute_compares_against_the_repriced_old_route(session):
    """
    The comparison must use the old route's cost under NEW conditions (42), not
    the cost it had when it was chosen (35). Comparing against 35 would make the
    new 39-minute route look worse and no reroute would happen.
    """
    first = session.find_route("College Main Gate", "Railway Station")
    original_cost = first.route.total_cost

    result = session.update_traffic("R18", TrafficLevel.HIGH)

    assert original_cost == 35
    assert result.previous_cost_now == 42
    assert result.route.total_cost == 39
    assert result.previous_cost_now > result.route.total_cost > original_cost


def test_reroute_reason_distinguishes_worse_route_from_better_alternative(session):
    session.find_route("College Main Gate", "Railway Station")
    worse = session.update_traffic("R18", TrafficLevel.HIGH)
    assert "Heavy traffic detected on the previous route" in worse.reason

    # Now clear that road again: the active route did not get worse, another
    # route got better, and the explanation should say so.
    better = session.update_traffic("R18", TrafficLevel.LOW)
    assert better.decision is RerouteDecision.CHEAPER_ROUTE_FOUND
    assert "Traffic has eased elsewhere" in better.reason


def test_traffic_change_off_the_route_leaves_it_alone(session):
    first = session.find_route("College Main Gate", "Railway Station")
    result = session.update_traffic("R15", TrafficLevel.HIGH)   # G-L, far from the route

    assert result.decision is RerouteDecision.UNCHANGED
    assert result.headline == "Route unchanged"
    assert result.route.path == first.route.path
    assert result.route.total_cost == 35


def test_route_can_stay_optimal_while_getting_slower(session):
    """
    A small rise on the active route may still leave it the best option. The
    route is kept, but the user is told the cost has changed.
    """
    session.find_route("College Main Gate", "Railway Station")
    result = session.update_traffic("R02", TrafficLevel.MEDIUM)   # 5 -> 10 on the route

    assert result.decision is RerouteDecision.UNCHANGED
    assert result.route.path == ["A", "C", "F", "N", "I", "K"]
    assert result.route.total_cost == 40
    assert "longer" in result.reason


# ---------------------------------------------------------------------------
# Rerouting when a road on the active route is blocked
# ---------------------------------------------------------------------------

def test_reroute_when_the_active_route_is_blocked(session):
    first = session.find_route("College Main Gate", "Railway Station")
    assert "R02" in first.route.road_ids

    result = session.update_traffic("R02", TrafficLevel.BLOCKED)

    assert result.decision is RerouteDecision.ROUTE_BLOCKED
    assert result.headline == "Route Updated"
    assert result.previous_cost_now is None
    assert result.route.path == ["A", "B", "D", "L", "K"]
    assert result.route.total_cost == 40
    assert "R02" not in result.route.road_ids
    assert "R02" in result.reason


def test_navigation_reports_when_no_route_survives(session, traffic):
    session.find_route("College Main Gate", "Hilltop Observatory")
    result = session.update_traffic("R19", TrafficLevel.BLOCKED)

    assert result.decision is RerouteDecision.NO_ROUTE
    assert result.headline == "No route available"
    assert result.route is None
    assert session.active_route is None


def test_traffic_update_without_an_active_route(session):
    result = session.update_traffic("R18", TrafficLevel.HIGH)
    assert result.success
    assert result.decision is RerouteDecision.UNCHANGED
    assert "No route is currently being followed" in result.reason


# ---------------------------------------------------------------------------
# The full dynamic cycle
# ---------------------------------------------------------------------------

def test_route_recovers_when_traffic_clears(session):
    session.find_route("College Main Gate", "Railway Station")
    session.update_traffic("R18", TrafficLevel.HIGH)
    assert session.active_route.path == ["A", "C", "E", "H", "J", "K"]

    session.update_traffic("R18", TrafficLevel.LOW)
    assert session.active_route.path == ["A", "C", "F", "N", "I", "K"]
    assert session.active_route.total_cost == 30      # 9 + 0 on R18 now


def test_repeated_changes_keep_the_route_optimal(session, network, graph):
    """
    After every change, whatever the sequence, the active route must still be
    the cheapest available. Checked against a fresh brute-force minimum.
    """
    from conftest import all_simple_routes

    rng = random.Random(4242)
    session.find_route("College Main Gate", "Railway Station")

    for _ in range(25):
        road = rng.choice(network.roads)
        level = rng.choice([TrafficLevel.LOW, TrafficLevel.MEDIUM, TrafficLevel.HIGH])
        session.update_traffic(road.id, level)

        cheapest = min(cost for cost, _ in all_simple_routes(network, graph, "A", "K"))
        assert session.active_route is not None
        assert session.active_route.total_cost == cheapest


def test_auto_simulation_produces_a_change_and_reroutes(session):
    session.find_route("College Main Gate", "Railway Station")
    rng = random.Random(7)

    for _ in range(10):
        result = session.simulate_random_change(rng)
        assert result.success
        assert result.traffic_update is not None
        assert session.active_route is not None


def test_auto_simulation_does_not_block_roads_by_default(session, network):
    rng = random.Random(11)
    for _ in range(40):
        session.simulate_random_change(rng)
    assert all(road.is_traversable for road in network.roads)


def test_history_records_every_decision(session):
    session.find_route("College Main Gate", "Railway Station")
    session.update_traffic("R18", TrafficLevel.HIGH)
    session.update_traffic("R02", TrafficLevel.BLOCKED)

    decisions = [entry.decision for entry in session.history]
    assert decisions[0] is RerouteDecision.INITIAL_ROUTE
    assert RerouteDecision.CHEAPER_ROUTE_FOUND in decisions
    assert len(session.history) == 3
