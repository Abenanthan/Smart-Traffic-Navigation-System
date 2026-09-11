"""Dynamic graph routing contracts; all unit provider responses are test fixtures."""
import copy
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.real_map.service import RealMapService
from app.real_map.providers import MapProviders, ProviderError, trip_bounds
from test_real_map import snapshot, way, POINTS


@pytest.fixture
def dynamic_data():
    data = snapshot(way(1, [1, 2]), way(2, [2, 4]), way(3, [1, 3]), way(4, [3, 5]), way(5, [5, 4]))
    # Move the test graph far outside Besant Nagar, retaining its topology.
    for road in data['elements']:
        for point in road['geometry']:
            point['lat'] += 10
            point['lon'] -= 60
    return data


def point(index):
    return {'latitude': POINTS[index][0] + 10, 'longitude': POINTS[index][1] - 60}


def make_service(data):
    a, b = point(1), point(4)
    return RealMapService(data, bbox=trip_bounds(a, b), dynamic=True,
                          anchor_points=([a['latitude'], a['longitude']], [b['latitude'], b['longitude']]))


def test_new_region_uses_original_ucs_without_trace(dynamic_data, monkeypatch):
    import app.navigation as navigation
    spy = Mock(wraps=navigation.uniform_cost_search)
    monkeypatch.setattr(navigation, 'uniform_cost_search', spy)
    service = make_service(dynamic_data)
    response = service.find_route(point(1), point(4))
    assert response['result']['success']
    base = sum(service.session.network.get_road(r).distance * 2 for r in response['result']['route']['roadIds'])
    assert response['result']['route']['totalCost'] == pytest.approx(base)
    assert service.session.last_search.trace == []
    assert spy.call_args.kwargs == {'record_trace': False}
    first = response['result']['route']['roadIds'][0]
    reroute = service.update_traffic(first, 'high')['result']
    assert reroute['route']['totalCost'] <= reroute['previousCostNow']
    assert reroute['previousCostNow'] == pytest.approx(base + service.session.network.get_road(first).base_travel_time * 1.5)
    assert spy.call_count == 2
    assert service.data.metadata['dynamic']


def test_dynamic_block_and_reopen(dynamic_data):
    service = make_service(dynamic_data)
    route = service.find_route(point(1), point(4))['result']['route']
    first = route['roadIds'][0]
    rerouted = service.update_traffic(first, 'blocked')['result']['route']
    assert first not in rerouted['roadIds']
    for road in list(service.session.network.roads_at(route['source'])):
        service.update_traffic(road.id, 'blocked')
    assert service.session.active_route is None
    assert service.reset()['result']['route']['totalCost'] == pytest.approx(route['totalCost'])


def test_dynamic_snap_uses_selected_shape_vertex():
    data = snapshot(way(1, [1, 8, 2, 4]))
    start = {'latitude': POINTS[8][0], 'longitude': POINTS[8][1]}
    end = {'latitude': POINTS[4][0], 'longitude': POINTS[4][1]}
    service = RealMapService(data, bbox=trip_bounds(start, end), dynamic=True, anchor_points=(POINTS[8], POINTS[4]))
    result = service.find_route(start, end)
    assert result['result']['success']
    assert result['snappedLocations']['source']['distanceMetres'] == 0
    assert result['result']['route']['geometry'][0] == POINTS[8]


@pytest.mark.parametrize('a,b', [(point(1), {'latitude': 45, 'longitude': 10}),
                                     ({'latitude': 89, 'longitude': 0}, {'latitude': 89, 'longitude': 1}),
                                     ({'latitude': 0, 'longitude': 179}, {'latitude': 0, 'longitude': -179})])
def test_large_or_unsupported_bounds(a, b):
    with pytest.raises(ProviderError):
        trip_bounds(a, b)


def test_trip_endpoint_installs_new_graph_and_preserves_old_on_outage(dynamic_data, monkeypatch):
    import app.real_map.api as api
    monkeypatch.setattr(api, '_service', RealMapService())
    monkeypatch.setattr(api.providers, 'roads', lambda bbox: copy.deepcopy(dynamic_data))
    client = TestClient(app)
    old_simulation = client.get('/api/network').json()
    response = client.post('/api/real-map/trip', json={'source': point(1), 'destination': point(4)})
    assert response.status_code == 200
    assert response.json()['result']['success']
    assert client.get('/api/real-map/network').json()['metadata']['dynamic']
    assert client.get('/api/network').json() == old_simulation
    installed = api._service
    monkeypatch.setattr(api.providers, 'roads', Mock(side_effect=ProviderError('Offline')))
    assert client.post('/api/real-map/trip', json={'source': point(1), 'destination': point(4)}).status_code == 503
    assert api._service is installed


def test_search_bias_is_not_geographic_restriction(monkeypatch):
    provider = MapProviders()
    request = Mock(return_value={'features': [{'geometry': {'coordinates': [77, 12]}, 'properties': {'name': 'Place', 'city': 'City'}}]})
    monkeypatch.setattr(provider, '_request', request)
    result = provider.search('Place', point(1))
    assert result[0]['latitude'] == 12
    assert request.call_args.kwargs['params']['lat'] == point(1)['latitude']
    assert 'bbox' not in request.call_args.kwargs['params']


def test_nearby_distance_sort_and_deduplication(monkeypatch):
    provider = MapProviders()
    monkeypatch.setattr(provider, '_overpass_request', lambda query: {'elements': [
        {'lat': 13.01, 'lon': 80, 'tags': {'name': 'Far'}},
        {'lat': 13.001, 'lon': 80, 'tags': {'name': 'Near'}},
        {'lat': 13.001, 'lon': 80, 'tags': {'name': 'Near'}}]})
    assert [p['name'] for p in provider.nearby({'latitude': 13, 'longitude': 80})] == ['Near', 'Far']


def test_provider_cache_and_errors(monkeypatch):
    import app.real_map.providers as module
    provider = MapProviders()
    calls = []
    def respond(request):
        calls.append(request)
        return httpx.Response(200, json={'features': []})
    real_client = httpx.Client
    monkeypatch.setattr(module.httpx, 'Client', lambda **kw: real_client(transport=httpx.MockTransport(respond), **kw))
    monkeypatch.setattr(module.time, 'sleep', lambda seconds: None)
    assert provider.search('test') == []
    assert provider.search('test') == []
    assert len(calls) == 1
    assert calls[0].headers['User-Agent'] == 'SmartTrafficUCS-Academic/1.0'
    assert len(provider.cache) == 1


def test_provider_fallback(monkeypatch):
    provider = MapProviders()
    request = Mock(side_effect=[ProviderError('busy'), {'elements': []}])
    monkeypatch.setattr(provider, '_request', request)
    assert provider.roads((1, 2, 3, 4)) == {'elements': []}
    assert request.call_count == 2


@pytest.mark.parametrize('endpoint,body', [('search', {'query': '  '}), ('search', {'query': 'x'}),
    ('search', {'query': 'city', 'bias': {'latitude': 100, 'longitude': 20}}), ('trip', {'source': point(1)})])
def test_request_validation(endpoint, body):
    assert TestClient(app).post('/api/real-map/' + endpoint, json=body).status_code == 422
