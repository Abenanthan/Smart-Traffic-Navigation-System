"""Approximate minutes for geographic trips; the teaching model is unchanged."""
from dataclasses import dataclass, replace

from ..models import Road, TrafficLevel
from ..traffic_data import TrafficData

TRAFFIC_MULTIPLIERS = {TrafficLevel.LOW: 1.0, TrafficLevel.MEDIUM: 1.5, TrafficLevel.HIGH: 2.5}
TRANSPORT_PROFILES = {
    'car': {'label': 'Car', 'speedKmh': 30, 'trafficMultipliers': {'low': 1, 'medium': 1.5, 'high': 2.5}},
    'two_wheeler': {'label': 'Two-wheeler', 'speedKmh': 35, 'trafficMultipliers': {'low': 1, 'medium': 1.5, 'high': 2.5}},
    'walk': {'label': 'Walking', 'speedKmh': 5, 'trafficMultipliers': {'low': 1, 'medium': 1, 'high': 1}},
}


def road_types(mode, motor_types):
    if mode not in TRANSPORT_PROFILES:
        raise ValueError('Choose Car, Two-wheeler, or Walking.')
    if mode == 'walk':
        return (motor_types - {'motorway', 'motorway_link', 'trunk', 'trunk_link'}) | {'footway', 'pedestrian', 'path', 'steps', 'track'}
    return motor_types


def access_and_direction(tags, mode):
    """Conservative OSM way access; mode-specific permissions override general ones."""
    if mode == 'walk':
        access = tags.get('foot', tags.get('access', 'yes'))
        direction = tags.get('oneway:foot', 'no')
        if tags.get('foot:forward') == 'no':
            if tags.get('foot:backward') == 'no':
                access = 'no'
            direction = '-1'
        elif tags.get('foot:backward') == 'no':
            direction = 'yes'
        if tags.get('motorroad') == 'yes':
            access = 'no'
    else:
        key = 'motorcycle' if mode == 'two_wheeler' else 'motorcar'
        access = tags.get(key, tags.get('motor_vehicle', tags.get('vehicle', tags.get('access', 'yes'))))
        implied = 'yes' if tags.get('junction') == 'roundabout' or tags.get('highway') == 'motorway' else 'no'
        direction = tags.get('oneway:' + key, tags.get('oneway', implied))
    return access, direction


@dataclass
class TravelTimeRoad(Road):
    transport_mode: str = 'car'
    @property
    def traffic_delay(self):
        if self.traffic is TrafficLevel.BLOCKED:
            raise ValueError('Blocked roads have no finite travel time.')
        return self.base_travel_time * (TRANSPORT_PROFILES[self.transport_mode]['trafficMultipliers'][self.traffic.value] - 1)


class TravelTimeTraffic(TrafficData):
    def delay_of(self, road_id):
        road = self.network.get_road(road_id)
        return road.traffic_delay if road.is_traversable else None

    def condition_of(self, road_id):
        return replace(super().condition_of(road_id), delay=self.delay_of(road_id))
