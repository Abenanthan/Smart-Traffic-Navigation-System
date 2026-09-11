"""Convert a bounded OSM way snapshot to the existing road/traffic/graph types.

OSM node identity determines connectivity (not intersecting lines on screen).
Shape-only vertices stay in the polyline; shared vertices split ways into roads.
Distances are haversine kilometres. At an assumed 30 km/h, base time is rounded
up to whole minutes (minimum one), matching the existing integer-minute model.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
import math

from ..models import Node, Road
from ..road_network import RoadNetwork
from ..traffic_data import TrafficData
from ..weighted_graph import WeightedGraph
from .travel_time import TravelTimeRoad, TravelTimeTraffic

BBOX = (12.995, 80.260, 13.010, 80.278)  # south, west, north, east
SPEED_KMH = 30
ROAD_TYPES = {
    'primary', 'secondary', 'tertiary', 'residential', 'unclassified',
    'living_street', 'service', 'primary_link', 'secondary_link', 'tertiary_link',
}


def distance_km(a, b):
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlat, dlon = lat2 - lat1, math.radians(b[1] - a[1])
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * math.asin(math.sqrt(min(1, h)))


class GeographicGraph(WeightedGraph):
    """Keep inherited traffic/cost behaviour, filtering prohibited directions."""

    def __init__(self, network, traffic, road_details):
        self.road_details = road_details
        super().__init__(network, traffic)

    def _filter_directions(self, nodes):
        for node in nodes:
            self._adjacency[node] = [
                edge for edge in self._adjacency[node]
                if not self.road_details[edge.road_id]['oneWay']
                or edge.from_node == self.network.get_road(edge.road_id).from_node
            ]

    def rebuild(self):
        super().rebuild()
        self._filter_directions(self.network.node_ids)

    def _rebuild_road(self, road_id):
        super()._rebuild_road(road_id)
        road = self.network.get_road(road_id)
        self._filter_directions((road.from_node, road.to_node))


@dataclass
class GeographicData:
    network: RoadNetwork
    traffic: TrafficData
    graph: GeographicGraph
    coordinates: dict
    road_details: dict
    metadata: dict


def build_geographic_graph(data, bbox=BBOX, *, dynamic=False, anchor_points=()):
    if not isinstance(data, dict) or not isinstance(data.get('elements'), list):
        raise ValueError('Map data must contain an OSM elements list.')
    if not 0 < len(data['elements']) <= (30000 if dynamic else 2000):
        raise ValueError('Map snapshot is empty or exceeds the bounded-area limit.')
    south, west, north, east = bbox
    coordinates, names, parts = {}, defaultdict(set), []
    seen_ways = set()

    for way in data['elements']:
        if way.get('type') != 'way':
            continue
        tags = way.get('tags', {})
        if tags.get('highway') not in (ROAD_TYPES | {'motorway', 'trunk', 'motorway_link', 'trunk_link'} if dynamic else ROAD_TYPES):
            continue
        # Restrictive access and conditional permissions are conservatively omitted.
        access = tags.get('motorcar', tags.get('motor_vehicle', tags.get('vehicle', tags.get('access', 'yes'))))
        if access not in ('yes', 'permissive', 'designated') or any('conditional' in k for k in tags):
            continue
        direction = tags.get('oneway', 'yes' if tags.get('junction') == 'roundabout' else 'no')
        if direction not in ('yes', '1', 'true', '-1', 'no', '0', 'false'):
            continue  # e.g. reversible roads need a time-dependent model
        ids, geometry = way.get('nodes', []), way.get('geometry', [])
        if len(ids) != len(geometry) or len(ids) < 2 or len(ids) > 10000:
            raise ValueError('A road has missing or invalid geometry.')
        way_id = str(way.get('id', ''))
        if not way_id or way_id in seen_ways:
            raise ValueError('Map data contains a missing or duplicate way ID.')
        seen_ways.add(way_id)
        points = []
        for node_id, point in zip(ids, geometry):
            try:
                lat, lon = float(point['lat']), float(point['lon'])
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError('A road has invalid geographic coordinates.') from error
            if not math.isfinite(lat + lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
                raise ValueError('A road has invalid geographic coordinates.')
            node_id = str(node_id)
            coord = [lat, lon]
            if node_id in coordinates and coordinates[node_id] != coord:
                raise ValueError('An OSM node has inconsistent coordinates.')
            coordinates[node_id] = coord
            points.append(node_id)
        if direction == '-1':
            points.reverse()
        # Do not join across excursions outside the supported area.
        run = []
        for node_id in points + [None]:
            p = coordinates.get(node_id)
            if p is not None and south <= p[0] <= north and west <= p[1] <= east:
                if not run or run[-1] != node_id:
                    run.append(node_id)
            else:
                if len(run) >= 2:
                    parts.append((way_id, tags, direction, run))
                run = []

    occurrences = Counter(n for _, _, _, nodes in parts for n in nodes)
    # Split at existing OSM vertices near selected places, retaining real connectivity.
    for point in anchor_points:
        if occurrences:
            nearest = min(occurrences, key=lambda n: distance_km(point, coordinates[n]))
            occurrences[nearest] = max(2, occurrences[nearest])
    node_ids, roads, details, pairs = {}, [], {}, set()

    def node_id(osm_id):
        if osm_id not in node_ids:
            node_ids[osm_id] = f'J{len(node_ids) + 1:03d}'
        return node_ids[osm_id]

    def add_segment(way_id, tags, direction, shape):
        a, b = node_id(shape[0]), node_id(shape[-1])
        pair = frozenset((a, b))
        # Give parallel roads distinct paths, so inherited path repricing is exact.
        if a == b or pair in pairs:
            if len(shape) > 2:
                middle = len(shape) // 2
                add_segment(way_id, tags, direction, shape[:middle + 1])
                add_segment(way_id, tags, direction, shape[middle:])
                return
            virtual_id = f'via-{way_id}-{len(roads)}'
            coordinates[virtual_id] = [(x + y) / 2 for x, y in zip(coordinates[shape[0]], coordinates[shape[1]])]
            add_segment(way_id, tags, direction, [shape[0], virtual_id])
            add_segment(way_id, tags, direction, [virtual_id, shape[1]])
            return
        geometry = [coordinates[n] for n in shape]
        length = sum(distance_km(x, y) for x, y in zip(geometry, geometry[1:]))
        if length <= 0:
            return
        road_id = f'M{len(roads) + 1:03d}'
        name = tags.get('name:en') or tags.get('name') or f"Unnamed {tags['highway'].replace('_', ' ')} road"
        names[shape[0]].add(name)
        names[shape[-1]].add(name)
        road_type = TravelTimeRoad if dynamic else Road
        minutes = length / SPEED_KMH * 60
        roads.append(road_type(road_id, a, b, length, minutes if dynamic else max(1, math.ceil(minutes))))
        pairs.add(pair)
        details[road_id] = {
            'name': name, 'osmWayId': way_id, 'geometry': geometry,
            'oneWay': direction in ('yes', '1', 'true', '-1'),
            'assumedSpeedKmh': SPEED_KMH,
        }

    for way_id, tags, direction, nodes in parts:
        start = 0
        for index in range(1, len(nodes)):
            if occurrences[nodes[index]] > 1 or index == len(nodes) - 1:
                add_segment(way_id, tags, direction, nodes[start:index + 1])
                start = index
    if not roads or len(node_ids) > (15000 if dynamic else 1500) or len(roads) > (25000 if dynamic else 2500):
        raise ValueError('Map contains no usable roads or exceeds the graph size limit.')
    nodes = [Node(id, f"{' / '.join(sorted(names[osm_id])) or 'Road junction'} · {id}") for osm_id, id in node_ids.items()]
    network = RoadNetwork(nodes, roads)
    traffic = TravelTimeTraffic(network) if dynamic else TrafficData(network)
    graph = GeographicGraph(network, traffic, details)
    metadata = {
        'area': 'Selected trip area' if dynamic else 'Besant Nagar, Chennai', 'bbox': list(bbox),
        'dynamic': dynamic, 'snapLimitMetres': 500 if dynamic else 80,
        'source': 'OpenStreetMap contributors', 'license': 'ODbL 1.0',
        'sourceUrl': 'https://www.openstreetmap.org/copyright',
        'snapshotDate': data.get('osm3s', {}).get('timestamp_osm_base', 'unknown'),
        'assumedSpeedKmh': SPEED_KMH,
        'baseTimeRounding': 'No per-segment rounding; fractional minutes.' if dynamic else 'Ceiling to whole minutes; minimum 1 minute per graph road.',
        'trafficMultipliers': {'low': 1, 'medium': 1.5, 'high': 2.5} if dynamic else None,
        'trafficMode': 'Simulated Real-Time Traffic', 'reroutingOrigin': 'Original selected source',
    }
    return GeographicData(network, traffic, graph, {id: coordinates[osm] for osm, id in node_ids.items()}, details, metadata)
