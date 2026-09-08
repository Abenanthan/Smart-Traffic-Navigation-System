"""
Shared data model for the Smart Traffic Navigation System.

This module defines the vocabulary every other module speaks: what a location is,
what a road is, how congested a road can be, and -- most importantly -- the single
cost function on which the entire search rests.

    edge_cost = base_travel_time + traffic_delay

Nothing in this file performs search or holds mutable state. It is deliberately
dependency-free so that the cost model can be read and checked in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# Traffic vocabulary
# ---------------------------------------------------------------------------

class TrafficLevel(str, Enum):
    """
    Simulated congestion level on a road.

    NOTE: these values are SIMULATED. The system does not consume real-time
    traffic data from any commercial mapping service. See TrafficData (Module 3)
    for the interface a real feed would need to implement.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKED = "blocked"


class RoadStatus(str, Enum):
    """
    Physical availability of a road, independent of congestion.

    Congestion (TrafficLevel) and closure (RoadStatus) are modelled separately
    on purpose: a road can be jammed but usable, or empty but physically shut
    (flooding, construction, an accident). Either kind of "blocked" removes the
    road from the search space -- see `Road.is_traversable`.
    """

    OPEN = "open"
    BLOCKED = "blocked"


#: The traffic-delay model, in minutes added to a road's base travel time.
#: TrafficLevel.BLOCKED is intentionally absent: a blocked road has no finite
#: cost, it is simply not part of the state space.
TRAFFIC_DELAY: dict[TrafficLevel, int] = {
    TrafficLevel.LOW: 0,
    TrafficLevel.MEDIUM: 5,
    TrafficLevel.HIGH: 12,
}


def traffic_delay(level: TrafficLevel) -> int:
    """
    Convert a traffic level into a delay in minutes.

    Raises ValueError for BLOCKED, because a blocked road must be excluded from
    the graph rather than assigned a large cost. Assigning "infinity" would let
    a search still traverse it if no alternative existed, which is wrong: the
    road is unavailable, not merely expensive.
    """
    if level is TrafficLevel.BLOCKED:
        raise ValueError(
            "A blocked road has no traffic delay; it must be excluded from the "
            "weighted graph entirely. Check `is_traversable` before costing an edge."
        )
    return TRAFFIC_DELAY[level]


# ---------------------------------------------------------------------------
# Network elements
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Node:
    """
    A location or junction in the road network -- one STATE in the search space.

    `x` and `y` are screen coordinates used only for drawing the network; they
    play no part in the cost function or the search. (UCS uses no geometry and
    no heuristic -- that is precisely what distinguishes it from A*.)
    """

    id: str
    name: str
    x: float = 0.0
    y: float = 0.0

    def __str__(self) -> str:
        return f"{self.id} ({self.name})"


@dataclass
class Road:
    """
    A road between two locations -- one ACTION in the search space.

    Roads are bidirectional: a single Road produces two directed adjacency
    entries of equal cost. One-way streets are listed as future work.

    Mutable by design: `traffic` and `road_status` are exactly what the
    simulation changes at run time, which is what makes the environment dynamic.
    """

    id: str
    from_node: str
    to_node: str
    distance: float           # kilometres (reported to the user; not used in cost)
    base_travel_time: int     # minutes, free-flow
    traffic: TrafficLevel = TrafficLevel.LOW
    road_status: RoadStatus = RoadStatus.OPEN

    # -- the cost model -----------------------------------------------------

    @property
    def is_traversable(self) -> bool:
        """A road may be used only if it is open AND not traffic-blocked."""
        return (
            self.road_status is RoadStatus.OPEN
            and self.traffic is not TrafficLevel.BLOCKED
        )

    @property
    def traffic_delay(self) -> int:
        """Minutes of delay contributed by the current congestion level."""
        return traffic_delay(self.traffic)

    @property
    def cost(self) -> int:
        """
        The edge weight used by Uniform Cost Search:

            cost = base_travel_time + traffic_delay

        Only defined for traversable roads.
        """
        if not self.is_traversable:
            raise ValueError(
                f"Road {self.id} ({self.from_node}-{self.to_node}) is not traversable "
                f"(traffic={self.traffic.value}, status={self.road_status.value}); "
                f"it has no cost and must be excluded from the graph."
            )
        return self.base_travel_time + self.traffic_delay

    # -- convenience --------------------------------------------------------

    def connects(self, a: str, b: str) -> bool:
        """True if this road joins `a` and `b`, in either direction."""
        return (self.from_node, self.to_node) in ((a, b), (b, a))

    def other_end(self, node_id: str) -> str:
        """Given one endpoint, return the other."""
        if node_id == self.from_node:
            return self.to_node
        if node_id == self.to_node:
            return self.from_node
        raise ValueError(f"Node {node_id!r} is not an endpoint of road {self.id}")

    def __str__(self) -> str:
        if self.is_traversable:
            return (
                f"{self.id}: {self.from_node}-{self.to_node} "
                f"[{self.base_travel_time} + {self.traffic_delay} = {self.cost} min, "
                f"{self.traffic.value}]"
            )
        return (
            f"{self.id}: {self.from_node}-{self.to_node} "
            f"[UNAVAILABLE: traffic={self.traffic.value}, status={self.road_status.value}]"
        )


@dataclass(frozen=True)
class Edge:
    """
    A directed, costed adjacency entry produced by the WeightedGraph (Module 4).

    Where `Road` is the raw network datum, `Edge` is what the search actually
    walks: one direction, one number. Edges are rebuilt whenever traffic changes,
    so an Edge is always priced under current conditions.
    """

    road_id: str
    from_node: str
    to_node: str
    cost: int

    def __str__(self) -> str:
        return f"{self.from_node} -> {self.to_node} (cost {self.cost}, via {self.road_id})"
