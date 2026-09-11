"""Read-only OSM providers. No provider is ever asked to calculate directions.

Explicit user requests only, serialized/throttled calls, bounded in-memory cache,
response limits and configurable hosts. No world dataset is saved to disk.
"""
from collections import OrderedDict
import json
import math
import os
from threading import Lock
import time

import httpx

from .graph_builder import distance_km, ROAD_TYPES
from .travel_time import road_types


class ProviderError(ValueError):
    pass


class MapProviders:
    def __init__(self):
        self.photon = os.getenv('PHOTON_URL', 'https://photon.komoot.io').rstrip('/')
        self.overpass = os.getenv('OVERPASS_URL', 'https://overpass-api.de/api/interpreter')
        self.overpass_fallback = os.getenv('OVERPASS_FALLBACK_URL', 'https://overpass.kumi.systems/api/interpreter')
        self.lock = Lock()
        self.cache = OrderedDict()
        self.last_request = 0

    def _request(self, url, *, params=None, query=None):
        key = (url, json.dumps(params, sort_keys=True), query)
        with self.lock:
            cached = self.cache.get(key)
            if cached and time.monotonic() - cached[0] < 900:
                self.cache.move_to_end(key)
                return cached[1]
            time.sleep(max(0, 1.1 - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            try:
                with httpx.Client(timeout=httpx.Timeout(55, connect=10), headers={'User-Agent': 'SmartTrafficUCS-Academic/1.0', 'Accept': 'application/json'}, follow_redirects=True) as client:
                    with client.stream('POST' if query else 'GET', url, params=params, data={'data': query} if query else None) as response:
                        response.raise_for_status()
                        body = bytearray()
                        for chunk in response.iter_bytes():
                            body.extend(chunk)
                            if len(body) > 12_000_000:
                                raise ProviderError('This area has too much road data. Choose a shorter trip or a less dense area.')
                        value = json.loads(body)
            except (httpx.HTTPError, ValueError) as error:
                if isinstance(error, ProviderError):
                    raise
                raise ProviderError('The map data provider is unavailable or busy. Wait a moment and retry. Your selections are kept.') from error
            if isinstance(value, dict) and value.get('remark'):
                raise ProviderError('The road provider could not finish this request. Retry or choose a shorter trip.')
            self.cache[key] = (time.monotonic(), value, len(body))
            while len(self.cache) > 32 or sum(item[2] for item in self.cache.values()) > 24_000_000:
                self.cache.popitem(last=False)
            return value

    def search(self, query, bias=None):
        params = {'q': query, 'limit': 8, 'lang': 'en'}
        if bias:
            params.update(lat=bias['latitude'], lon=bias['longitude'])
        data = self._request(self.photon + '/api/', params=params)
        if not isinstance(data, dict) or not isinstance(data.get('features'), list):
            raise ProviderError('Place search returned an invalid response. Please retry.')
        results = []
        for feature in data.get('features', []):
            p = feature.get('properties', {})
            coords = feature.get('geometry', {}).get('coordinates', [])
            if len(coords) < 2:
                continue
            if not all(isinstance(v, (float, int)) and math.isfinite(v) for v in coords[:2]) or not (-90 <= coords[1] <= 90 and -180 <= coords[0] <= 180):
                continue
            label = ', '.join(dict.fromkeys(str(p[k]) for k in ('name', 'street', 'district', 'city', 'state', 'country') if p.get(k)))
            results.append({'name': label or query, 'latitude': coords[1], 'longitude': coords[0]})
        return results

    def nearby(self, point):
        lat, lon = point['latitude'], point['longitude']
        # A small local set of named areas and useful destinations, not all POIs.
        query = f'''[out:json][timeout:25];(
          node(around:2000,{lat},{lon})[place~"^(suburb|neighbourhood|quarter|village|town)$"][name];
          nwr(around:1500,{lat},{lon})[amenity~"^(hospital|school|college|university|bus_station)$"][name];
          node(around:1500,{lat},{lon})[railway=station][name];
        );out center tags 100;'''
        data = self._overpass_request(query)
        if not isinstance(data, dict) or not isinstance(data.get('elements'), list):
            raise ProviderError('Nearby places returned an invalid response. Please retry.')
        places, seen = [], set()
        for item in data.get('elements', []):
            center = item.get('center', item)
            name = item.get('tags', {}).get('name:en') or item.get('tags', {}).get('name')
            if not name or name in seen or 'lat' not in center:
                continue
            seen.add(name)
            distance = distance_km([lat, lon], [center['lat'], center['lon']])
            places.append({'name': name, 'latitude': center['lat'], 'longitude': center['lon'], 'distanceKm': round(distance, 2)})
        return sorted(places, key=lambda item: item['distanceKm'])[:12]

    def roads(self, bbox, transport_mode='car'):
        types = '|'.join(sorted(road_types(transport_mode, ROAD_TYPES | {'motorway', 'trunk', 'motorway_link', 'trunk_link'})))
        bounds = ','.join(f'{v:.6f}' for v in bbox)
        return self._overpass_request(f'[out:json][timeout:45];way[highway~"^({types})$"]({bounds});out geom;')

    def _overpass_request(self, query):
        try:
            return self._request(self.overpass, query=query)
        except ProviderError:
            if not self.overpass_fallback or self.overpass_fallback == self.overpass:
                raise
            return self._request(self.overpass_fallback, query=query)


def trip_bounds(source, destination, padding_km=2):
    a, b = [source['latitude'], source['longitude']], [destination['latitude'], destination['longitude']]
    if abs(a[0]) > 85 or abs(b[0]) > 85 or abs(a[1] - b[1]) > 180:
        raise ProviderError('Polar and date-line crossing trips are not supported by this map loader.')
    lat_pad = padding_km / 111
    lon_pad = padding_km / (111 * math.cos(math.radians((a[0] + b[0]) / 2)))
    bbox = (max(-85, min(a[0], b[0]) - lat_pad), max(-180, min(a[1], b[1]) - lon_pad),
            min(85, max(a[0], b[0]) + lat_pad), min(180, max(a[1], b[1]) + lon_pad))
    width = distance_km([bbox[0], bbox[1]], [bbox[0], bbox[3]])
    height = distance_km([bbox[0], bbox[1]], [bbox[2], bbox[1]])
    if width * height > 2500 or distance_km(a, b) > 100:
        raise ProviderError('This trip exceeds the demo road-loading limit (100 km straight-line / 2,500 km²). Choose a shorter trip. Search works worldwide.')
    return bbox


providers = MapProviders()
