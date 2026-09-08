"""
MODULE 1 -- INPUT PROCESSING
============================

Input   : a source location and a destination location
Process : accept both from the user; check that neither is empty; check that
          each exists in the road network; check that they are not the same;
          check whether a route can potentially exist; report a clear error if
          any check fails, or build a route request if all pass
Output  : a validated source and destination

This module is the gate in front of the search. Everything downstream -- the
graph, the search engine, the navigation display -- is allowed to assume that
the source and destination are real, distinct locations. That assumption is
established here and nowhere else.

The final check is worth singling out. Before UCS is invoked at all, a
breadth-first reachability test asks whether *any* route could exist. This
separates two outcomes that look identical to a user but are entirely different
in nature: "the destination cannot be reached" (a property of the network) and
"the search failed" (a property of the algorithm). Distinguishing them is what
lets the system report "No route available" with confidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .road_network import RoadNetwork


class ValidationError(str, Enum):
    """The reasons a route request can be rejected, as machine-readable codes."""

    EMPTY_SOURCE = "empty_source"
    EMPTY_DESTINATION = "empty_destination"
    UNKNOWN_SOURCE = "unknown_source"
    UNKNOWN_DESTINATION = "unknown_destination"
    SAME_LOCATION = "same_location"
    NO_POSSIBLE_ROUTE = "no_possible_route"


@dataclass
class RouteRequest:
    """A validated request, safe to hand to the routing system."""

    source: str
    destination: str
    source_name: str
    destination_name: str

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "destination": self.destination,
            "sourceName": self.source_name,
            "destinationName": self.destination_name,
        }


@dataclass
class ValidationResult:
    """The outcome of validating one route request."""

    valid: bool
    request: RouteRequest | None = None
    error: ValidationError | None = None
    message: str = ""
    field: str = ""            # which input the user should correct

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "request": self.request.to_dict() if self.request else None,
            "error": self.error.value if self.error else None,
            "message": self.message,
            "field": self.field,
        }


class InputProcessing:
    """Validates the user's source and destination against the road network."""

    def __init__(self, network: RoadNetwork):
        self.network = network

    def available_locations(self) -> list[dict]:
        """Every selectable location, for populating the interface's dropdowns."""
        return [{"id": node.id, "name": node.name} for node in self.network.nodes]

    def validate(self, source_text: str | None, destination_text: str | None) -> ValidationResult:
        """
        Run every check in order and stop at the first failure, so the user is
        told about one problem at a time rather than a list of them.
        """
        # 1. Neither field may be empty.
        if source_text is None or not str(source_text).strip():
            return ValidationResult(
                valid=False,
                error=ValidationError.EMPTY_SOURCE,
                field="source",
                message="Please select a source location.",
            )
        if destination_text is None or not str(destination_text).strip():
            return ValidationResult(
                valid=False,
                error=ValidationError.EMPTY_DESTINATION,
                field="destination",
                message="Please select a destination location.",
            )

        # 2. Both must exist in the road network. `resolve` accepts either the
        #    node id ("K") or the full location name ("Railway Station").
        source = self.network.resolve(str(source_text))
        if source is None:
            return ValidationResult(
                valid=False,
                error=ValidationError.UNKNOWN_SOURCE,
                field="source",
                message=(
                    f"'{str(source_text).strip()}' is not a location in this road "
                    f"network. Please choose a source from the list."
                ),
            )

        destination = self.network.resolve(str(destination_text))
        if destination is None:
            return ValidationResult(
                valid=False,
                error=ValidationError.UNKNOWN_DESTINATION,
                field="destination",
                message=(
                    f"'{str(destination_text).strip()}' is not a location in this road "
                    f"network. Please choose a destination from the list."
                ),
            )

        # 3. Source and destination must differ.
        if source == destination:
            name = self.network.get_node(source).name
            return ValidationResult(
                valid=False,
                error=ValidationError.SAME_LOCATION,
                field="destination",
                message=(
                    f"Source and destination are both {name}. Please choose two "
                    f"different locations."
                ),
            )

        # 4. A route must be structurally possible. This ignores cost entirely --
        #    it asks only whether the destination is reachable through roads that
        #    are currently open, before any search is attempted.
        if not self.network.is_connected(source, destination, traversable_only=True):
            source_name = self.network.get_node(source).name
            destination_name = self.network.get_node(destination).name
            if self.network.is_connected(source, destination, traversable_only=False):
                reason = (
                    " Every road that could connect them is currently blocked."
                )
            else:
                reason = (
                    " These locations are in separate parts of the network and are "
                    "not joined by any road."
                )
            return ValidationResult(
                valid=False,
                error=ValidationError.NO_POSSIBLE_ROUTE,
                field="destination",
                message=f"No route available from {source_name} to {destination_name}.{reason}",
            )

        # 5. All checks passed: build the request and forward it to the router.
        return ValidationResult(
            valid=True,
            request=RouteRequest(
                source=source,
                destination=destination,
                source_name=self.network.get_node(source).name,
                destination_name=self.network.get_node(destination).name,
            ),
            message=(
                f"Route request accepted: {self.network.get_node(source).name} to "
                f"{self.network.get_node(destination).name}."
            ),
        )
