"""A separate API namespace and state; no changes to fictional demo endpoints."""

from threading import RLock
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..models import TrafficLevel
from .service import RealMapService
from .providers import providers, trip_bounds, ProviderError

router = APIRouter(prefix='/api/real-map', tags=['Real Map Navigation'])
_service = None
_lock = RLock()


def service():
    global _service
    if _service is None:
        try:
            _service = RealMapService()
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise HTTPException(503, 'The local road dataset could not be loaded. Restore backend/data/besant_nagar.osm.json and retry.') from error
    return _service


class Coordinate(BaseModel):
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)


class ResolveBody(Coordinate):
    role: Literal['source', 'destination'] = 'source'


class RouteBody(BaseModel):
    source: Annotated[str, Field(max_length=250)] | Coordinate | None = None
    destination: Annotated[str, Field(max_length=250)] | Coordinate | None = None


class SearchBody(BaseModel):
    query: str = Field(min_length=2, max_length=200)
    bias: Coordinate | None = None


class TripBody(BaseModel):
    source: Coordinate
    destination: Coordinate


class TrafficBody(BaseModel):
    roadId: str = Field(min_length=1, max_length=100)
    traffic: TrafficLevel


class SimulationBody(BaseModel):
    allowBlocking: bool = False


@router.get('/network')
def network():
    with _lock:
        return service().state()


@router.post('/route')
def route(body: RouteBody):
    with _lock:
        return service().find_route(**body.model_dump())


@router.post('/resolve')
def resolve(body: ResolveBody):
    with _lock:
        try:
            return service().resolve_coordinate(body.latitude, body.longitude, body.role)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error


@router.post('/search')
def search(body: SearchBody):
    if len(body.query.strip()) < 2:
        raise HTTPException(422, 'Enter at least two characters to search for a place.')
    try:
        return {'places': providers.search(body.query.strip(), body.bias.model_dump() if body.bias else None)}
    except ProviderError as error:
        raise HTTPException(503, str(error)) from error


@router.post('/nearby')
def nearby(body: Coordinate):
    try:
        return {'places': providers.nearby(body.model_dump())}
    except ProviderError as error:
        raise HTTPException(503, str(error)) from error


@router.post('/trip')
def trip(body: TripBody):
    """Load a trip-specific graph atomically; existing state survives provider errors."""
    global _service
    source, destination = body.source.model_dump(), body.destination.model_dump()
    try:
        bbox = trip_bounds(source, destination)
        data = providers.roads(bbox)
        candidate = RealMapService(data, bbox=bbox, dynamic=True,
                                   anchor_points=([source['latitude'], source['longitude']], [destination['latitude'], destination['longitude']]))
        response = candidate.find_route(source, destination)
        # A failed attempt never leaves an old route in the returned graph.
        with _lock:
            _service = candidate
        return response
    except ProviderError as error:
        raise HTTPException(503, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@router.post('/traffic')
def traffic(body: TrafficBody):
    with _lock:
        try:
            return service().update_traffic(body.roadId, body.traffic)
        except KeyError as error:
            raise HTTPException(404, 'This road is not in the supported map area. Choose a road from the list.') from error


@router.post('/simulate')
def simulate(body: SimulationBody):
    with _lock:
        return service().simulate(body.allowBlocking)


@router.post('/reset')
def reset():
    with _lock:
        return service().reset()
