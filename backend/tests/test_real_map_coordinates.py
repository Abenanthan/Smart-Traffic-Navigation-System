"""Coordinate selection must reuse UCS and respect the available directed graph."""
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from test_real_map import small_map, id_at, POINTS, snapshot, way
from app.real_map.service import RealMapService
from app.real_map.providers import ProviderError


def coordinate(point):
    return dict(zip(('latitude', 'longitude'), POINTS[point]))


def test_coordinates_use_existing_ucs(small_map, monkeypatch):
    import app.navigation as navigation
    spy = Mock(wraps=navigation.uniform_cost_search)
    monkeypatch.setattr(navigation, 'uniform_cost_search', spy)
    response = small_map.find_route(coordinate(1), coordinate(4))
    assert response['result']['success']
    assert response['result']['route']['totalCost'] == 2
    assert spy.call_count == 1
    assert response['snappedLocations']['source']['nodeId'] == id_at(small_map, 1)


@pytest.mark.parametrize('lat,lon', [(51.5, -.12), (float('nan'), 80.265), (13.001, float('inf')), (True, 80.265), (None, 80.265)])
def test_invalid_or_outside_coordinates(small_map, lat, lon):
    with pytest.raises(ValueError):
        small_map.resolve_coordinate(lat, lon)


def test_outside_route_clears_previous_route(small_map):
    small_map.find_route(coordinate(1), coordinate(4))
    response = small_map.find_route({'latitude': 51.5, 'longitude': -.12}, coordinate(4))
    assert not response['result']['success']
    assert response['network']['activeRoute'] is None
    assert response['network']['requestedPair'] is None


def test_no_nearby_road(small_map):
    with pytest.raises(ValueError, match='80 metres'):
        small_map.resolve_coordinate(13.009, 80.277)


def test_direction_and_blocking_affect_snap():
    service = RealMapService(snapshot(way(1, [1, 4], oneway='yes')))
    assert service.resolve_coordinate(*POINTS[1], 'source')['nodeId'] == id_at(service, 1)
    assert service.resolve_coordinate(*POINTS[4], 'destination')['nodeId'] == id_at(service, 4)
    with pytest.raises(ValueError):
        service.resolve_coordinate(*POINTS[4], 'source')
    service.update_traffic(service.state()['roads'][0]['roadId'], 'blocked')
    with pytest.raises(ValueError):
        service.resolve_coordinate(*POINTS[1], 'source')


def test_api_coordinate_contract(small_map, monkeypatch):
    from app.api import app
    import app.real_map.api as real_api
    monkeypatch.setattr(real_api, '_service', small_map)
    client = TestClient(app)
    assert client.post('/api/real-map/resolve', json={**coordinate(1), 'role': 'source'}).status_code == 200
    response = client.post('/api/real-map/route', json={'source': coordinate(1), 'destination': id_at(small_map, 4)})
    assert response.status_code == 200
    assert response.json()['result']['success']
    for body in ({'latitude': 100, 'longitude': 80}, {**coordinate(1), 'role': 'invalid'}, {'latitude': 51.5, 'longitude': -.12}):
        assert client.post('/api/real-map/resolve', json=body).status_code == 422


def test_trip_reuses_loaded_graph_when_all_road_servers_fail(monkeypatch):
    from app.api import app
    import app.real_map.api as real_api
    loaded = RealMapService(
        snapshot(way(1, [1, 2]), way(2, [2, 4])),
        bbox=(12.99, 80.25, 13.01, 80.28), dynamic=True, transport_mode='car',
    )
    monkeypatch.setattr(real_api, '_service', loaded)
    monkeypatch.setattr(real_api.providers, 'roads', Mock(side_effect=ProviderError('all servers timed out')))
    response = TestClient(app).post('/api/real-map/trip', json={
        'source': coordinate(1), 'destination': coordinate(4), 'transportMode': 'car',
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload['result']['success']
    assert payload['roadDataFallback']['used'] is True
    assert real_api._service is loaded


def test_trip_does_not_reuse_graph_for_another_transport_mode(monkeypatch):
    from app.api import app
    import app.real_map.api as real_api
    loaded = RealMapService(
        snapshot(way(1, [1, 2]), way(2, [2, 4])),
        bbox=(12.99, 80.25, 13.01, 80.28), dynamic=True, transport_mode='car',
    )
    monkeypatch.setattr(real_api, '_service', loaded)
    monkeypatch.setattr(real_api.providers, 'roads', Mock(side_effect=ProviderError('all servers timed out')))
    response = TestClient(app).post('/api/real-map/trip', json={
        'source': coordinate(1), 'destination': coordinate(4), 'transportMode': 'walk',
    })
    assert response.status_code == 503
