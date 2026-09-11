import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.real_map.graph_builder import build_geographic_graph
from app.real_map.service import RealMapService
from app.real_map.providers import MapProviders
from app.real_map.travel_time import TravelTimeRoad, TRANSPORT_PROFILES
from app.models import TrafficLevel
from test_real_map import snapshot, way, POINTS


@pytest.mark.parametrize('mode,minutes', [('car', 2), ('two_wheeler', 60/35), ('walk', 12)])
def test_one_km_by_mode(mode, minutes):
    speed = TRANSPORT_PROFILES[mode]['speedKmh']
    road = TravelTimeRoad('a', 'b', 'c', 1, 60/speed, transport_mode=mode)
    assert road.cost == pytest.approx(minutes)
    road.traffic = TrafficLevel.HIGH
    assert road.cost == pytest.approx(minutes * (1 if mode == 'walk' else 2.5))


def graph(mode, *ways):
    return build_geographic_graph(snapshot(*ways), dynamic=True, transport_mode=mode)


@pytest.mark.parametrize('mode,ids', [('car', {'1', '3'}), ('two_wheeler', {'2', '3'}), ('walk', {'1', '2', '3', '4'})])
def test_mode_specific_access_and_footpaths(mode, ids):
    result = graph(mode, way(1, [1, 2], motorcycle='no'), way(2, [2, 4], motorcar='no'),
                   way(3, [1, 3]), way(4, [3, 5], highway='footway'))
    assert {r['osmWayId'] for r in result.road_details.values()} == ids


def test_walk_ignores_vehicle_oneway_but_respects_foot_rules():
    result = graph('walk', way(1, [1, 2], oneway='yes'), way(2, [2, 4], **{'oneway:foot': '-1'}))
    values = list(result.road_details.values())
    assert values[0]['oneWay'] is False
    assert values[1]['oneWay'] is True
    reverse = result.network.roads[1]
    assert result.coordinates[reverse.from_node] == POINTS[4]


def test_walk_excludes_forbidden_roads_and_motorways():
    result = graph('walk', way(1, [1, 2], foot='no'), way(2, [2, 4], highway='motorway'),
                   way(3, [1, 3], access='private'), way(4, [3, 5], motorroad='yes'),
                   way(5, [5, 4], highway='path', access='private', foot='yes'))
    assert {r['osmWayId'] for r in result.road_details.values()} == {'5'}


def test_walk_ucs_and_traffic_keep_profile():
    service = RealMapService(snapshot(way(1, [1, 2], highway='footway'), way(2, [2, 4], highway='footway')), dynamic=True, transport_mode='walk')
    coords = lambda p: dict(zip(('latitude', 'longitude'), POINTS[p]))
    route = service.find_route(coords(1), coords(4))['result']['route']
    assert route['transportMode'] == 'walk'
    assert route['totalCost'] == pytest.approx(service.session.active_route.total_distance * 12)
    road = route['roadIds'][0]
    changed = service.update_traffic(road, 'high')['result']['route']
    assert changed['totalCost'] == pytest.approx(route['totalCost'])
    assert changed['totalDelay'] == 0
    assert service.update_traffic(road, 'blocked')['result']['route'] is None


def test_provider_walking_query_includes_paths(monkeypatch):
    provider = MapProviders()
    queries = []
    monkeypatch.setattr(provider, '_overpass_request', lambda query: queries.append(query))
    provider.roads((1, 2, 3, 4), 'walk')
    assert 'footway' in queries[0] and 'motorway' not in queries[0]
    provider.roads((1, 2, 3, 4), 'car')
    assert 'footway' not in queries[1]


@pytest.mark.parametrize('mode', ['car', 'two_wheeler', 'walk'])
def test_trip_mode_reaches_graph_and_response(mode, monkeypatch):
    import app.real_map.api as api
    monkeypatch.setattr(api, '_service', None)
    seen = []
    def roads(bbox, transport_mode):
        seen.append(transport_mode)
        return snapshot(way(1, [1, 2]), way(2, [2, 4]))
    monkeypatch.setattr(api.providers, 'roads', roads)
    response = TestClient(app).post('/api/real-map/trip', json={
        'source': dict(zip(('latitude', 'longitude'), POINTS[1])),
        'destination': dict(zip(('latitude', 'longitude'), POINTS[4])), 'transportMode': mode})
    assert response.status_code == 200
    assert response.json()['result']['route']['transportMode'] == mode
    assert seen == [mode]


def test_invalid_mode_rejected():
    response = TestClient(app).post('/api/real-map/trip', json={
        'source': {'latitude': 13, 'longitude': 80.265},
        'destination': {'latitude': 13.001, 'longitude': 80.266}, 'transportMode': 'plane'})
    assert response.status_code == 422
