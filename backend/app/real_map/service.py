"""Independent real-map session, using the original NavigationSession and UCS."""

import json
from pathlib import Path
import random
import math
from dataclasses import replace

from ..navigation import NavigationSession, NavigationResult, RerouteDecision
from ..models import TrafficLevel
from .graph_builder import BBOX, build_geographic_graph, distance_km

DATA_FILE = Path(__file__).resolve().parents[2] / 'data' / 'besant_nagar.osm.json'


class GeographicNavigation(NavigationSession):
    def _decide(self, previous, previous_cost_now, new_route, search, update):
        # Avoid unnecessary route changes when UCS finds an equal-cost alternative.
        # This keeps a previously UCS-selected path only after the fresh search
        # proves its repriced cost equals the current optimum. No second search.
        if previous.path != new_route.path and previous_cost_now == new_route.total_cost:
            edges = [self.graph.edge_between(a, b) for a, b in zip(previous.path, previous.path[1:])]
            repriced = self._build_route(replace(search, path=previous.path, edges=edges))
            self.active_route = repriced
            return NavigationResult(
                success=True, decision=RerouteDecision.UNCHANGED,
                headline='Route remains optimal',
                reason=f'UCS found an equal-cost alternative. Keeping your existing route at {previous_cost_now} min.',
                route=repriced, previous_route=previous, previous_cost_now=previous_cost_now,
                saving=0, search=search, traffic_update=update,
            )
        return super()._decide(previous, previous_cost_now, new_route, search, update)


