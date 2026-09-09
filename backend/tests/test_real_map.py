"""Geographic import, UCS reuse, directed costs, isolation, and API regressions."""

import math
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.navigation import NavigationSession
from app.real_map.graph_builder import build_geographic_graph, distance_km
from app.real_map.service import RealMapService
from app.weighted_graph import build_graph


POINTS = {
    1: [13.001, 80.265], 2: [13.001, 80.266], 3: [13.002, 80.265],
    4: [13.001, 80.267], 5: [13.002, 80.267], 6: [13.005, 80.265],
    7: [13.005, 80.266], 8: [13.001, 80.2655],
}


def way(id, nodes, **tags):
    return {'type': 'way', 'id': id, 'nodes': nodes,
            'geometry': [dict(zip(('lat', 'lon'), POINTS[n])) for n in nodes],
            'tags': {'highway': 'residential', 'name': f'Test road {id}', **tags}}


def snapshot(*ways):
    return {'elements': list(ways), 'osm3s': {'timestamp_osm_base': 'test fixture'}}


@pytest.fixture
def small_map():
    # Test-only geographic fixture: two paths of costs 2 and 3, plus an island.
    return RealMapService(snapshot(way(1, [1, 2]), way(2, [2, 4]), way(3, [1, 3]),
                                   way(4, [3, 5]), way(5, [5, 4]), way(6, [6, 7])))


def id_at(service, point):
    return next(id for id, coordinate in service.data.coordinates.items() if coordinate == POINTS[point])


def find(service, a=1, b=4):
    return service.find_route(id_at(service, a), id_at(service, b))


def test_real_snapshot_loads_and_default_route_is_ucs():
    service = RealMapService()
    state = service.state()
    assert state['metadata']['source'] == 'OpenStreetMap contributors'
    assert 100 < len(state['locations']) <= 1500
    assert all(road['osmWayId'].isdigit() for road in state['roads'])
    result = service.find_route(**state['defaults'])['result']
    assert result['success']
    assert result['route']['path'] == result['search']['path']
    assert result['route']['totalCost'] == sum(s['cost'] for s in result['route']['steps'])
    assert result['route']['geometry'][0] == service.data.coordinates[result['route']['source']]
    assert result['route']['geometry'][-1] == service.data.coordinates[result['route']['destination']]


def test_calls_existing_ucs_for_find_and_traffic(small_map, monkeypatch):
    import app.navigation as navigation
    spy = Mock(wraps=navigation.uniform_cost_search)
    monkeypatch.setattr(navigation, 'uniform_cost_search', spy)
    route = find(small_map)['result']['route']
    assert spy.call_count == 1
    result = small_map.update_traffic(route['roadIds'][0], 'high')['result']
    assert spy.call_count == 2
    assert result['decision'] == 'cheaper_route_found'
    assert result['previousCostNow'] == 14
    assert result['route']['totalCost'] == 3
    assert result['saving'] == 11


def test_block_and_reopen_recovers_route(small_map):
    route = find(small_map)['result']['route']
    first_road = route['roadIds'][0]
    result = small_map.update_traffic(first_road, 'blocked')['result']
    assert result['decision'] == 'route_blocked'
    assert result['route']['totalCost'] == 3
    assert first_road not in result['route']['roadIds']
    other_road = result['route']['roadIds'][0]
    result = small_map.update_traffic(other_road, 'blocked')
    assert not result['result']['success']
    assert result['network']['activeRoute'] is None
    restored = small_map.update_traffic(first_road, 'low')
    assert restored['result']['success']
    assert restored['network']['activeRoute']['totalCost'] == 2


def test_reset_recovers_disconnected_route(small_map):
    find(small_map)
    start = id_at(small_map, 1)
    for road in small_map.session.network.roads_at(start):
        small_map.update_traffic(road.id, 'blocked')
    assert small_map.session.active_route is None
    assert small_map.reset()['result']['route']['totalCost'] == 2


@pytest.mark.parametrize('a,b', [(None, 'J001'), ('J001', None), ('unsupported', 'J001'), ('J001', 'unsupported'), ('J001', 'J001')])
def test_invalid_inputs_clear_stale_route(small_map, a, b):
    find(small_map)
    response = small_map.find_route(a, b)
    assert not response['result']['success']
    assert response['network']['activeRoute'] is None


def test_disconnected_locations(small_map):
    response = find(small_map, 1, 6)
    assert not response['result']['success']
    assert response['network']['activeRoute'] is None
    assert find(small_map, 6, 7)['result']['success']


@pytest.mark.parametrize('direction', ['yes', '-1'])
def test_one_way_geometry_and_traffic(direction):
    service = RealMapService(snapshot(way(1, [1, 8, 2], oneway=direction)))
    a, b = (1, 2) if direction == 'yes' else (2, 1)
    assert not find(service, b, a)['result']['success']
    route = find(service, a, b)['result']['route']
    assert len(route['geometry']) == 3  # shape vertex is not discarded
    assert route['geometry'][0] == POINTS[a]
    road = route['roadIds'][0]
    for level, cost in [('medium', 6), ('high', 13), ('low', 1)]:
        assert service.update_traffic(road, level)['result']['route']['totalCost'] == cost
        assert not service.session.graph.neighbours(id_at(service, b))
    service.reset()
    assert not find(service, b, a)['result']['success']


