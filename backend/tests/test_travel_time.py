import pytest

from app.models import TrafficLevel
from app.real_map.travel_time import TravelTimeRoad, TravelTimeTraffic
from app.real_map.graph_builder import build_geographic_graph
from app.road_network import RoadNetwork
from app.models import Node


@pytest.mark.parametrize('segments', [1, 10, 100])
@pytest.mark.parametrize('level,expected', [('low', 2), ('medium', 3), ('high', 5)])
def test_one_kilometre_time_independent_of_segmentation(segments, level, expected):
    roads = [TravelTimeRoad(str(i), str(i), str(i+1), 1/segments, 2/segments, TrafficLevel(level)) for i in range(segments)]
    assert sum(road.cost for road in roads) == pytest.approx(expected)


def test_import_does_not_round_each_segment():
    data = {'elements': [{'type': 'way', 'id': 1, 'tags': {'highway': 'residential'},
                         'nodes': [1, 2], 'geometry': [{'lat': 13, 'lon': 80.265}, {'lat': 13, 'lon': 80.266}]}]}
    graph = build_geographic_graph(data, dynamic=True)
    road = graph.network.roads[0]
    assert 0 < road.base_travel_time < 1
    assert road.cost == pytest.approx(road.distance / 30 * 60)


def test_traffic_conditions_match_actual_edge_cost_and_blocking():
    road = TravelTimeRoad('r', 'a', 'b', .1, .2)
    network = RoadNetwork([Node('a', 'A'), Node('b', 'B')], [road])
    traffic = TravelTimeTraffic(network)
    traffic.apply_update('r', 'high')
    condition = traffic.condition_of('r')
    assert condition.delay == pytest.approx(.3)
    assert condition.cost == pytest.approx(.5)
    assert traffic.delay_of('r') == pytest.approx(.3)
    traffic.apply_update('r', 'blocked')
    assert traffic.condition_of('r').cost is None
    assert traffic.delay_of('r') is None