class RealMapService:
    def __init__(self, data=None, *, bbox=BBOX, dynamic=False, anchor_points=()):
        if data is None:
            with DATA_FILE.open(encoding='utf-8-sig') as handle:
                data = json.load(handle)
        self.data = build_geographic_graph(data, bbox, dynamic=dynamic, anchor_points=anchor_points)
        self.session = GeographicNavigation(self.data.network, self.data.traffic, self.data.graph)
        if dynamic:
            from .dynamic_navigation import DynamicNavigation
            self.session = DynamicNavigation(self.data.network, self.data.traffic, self.data.graph)
        self.requested_pair = None
        self.last_result = None

    def state(self):
        s = self.session
        # All locations are real graph endpoints. Presets are selected, not geocoded.
        locations = [
            {'id': n.id, 'name': n.name, 'coordinates': self.data.coordinates[n.id]}
            for n in s.network.nodes
        ]
        south, west, north, east = self.data.metadata['bbox']
        named_locations = [n for n in locations if 'Unnamed' not in n['name']] or locations
        source = min(named_locations, key=lambda n: distance_km(n['coordinates'], [north - .003, west + .002]))['id']
        destination = min(named_locations, key=lambda n: distance_km(n['coordinates'], [south + .003, east - .003]))['id']
        return {
            'metadata': self.data.metadata, 'locations': locations,
            'roads': [{**r, **self.data.road_details[r['roadId']]} for r in s.graph.cost_table()],
            'trafficCounts': s.traffic.counts_by_level(),
            'defaults': {'source': source, 'destination': destination},
            'requestedPair': list(self.requested_pair) if self.requested_pair else None,
            'activeRoute': self.route_data(s.active_route),
            'lastResult': self.last_result,
        }

    def route_data(self, route):
        if route is None:
            return None
        geometry = []
        steps = []
        for step in route.steps:
            detail = self.data.road_details[step.road_id]
            points = detail['geometry']
            road = self.session.network.get_road(step.road_id)
            if step.from_node != road.from_node:
                points = list(reversed(points))
            geometry.extend(points if not geometry else points[1:])
            steps.append({**step.to_dict(), 'name': detail['name'], 'oneWay': detail['oneWay']})
        return {
            **route.to_dict(), 'geometry': geometry, 'steps': steps,
            'highTrafficRoads': sum(step.traffic == 'high' for step in route.steps),
        }

    def response(self, result):
        if result is not None:
            output = result.to_dict()
            output['route'] = self.route_data(result.route)
            output['previousRoute'] = self.route_data(result.previous_route)
            # The unchanged engine records the trace; the real-map UI needs only
            # its summary, leaving the full educational replay on AI Simulation.
            if output.get('search'):
                output['search'].pop('trace', None)
            self.last_result = output
        else:
            self.last_result = None
        # Keep this long-running demo's memory bounded.
        self.session.history[:] = self.session.history[-5:]
        self.session.traffic.history[:] = self.session.traffic.history[-20:]
        return {'result': self.last_result, 'network': self.state()}

    def resolve_coordinate(self, latitude, longitude, role='source'):
        """Snap within 80 m to a junction with a usable departure/arrival edge."""
        if role not in ('source', 'destination'):
            raise ValueError('Choose source or destination as the location role.')
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in (latitude, longitude)):
            raise ValueError('Latitude and longitude must be finite numbers.')
        south, west, north, east = self.data.metadata['bbox']
        if not south <= latitude <= north or not west <= longitude <= east:
            raise ValueError('This point is outside the loaded road network. Search for your locations and find a new route to load roads for that trip.')
        graph = self.session.graph
        usable = {edge.from_node if role == 'source' else edge.to_node for edge in graph.edges()}
        candidates = [(distance_km([latitude, longitude], position) * 1000, id)
                      for id, position in self.data.coordinates.items() if id in usable]
        limit = self.data.metadata['snapLimitMetres']
        if not candidates or min(candidates)[0] > limit:
            raise ValueError(f'No usable road junction within {limit} metres. Choose a point closer to a road, or reopen blocked roads.')
        metres, id = min(candidates)
        return {'nodeId': id, 'name': self.session.network.get_node(id).name,
                'coordinates': self.data.coordinates[id], 'distanceMetres': round(metres, 1),
                'selectedCoordinates': [latitude, longitude]}

    def find_route(self, source, destination):
        snaps = {}
        try:
            for role, value in [('source', source), ('destination', destination)]:
                if isinstance(value, dict):
                    snaps[role] = self.resolve_coordinate(value.get('latitude'), value.get('longitude'), role)
            source = snaps['source']['nodeId'] if 'source' in snaps else source
            destination = snaps['destination']['nodeId'] if 'destination' in snaps else destination
        except ValueError as error:
            self.session.active_route = None
            self.requested_pair = None
            return self.response(NavigationResult(success=False, decision=RerouteDecision.NO_ROUTE,
                headline='Location outside supported roads', reason=str(error)))
        result = self.session.find_route(source, destination)
        if result.success:
            self.requested_pair = (result.route.source, result.route.destination)
        else:
            self.session.active_route = None  # Never display a stale route for new inputs.
            a, b = self.session.network.resolve(source), self.session.network.resolve(destination)
            self.requested_pair = (a, b) if a and b and a != b else None
            if result.validation and result.validation.error and result.validation.error.value == 'no_possible_route':
                result.headline = 'No route available'
        response = self.response(result)
        response['snappedLocations'] = snaps
        return response

    def _recover_if_reopened(self, result):
        # The original demo clears its route on disconnection. Remember this
        # page's endpoints so reopening roads can recover without another click.
        if self.session.active_route is None and self.requested_pair:
            update = result.traffic_update if result else None
            result = self.session.find_route(*self.requested_pair)
            result.traffic_update = update
        return result

    def update_traffic(self, road_id, traffic):
        result = self.session.update_traffic(road_id, TrafficLevel(traffic))
        return self.response(self._recover_if_reopened(result))

    def simulate(self, allow_blocking=False):
        result = self.session.simulate_random_change(random, allow_blocking=allow_blocking)
        return self.response(self._recover_if_reopened(result))

    def reset(self):
        result = self.session.reset_traffic()
        return self.response(self._recover_if_reopened(result))
