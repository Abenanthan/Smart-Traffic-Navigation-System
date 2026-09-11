"""Approximate minutes for geographic trips; the teaching model is unchanged."""
from dataclasses import replace

from ..models import Road, TrafficLevel
from ..traffic_data import TrafficData

TRAFFIC_MULTIPLIERS = {TrafficLevel.LOW: 1.0, TrafficLevel.MEDIUM: 1.5, TrafficLevel.HIGH: 2.5}


class TravelTimeRoad(Road):
    @property
    def traffic_delay(self):
        if self.traffic is TrafficLevel.BLOCKED:
            raise ValueError('Blocked roads have no finite travel time.')
        return self.base_travel_time * (TRAFFIC_MULTIPLIERS[self.traffic] - 1)


class TravelTimeTraffic(TrafficData):
    def delay_of(self, road_id):
        road = self.network.get_road(road_id)
        return road.traffic_delay if road.is_traversable else None

    def condition_of(self, road_id):
        return replace(super().condition_of(road_id), delay=self.delay_of(road_id))
