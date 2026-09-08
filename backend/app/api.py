"""
HTTP interface for the Smart Traffic Navigation System.

This layer contains no logic of its own. Every endpoint validates its arguments,
calls one method on the navigation session, and serialises the answer. All six
modules work exactly the same way without it -- see demo_cli.py -- and this file
exists only so that a browser can drive them.

State is held in a single in-memory session. That is appropriate for a
single-user demonstration and is the reason the system does not need a database;
it also means two browsers pointed at the same server would share one route.
This is a deliberate simplification, recorded under Limitations.

Run with:
    uvicorn app.api:app --reload --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .models import TrafficLevel
from .navigation import NavigationSession
from .weighted_graph import build_graph

app = FastAPI(
    title="Smart Traffic Navigation System",
    description=(
        "An academic demonstration of Uniform Cost Search over a weighted road "
        "graph with simulated traffic. Traffic data is SIMULATED and is not "
        "obtained from any live traffic service."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# The single in-memory session
# ---------------------------------------------------------------------------

_network, _traffic, _graph = build_graph()
session = NavigationSession(_network, _traffic, _graph)


def network_state() -> dict:
    """Everything the interface needs to draw the network in its current state."""
    return {
        "nodes": [
            {"id": node.id, "name": node.name, "x": node.x, "y": node.y}
            for node in session.network.nodes
        ],
        "roads": session.graph.cost_table(),
        "trafficCounts": session.traffic.counts_by_level(),
        "activeRoute": session.active_route.to_dict() if session.active_route else None,
        "trafficDelayModel": {"low": 0, "medium": 5, "high": 12, "blocked": None},
        "simulated": True,
    }


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class RouteBody(BaseModel):
    source: str | None = Field(default=None, description="Source location id or name")
    destination: str | None = Field(default=None, description="Destination id or name")


class TrafficBody(BaseModel):
    roadId: str
    traffic: str


class SimulateBody(BaseModel):
    allowBlocking: bool = False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/network")
def get_network() -> dict:
    """The road network, current road costs, and the active route if any."""
    return network_state()


@app.get("/api/locations")
def get_locations() -> dict:
    """The selectable locations, for the source and destination pickers."""
    return {"locations": session.input_processing.available_locations()}


@app.post("/api/route")
def find_route(body: RouteBody) -> dict:
    """
    MODULE 1 -> MODULE 5: validate the request, then run Uniform Cost Search.

    An invalid request is not an HTTP error -- it is a normal answer carrying a
    message for the user, which is what the interface displays.
    """
    result = session.find_route(body.source, body.destination)
    return {"result": result.to_dict(), "network": network_state()}


@app.post("/api/traffic")
def update_traffic(body: TrafficBody) -> dict:
    """
    MODULE 3 -> MODULE 4 -> MODULE 5 -> MODULE 6: apply a traffic change,
    re-cost the affected edges, run the search again, and decide whether the
    route being followed should change.
    """
    try:
        level = TrafficLevel(body.traffic)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown traffic level {body.traffic!r}. "
                   f"Expected one of: low, medium, high, blocked.",
        )

    try:
        result = session.update_traffic(body.roadId, level)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error))

    return {"result": result.to_dict(), "network": network_state()}


@app.post("/api/simulate")
def simulate(body: SimulateBody) -> dict:
    """
    One step of the optional traffic simulation: change a random road, then
    reroute. This drives the "auto-simulate" switch in the interface.
    """
    result = session.simulate_random_change(allow_blocking=body.allowBlocking)
    return {"result": result.to_dict(), "network": network_state()}


@app.post("/api/reset")
def reset() -> dict:
    """Restore the traffic conditions loaded from the data file."""
    result = session.reset_traffic()
    return {
        "result": result.to_dict() if result else None,
        "network": network_state(),
    }


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "locations": len(session.network.nodes),
        "roads": len(session.network.roads),
        "simulatedTraffic": True,
    }
