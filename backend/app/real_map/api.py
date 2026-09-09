"""A separate API namespace and state; no changes to fictional demo endpoints."""

from threading import RLock

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..models import TrafficLevel
from .service import RealMapService

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


class RouteBody(BaseModel):
    source: str | None = Field(None, max_length=250)
    destination: str | None = Field(None, max_length=250)


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
        return service().find_route(body.source, body.destination)


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
