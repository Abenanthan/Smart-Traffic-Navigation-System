"""
MODULE 6 -- OPTIMAL NAVIGATION
==============================

Input   : the route returned by UCS, its total cost, current traffic information
Process : present the selected route with its cost, travel time and traffic
          conditions; watch for simulated traffic changes; update the graph;
          run UCS again; compare the new result against the route being
          followed; and switch to the new route when it is better or when the
          current one has become unavailable
Output  : the optimal navigation route, the updated route after traffic changes,
          route statistics, and rerouting notifications

THE COMPARISON THAT MAKES REROUTING CORRECT
-------------------------------------------
When traffic changes, it is not enough to run UCS again and see whether the
answer differs. The route the user is already following must first be re-priced
under the *new* conditions. Its stored cost was computed under the old ones and
is now meaningless -- comparing a fresh search result against a stale number
would announce reroutes that save nothing, and miss ones that matter.

So the sequence is: re-price the current route, re-run UCS, then compare like
with like. `_decide` below is where that comparison happens, and it is the only
place in the system that decides whether to change route.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .input_processing import InputProcessing, ValidationResult
from .models import TrafficLevel
from .road_network import RoadNetwork
from .traffic_data import TrafficData, TrafficUpdate
from .ucs_engine import UCSResult, uniform_cost_search
from .weighted_graph import WeightedGraph


class RerouteDecision(str, Enum):
    """What happened to the active route after a change in traffic."""

    INITIAL_ROUTE = "initial_route"
    UNCHANGED = "unchanged"
    CHEAPER_ROUTE_FOUND = "cheaper_route_found"
    ROUTE_BLOCKED = "route_blocked"
    NO_ROUTE = "no_route"


@dataclass
class RouteStep:
    """One leg of a route, as shown in the navigation panel."""

    from_node: str
    to_node: str
    from_name: str
    to_name: str
    road_id: str
    base_travel_time: int
    traffic: str
    traffic_delay: int
    cost: int
    cumulative_cost: int

    def to_dict(self) -> dict:
        return {
            "from": self.from_node,
            "to": self.to_node,
            "fromName": self.from_name,
            "toName": self.to_name,
            "roadId": self.road_id,
            "baseTravelTime": self.base_travel_time,
            "traffic": self.traffic,
            "trafficDelay": self.traffic_delay,
            "cost": self.cost,
            "cumulativeCost": self.cumulative_cost,
        }


@dataclass
class Route:
    """A route ready to be displayed: the path, its cost, and its conditions."""

    source: str
    destination: str
    source_name: str
    destination_name: str
    path: list[str]
    path_names: list[str]
    steps: list[RouteStep]
    total_cost: int
    total_distance: float
    base_time: int
    total_delay: int
    road_ids: list[str]
    worst_traffic: str
    nodes_explored: int
    nodes_expanded: list[str] = field(default_factory=list)
    pops: int = 0

    def path_string(self, arrow: str = " -> ") -> str:
        return arrow.join(self.path)

    def named_string(self, arrow: str = " -> ") -> str:
        return arrow.join(self.path_names)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "destination": self.destination,
            "sourceName": self.source_name,
            "destinationName": self.destination_name,
            "path": self.path,
            "pathNames": self.path_names,
            "steps": [step.to_dict() for step in self.steps],
            "totalCost": self.total_cost,
            "totalDistance": round(self.total_distance, 1),
            "baseTime": self.base_time,
            "totalDelay": self.total_delay,
            "roadIds": self.road_ids,
            "worstTraffic": self.worst_traffic,
            "nodesExplored": self.nodes_explored,
            "nodesExpanded": self.nodes_expanded,
            "pops": self.pops,
        }


@dataclass
class NavigationResult:
    """The full outcome of a routing or rerouting request."""

    success: bool
    decision: RerouteDecision
    headline: str
    reason: str
    route: Route | None = None
    previous_route: Route | None = None
    previous_cost_now: int | None = None      # old route re-priced under new traffic
    saving: int | None = None
    search: UCSResult | None = None
    validation: ValidationResult | None = None
    traffic_update: TrafficUpdate | None = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "decision": self.decision.value,
            "headline": self.headline,
            "reason": self.reason,
            "route": self.route.to_dict() if self.route else None,
            "previousRoute": self.previous_route.to_dict() if self.previous_route else None,
            "previousCostNow": self.previous_cost_now,
            "saving": self.saving,
            "search": self.search.to_dict() if self.search else None,
            "validation": self.validation.to_dict() if self.validation else None,
            "trafficUpdate": self.traffic_update.to_dict() if self.traffic_update else None,
        }


#: Ordering used to report the worst congestion encountered along a route.
_TRAFFIC_SEVERITY = {
    TrafficLevel.LOW: 0,
    TrafficLevel.MEDIUM: 1,
    TrafficLevel.HIGH: 2,
    TrafficLevel.BLOCKED: 3,
}


class NavigationSession:
    """
    Holds the route currently being followed and keeps it optimal as simulated
    traffic changes.

    This class is the top of the system: it wires Modules 1 to 5 together and is
    the only object the interface layer needs to talk to.
    """

    def __init__(self, network: RoadNetwork, traffic: TrafficData, graph: WeightedGraph):
        self.network = network
        self.traffic = traffic
        self.graph = graph
        self.input_processing = InputProcessing(network)

        self.active_route: Route | None = None
        self.last_search: UCSResult | None = None
        self.history: list[NavigationResult] = []

    # -- finding a route ----------------------------------------------------

    def find_route(self, source_text: str, destination_text: str) -> NavigationResult:
        """
        The main flow: validate the input, run UCS on the current weighted
        graph, and present the result.
        """
        validation = self.input_processing.validate(source_text, destination_text)
        if not validation.valid:
            result = NavigationResult(
                success=False,
                decision=RerouteDecision.NO_ROUTE,
                headline="Invalid request",
                reason=validation.message,
                validation=validation,
            )
            self.history.append(result)
            return result

        request = validation.request
        search = uniform_cost_search(self.graph, request.source, request.destination)
        self.last_search = search

        if not search.found:
            # Module 1's reachability check should have caught this already;
            # reaching here means the search itself found no path, and the user
            # is told the same thing either way.
            result = NavigationResult(
                success=False,
                decision=RerouteDecision.NO_ROUTE,
                headline="No route available",
                reason=search.failure_reason,
                search=search,
                validation=validation,
            )
            self.active_route = None
            self.history.append(result)
            return result

        route = self._build_route(search)
        self.active_route = route

        result = NavigationResult(
            success=True,
            decision=RerouteDecision.INITIAL_ROUTE,
            headline="Optimal route found",
            reason=(
                f"Uniform Cost Search expanded {search.explored_count} locations and "
                f"returned the route with the lowest cumulative cost "
                f"({route.total_cost} min)."
            ),
            route=route,
            search=search,
            validation=validation,
        )
        self.history.append(result)
        return result

    # -- reacting to traffic ------------------------------------------------

    def update_traffic(
        self,
        road_id: str,
        traffic: TrafficLevel | str | None = None,
        road_status: str | None = None,
    ) -> NavigationResult:
        """
        Apply a traffic change and decide what it means for the active route.

            traffic change -> edge cost change -> graph update -> UCS again
            -> navigation update

        The graph updates itself: it subscribed to TrafficData when it was
        built, so by the time `apply_update` returns, the affected edges have
        already been re-costed.
        """
        update = self.traffic.apply_update(road_id, traffic=traffic, road_status=road_status)

        if self.active_route is None:
            result = NavigationResult(
                success=True,
                decision=RerouteDecision.UNCHANGED,
                headline="Traffic condition changed",
                reason=f"{update.description} No route is currently being followed.",
                traffic_update=update,
            )
            self.history.append(result)
            return result

        result = self._recalculate(update)
        self.history.append(result)
        return result

    def simulate_random_change(self, rng=None, *, allow_blocking: bool = False) -> NavigationResult:
        """One step of the optional auto-simulation, followed by rerouting."""
        update = self.traffic.simulate_random_change(rng, allow_blocking=allow_blocking)
        if self.active_route is None:
            result = NavigationResult(
                success=True,
                decision=RerouteDecision.UNCHANGED,
                headline="Traffic condition changed",
                reason=f"{update.description} No route is currently being followed.",
                traffic_update=update,
            )
        else:
            result = self._recalculate(update)
        self.history.append(result)
        return result

    def reset_traffic(self) -> NavigationResult | None:
        """Restore the network to its starting conditions and re-route."""
        self.traffic.reset()
        if self.active_route is None:
            return None
        return self._recalculate(None)

    # -- the rerouting decision ---------------------------------------------

    def _recalculate(self, update: TrafficUpdate | None) -> NavigationResult:
        previous = self.active_route
        assert previous is not None

        # Step 1: re-price the route being followed under the NEW conditions.
        #         `None` means one of its roads is no longer traversable.
        previous_cost_now = self.graph.path_cost(previous.path)

        # Step 2: run UCS again on the updated graph.
        search = uniform_cost_search(self.graph, previous.source, previous.destination)
        self.last_search = search

        if not search.found:
            self.active_route = None
            return NavigationResult(
                success=False,
                decision=RerouteDecision.NO_ROUTE,
                headline="No route available",
                reason=(
                    f"{update.description + ' ' if update else ''}"
                    f"There is no longer any open route from {previous.source_name} to "
                    f"{previous.destination_name}."
                ),
                previous_route=previous,
                search=search,
                traffic_update=update,
            )

        new_route = self._build_route(search)
        self.active_route = new_route

        # Step 3: compare like with like.
        return self._decide(previous, previous_cost_now, new_route, search, update)

    def _decide(
        self,
        previous: Route,
        previous_cost_now: int | None,
        new_route: Route,
        search: UCSResult,
        update: TrafficUpdate | None,
    ) -> NavigationResult:
        prefix = f"{update.description} " if update else ""

        # (a) The route being followed is no longer passable.
        if previous_cost_now is None:
            blocked = [
                road_id for road_id in previous.road_ids if self.traffic.is_blocked(road_id)
            ]
            return NavigationResult(
                success=True,
                decision=RerouteDecision.ROUTE_BLOCKED,
                headline="Route Updated",
                reason=(
                    f"{prefix}A road on your route ({', '.join(blocked) or 'unknown'}) is "
                    f"blocked, so the previous route is no longer usable. Uniform Cost "
                    f"Search has been run again on the updated graph and now returns "
                    f"{new_route.named_string()} at {new_route.total_cost} min."
                ),
                route=new_route,
                previous_route=previous,
                previous_cost_now=None,
                search=search,
                traffic_update=update,
            )

        # (b) The search returns the same path: keep it, but report its new cost,
        #     because congestion may have made the same route slower.
        if new_route.path == previous.path:
            if previous_cost_now == previous.total_cost:
                reason = (
                    f"{prefix}Your route is unaffected and remains optimal at "
                    f"{new_route.total_cost} min."
                )
            else:
                direction = "longer" if previous_cost_now > previous.total_cost else "shorter"
                reason = (
                    f"{prefix}Your route is still the cheapest available, but it is now "
                    f"{direction}: {previous.total_cost} -> {new_route.total_cost} min. "
                    f"No alternative route improves on it."
                )
            return NavigationResult(
                success=True,
                decision=RerouteDecision.UNCHANGED,
                headline="Route unchanged",
                reason=reason,
                route=new_route,
                previous_route=previous,
                previous_cost_now=previous_cost_now,
                saving=0,
                search=search,
                traffic_update=update,
            )

        # (c) A different, strictly cheaper route now exists. Two quite different
        #     things can cause that, and the user should be told which: either
        #     the route being followed got worse, or another route got better.
        saving = previous_cost_now - new_route.total_cost
        if previous_cost_now > previous.total_cost:
            cause = (
                f"Heavy traffic detected on the previous route, which has risen from "
                f"{previous.total_cost} to {previous_cost_now} min."
            )
        else:
            cause = (
                f"Traffic has eased elsewhere in the network. The previous route still "
                f"costs {previous_cost_now} min, but a better one is now open."
            )
        return NavigationResult(
            success=True,
            decision=RerouteDecision.CHEAPER_ROUTE_FOUND,
            headline="Route Updated",
            reason=(
                f"{prefix}{cause} Uniform Cost Search has found a cheaper route at "
                f"{new_route.total_cost} min, saving {saving} min."
            ),
            route=new_route,
            previous_route=previous,
            previous_cost_now=previous_cost_now,
            saving=saving,
            search=search,
            traffic_update=update,
        )

    # -- presentation -------------------------------------------------------

    def _build_route(self, search: UCSResult) -> Route:
        """Turn a raw search result into something worth showing a user."""
        steps: list[RouteStep] = []
        running = 0
        total_distance = 0.0
        base_time = 0
        total_delay = 0
        worst = TrafficLevel.LOW

        for edge in search.edges:
            road = self.network.get_road(edge.road_id)
            running += edge.cost
            total_distance += road.distance
            base_time += road.base_travel_time
            total_delay += road.traffic_delay
            if _TRAFFIC_SEVERITY[road.traffic] > _TRAFFIC_SEVERITY[worst]:
                worst = road.traffic

            steps.append(
                RouteStep(
                    from_node=edge.from_node,
                    to_node=edge.to_node,
                    from_name=self.network.get_node(edge.from_node).name,
                    to_name=self.network.get_node(edge.to_node).name,
                    road_id=road.id,
                    base_travel_time=road.base_travel_time,
                    traffic=road.traffic.value,
                    traffic_delay=road.traffic_delay,
                    cost=edge.cost,
                    cumulative_cost=running,
                )
            )

        return Route(
            source=search.source,
            destination=search.destination,
            source_name=self.network.get_node(search.source).name,
            destination_name=self.network.get_node(search.destination).name,
            path=list(search.path),
            path_names=[self.network.get_node(node_id).name for node_id in search.path],
            steps=steps,
            total_cost=search.total_cost,
            total_distance=total_distance,
            base_time=base_time,
            total_delay=total_delay,
            road_ids=[edge.road_id for edge in search.edges],
            worst_traffic=worst.value,
            nodes_explored=search.explored_count,
            nodes_expanded=list(search.nodes_expanded),
            pops=search.pops,
        )