def test_reverse_two_way_geometry():
    service = RealMapService(snapshot(way(1, [1, 8, 2])))
    assert find(service, 2, 1)['result']['route']['geometry'] == [POINTS[2], POINTS[8], POINTS[1]]


def test_parallel_roads_have_unambiguous_paths():
    service = RealMapService(snapshot(way(1, [1, 2]), way(2, [1, 8, 2])))
    pairs = [frozenset((r.from_node, r.to_node)) for r in service.session.network.roads]
    assert len(pairs) == len(set(pairs))
    route = find(service, 1, 2)['result']['route']
    changed = service.update_traffic(route['roadIds'][0], 'blocked')['result']
    assert changed['success']
    assert changed['decision'] == 'route_blocked'


def test_keeps_existing_route_when_alternative_has_equal_cost(small_map):
    # Explicit costs for tie handling; all production costs still use the importer.
    service = small_map
    service.session.network.get_road('M005').base_travel_time = 5
    service.session.graph.rebuild()
    baseline = find(service)['result']['route']
    # Increase old 2-min route by 5: alternative and old route now both cost 7.
    result = service.update_traffic(baseline['roadIds'][0], 'medium')['result']
    assert result['route']['totalCost'] == 7
    assert result['route']['roadIds'] == baseline['roadIds']
    assert result['decision'] == 'unchanged'


def test_geometry_and_units():
    graph = build_geographic_graph(snapshot(way(1, [1, 8, 2])))
    road = graph.network.roads[0]
    length = distance_km(POINTS[1], POINTS[8]) + distance_km(POINTS[8], POINTS[2])
    assert road.distance == pytest.approx(length)
    assert road.base_travel_time == max(1, math.ceil(length / 30 * 60))
    assert graph.road_details[road.id]['geometry'] == [POINTS[1], POINTS[8], POINTS[2]]


@pytest.mark.parametrize('bad_data', [{}, {'elements': []}, snapshot(way(1, [1, 2], access='private')), snapshot(way(1, [1, 2], oneway='reversible'))])
def test_empty_or_unsupported_map_rejected(bad_data):
    with pytest.raises(ValueError):
        build_geographic_graph(bad_data)


def test_malformed_map_rejected():
    data = snapshot(way(1, [1, 2]))
    data['elements'][0]['geometry'][0]['lat'] = float('nan')
    with pytest.raises(ValueError, match='coordinates'):
        build_geographic_graph(data)


def test_no_connections_created_at_visual_crossings():
    data = snapshot(way(1, [1, 5]), way(2, [3, 2]))
    service = RealMapService(data)
    assert not find(service, 1, 2)['result']['success']


def test_outside_bbox_not_bridged():
    data = snapshot(way(1, [1, 8, 2]))
    data['elements'][0]['geometry'][1] = {'lat': 14, 'lon': 81}
    with pytest.raises(ValueError):
        build_geographic_graph(data)


@pytest.fixture
def client(small_map, monkeypatch):
    import app.api as existing_api
    import app.real_map.api as real_api
    monkeypatch.setattr(real_api, '_service', small_map)
    monkeypatch.setattr(existing_api, 'session', NavigationSession(*build_graph()))
    with TestClient(existing_api.app) as c:
        yield c


def test_api_namespaces_are_isolated(client, small_map):
    original = client.post('/api/route', json={'source': 'A', 'destination': 'K'}).json()
    assert original['result']['route']['totalCost'] == 35
    response = client.post('/api/real-map/route', json={'source': id_at(small_map, 1), 'destination': id_at(small_map, 4)}).json()
    road = response['result']['route']['roadIds'][0]
    assert client.post('/api/real-map/traffic', json={'roadId': road, 'traffic': 'high'}).status_code == 200
    assert client.get('/api/network').json() == original['network']
    before = client.get('/api/real-map/network').json()
    client.post('/api/traffic', json={'roadId': 'R18', 'traffic': 'high'})
    assert client.get('/api/real-map/network').json() == before


def test_api_errors_simulation_reset(client, small_map):
    assert client.post('/api/real-map/traffic', json={'roadId': 'missing', 'traffic': 'low'}).status_code == 404
    assert client.post('/api/real-map/traffic', json={'roadId': 'M001', 'traffic': 'fake'}).status_code == 422
    assert client.post('/api/real-map/route', json={'source': 12, 'destination': None}).status_code == 422
    response = client.post('/api/real-map/simulate', json={})
    assert response.status_code == 200
    assert response.json()['result']['trafficUpdate']['changed']
    assert client.post('/api/real-map/reset').status_code == 200
    assert all(road['traffic'] == 'low' for road in client.get('/api/real-map/network').json()['roads'])


def test_bad_map_does_not_break_existing_api(client, monkeypatch):
    import app.real_map.api as real_api
    monkeypatch.setattr(real_api, '_service', None)
    monkeypatch.setattr(real_api, 'RealMapService', Mock(side_effect=ValueError('invalid data')))
    assert client.get('/api/real-map/network').status_code == 503
    assert client.get('/api/health').json()['locations'] == 16
