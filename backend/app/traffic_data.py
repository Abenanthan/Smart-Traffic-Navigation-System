"""
MODULE 3 -- TRAFFIC DATA
========================

Input   : the traffic condition of each road, road status, traffic updates
Process : determine the traffic level of each road, convert that level into a
          traffic delay, detect blocked roads, apply updates requested by the
          user, and notify the graph system when a road's condition changes
Output  : the current traffic cost and status of every road

SIMULATED DATA
--------------
The traffic levels in this system are SIMULATED. They are set from the network
data file and changed by the user (or by the optional random simulator below).
This project does not receive live traffic from Google Maps or any other
commercial service, and does not claim to.

The separation matters for more than honesty. This module is the *only* place
that decides how congested a road is. Every other module -- the weighted graph,
the search engine, the navigation display -- asks this module rather than
deciding for itself. A real traffic feed would therefore be introduced by
replacing the source of `apply_update` calls, with no change to the search at
all. That is what "designed for future integration" means here concretely, and
it is listed under Future Enhancements rather than claimed as built.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

from .models import RoadStatus, TrafficLevel, traffic_delay
from .road_network import RoadNetwork


@dataclass
class TrafficCondition:
    """The current traffic picture for one road."""

    road_id: str
    from_node: str
    to_node: str
    traffic: TrafficLevel
    road_status: RoadStatus
    base_travel_time: int
    delay: int | None          # None when the road is unavailable
    cost: int | None           # None when the road is unavailable
    traversable: bool

    def to_dict(self) -> dict:
        return {
            "roadId": self.road_id,
            "from": self.from_node,
            "to": self.to_node,
            "traffic": self.traffic.value,
            "roadStatus": self.road_status.value,
            "baseTravelTime": self.base_travel_time,
            "delay": self.delay,
            "cost": self.cost,
            "traversable": self.traversable,
        }


@dataclass
class TrafficUpdate:
    """The record of one change to traffic conditions."""

    road_id: str
    previous_traffic: TrafficLevel
    new_traffic: TrafficLevel
    previous_status: RoadStatus
    new_status: RoadStatus
    previous_cost: int | None
    new_cost: int | None
    changed: bool

    @property
    def description(self) -> str:
        if not self.changed:
            return f"Road {self.road_id} was already {self.new_traffic.value}; nothing changed."
        if self.new_status is RoadStatus.BLOCKED or self.new_traffic is TrafficLevel.BLOCKED:
            return f"Road {self.road_id} is now blocked and has been removed from the graph."
        if self.previous_cost is None:
            return (
                f"Road {self.road_id} has reopened at {self.new_traffic.value} traffic "
                f"(cost {self.new_cost} min)."
            )
        direction = "increased" if self.new_cost > self.previous_cost else "decreased"
        return (
            f"Road {self.road_id}: traffic {self.previous_traffic.value} -> "
            f"{self.new_traffic.value}, cost {direction} "
            f"{self.previous_cost} -> {self.new_cost} min."
        )

    def to_dict(self) -> dict:
        return {
            "roadId": self.road_id,
            "previousTraffic": self.previous_traffic.value,
            "newTraffic": self.new_traffic.value,
            "previousStatus": self.previous_status.value,
            "newStatus": self.new_status.value,
            "previousCost": self.previous_cost,
            "newCost": self.new_cost,
            "changed": self.changed,
            "description": self.description,
        }


class TrafficData:
    """
    The authoritative source of traffic conditions for the road network.

    This class owns the `traffic` and `road_status` fields of every road. Other
    modules read them but must route all *changes* through `apply_update`, so
    that dependent structures (the weighted graph) are always notified.
    """

    def __init__(self, network: RoadNetwork):
        self.network = network
        #: the conditions loaded from the data file, so the demo can be reset
        self._initial: dict[str, tuple[TrafficLevel, RoadStatus]] = {
            road.id: (road.traffic, road.road_status) for road in network.roads
        }
        self._observers: list[Callable[[TrafficUpdate], None]] = []
        self.history: list[TrafficUpdate] = []

    # -- notification -------------------------------------------------------

    def subscribe(self, observer: Callable[[TrafficUpdate], None]) -> None:
        """
        Register a callback to be told when a road's condition changes.

        The weighted graph subscribes here. This is the "notify the graph
        system" step of the module specification, and it is what makes the
        chain traffic change -> cost change -> graph update automatic rather
        than something a caller has to remember to do.
        """
        self._observers.append(observer)

    def _notify(self, update: TrafficUpdate) -> None:
        for observer in self._observers:
            observer(update)

    # -- reading current conditions ----------------------------------------

    def level_of(self, road_id: str) -> TrafficLevel:
        return self.network.get_road(road_id).traffic

    def delay_of(self, road_id: str) -> int | None:
        """Traffic delay in minutes, or None if the road is unavailable."""
        road = self.network.get_road(road_id)
        return traffic_delay(road.traffic) if road.is_traversable else None

    def cost_of(self, road_id: str) -> int | None:
        """Current edge cost in minutes, or None if the road is unavailable."""
        road = self.network.get_road(road_id)
        return road.cost if road.is_traversable else None

    def is_blocked(self, road_id: str) -> bool:
        return not self.network.get_road(road_id).is_traversable

    def blocked_roads(self) -> list[str]:
        return [road.id for road in self.network.roads if not road.is_traversable]

    def condition_of(self, road_id: str) -> TrafficCondition:
        road = self.network.get_road(road_id)
        traversable = road.is_traversable
        return TrafficCondition(
            road_id=road.id,
            from_node=road.from_node,
            to_node=road.to_node,
            traffic=road.traffic,
            road_status=road.road_status,
            base_travel_time=road.base_travel_time,
            delay=traffic_delay(road.traffic) if traversable else None,
            cost=road.cost if traversable else None,
            traversable=traversable,
        )

    def all_conditions(self) -> list[TrafficCondition]:
        return [self.condition_of(road.id) for road in self.network.roads]

    def counts_by_level(self) -> dict[str, int]:
        counts = {level.value: 0 for level in TrafficLevel}
        for road in self.network.roads:
            if road.road_status is RoadStatus.BLOCKED:
                counts[TrafficLevel.BLOCKED.value] += 1
            else:
                counts[road.traffic.value] += 1
        return counts

    # -- changing conditions ------------------------------------------------

    def apply_update(
        self,
        road_id: str,
        traffic: TrafficLevel | str | None = None,
        road_status: RoadStatus | str | None = None,
    ) -> TrafficUpdate:
        """
        Change the traffic level and/or physical status of one road.

        Passing `traffic="blocked"` also closes the road, because that is what a
        user selecting "Blocked" in the interface means. Setting any other
        traffic level on a closed road reopens it, so the interface's four
        traffic buttons behave the way a user expects without needing a separate
        open/close control.
        """
        if not self.network.has_road(road_id):
            raise KeyError(
                f"Unknown road: {road_id!r}. Traffic can only be set on a road "
                f"that exists in the network."
            )
        road = self.network.get_road(road_id)

        previous_traffic = road.traffic
        previous_status = road.road_status
        previous_cost = road.cost if road.is_traversable else None

        if traffic is not None:
            new_traffic = TrafficLevel(traffic)
            new_status = (
                RoadStatus.BLOCKED if new_traffic is TrafficLevel.BLOCKED else RoadStatus.OPEN
            )
        else:
            new_traffic = previous_traffic
            new_status = previous_status

        if road_status is not None:
            new_status = RoadStatus(road_status)

        road.traffic = new_traffic
        road.road_status = new_status
        new_cost = road.cost if road.is_traversable else None

        update = TrafficUpdate(
            road_id=road_id,
            previous_traffic=previous_traffic,
            new_traffic=new_traffic,
            previous_status=previous_status,
            new_status=new_status,
            previous_cost=previous_cost,
            new_cost=new_cost,
            changed=(previous_traffic != new_traffic or previous_status != new_status),
        )

        self.history.append(update)
        # Notify even when nothing changed, so subscribers stay consistent; the
        # navigation module checks `changed` before announcing a reroute.
        self._notify(update)
        return update

    def block_road(self, road_id: str) -> TrafficUpdate:
        return self.apply_update(road_id, road_status=RoadStatus.BLOCKED)

    def open_road(self, road_id: str, traffic: TrafficLevel = TrafficLevel.LOW) -> TrafficUpdate:
        return self.apply_update(road_id, traffic=traffic, road_status=RoadStatus.OPEN)

    def reset(self) -> list[TrafficUpdate]:
        """Restore every road to the conditions loaded from the data file."""
        updates = []
        for road_id, (level, status) in self._initial.items():
            updates.append(self.apply_update(road_id, traffic=level, road_status=status))
        self.history.clear()
        return updates

    # -- optional random simulation ----------------------------------------

    def simulate_random_change(
        self,
        rng: random.Random | None = None,
        *,
        allow_blocking: bool = False,
    ) -> TrafficUpdate:
        """
        Move one randomly chosen road to a different traffic level.

        This backs the optional "auto-simulate traffic" switch in the interface.
        It is a convenience for demonstrating rerouting live; it is not a traffic
        model and makes no attempt to be realistic. Blocking is off by default so
        that an unattended demo cannot strand the network.
        """
        rng = rng or random.Random()
        choices = [TrafficLevel.LOW, TrafficLevel.MEDIUM, TrafficLevel.HIGH]
        if allow_blocking:
            choices.append(TrafficLevel.BLOCKED)

        road = rng.choice(self.network.roads)
        alternatives = [level for level in choices if level != road.traffic]
        return self.apply_update(road.id, traffic=rng.choice(alternatives))

    # -- reporting ----------------------------------------------------------

    def summary(self) -> str:
        lines = [
            "Traffic conditions (SIMULATED -- not live data)",
            "",
            f"{'Road':<6}{'Link':<8}{'Base':>6}{'Traffic':>10}{'Delay':>7}{'Cost':>7}",
            "-" * 44,
        ]
        for condition in self.all_conditions():
            link = f"{condition.from_node}-{condition.to_node}"
            if condition.traversable:
                lines.append(
                    f"{condition.road_id:<6}{link:<8}{condition.base_travel_time:>6}"
                    f"{condition.traffic.value:>10}{condition.delay:>7}{condition.cost:>7}"
                )
            else:
                lines.append(
                    f"{condition.road_id:<6}{link:<8}{condition.base_travel_time:>6}"
                    f"{condition.traffic.value:>10}{'--':>7}{'BLOCKED':>7}"
                )
        counts = self.counts_by_level()
        lines += [
            "",
            "  ".join(f"{name}: {count}" for name, count in counts.items()),
        ]
        return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover - Phase 5 verification helper
    print(TrafficData(RoadNetwork.from_json_file()).summary())
