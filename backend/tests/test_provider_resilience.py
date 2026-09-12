from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import Mock
import time

import httpx
import pytest

from app.real_map.providers import MapProviders, ProviderError, ProviderLimitError, ProviderBusyError


def test_slow_nearby_does_not_lock_other_server_or_cache(monkeypatch):
    import app.real_map.providers as module
    provider = MapProviders()
    entered, release = Event(), Event()
    def handle(request):
        if request.url.host == 'slow.test':
            entered.set()
            assert release.wait(3)
        return httpx.Response(200, json={'elements': []})
    client = httpx.Client
    monkeypatch.setattr(module.httpx, 'Client', lambda **kw: client(transport=httpx.MockTransport(handle), **kw))
    monkeypatch.setattr(module.time, 'sleep', lambda seconds: None)
    provider._request('https://cached.test', query='roads')
    with ThreadPoolExecutor() as pool:
        slow = pool.submit(provider._request, 'https://slow.test', query='nearby')
        assert entered.wait(1)
        try:
            assert provider._request('https://cached.test', query='roads') == {'elements': []}
            assert provider._request('https://other.test', query='roads') == {'elements': []}
        finally:
            release.set()
        slow.result()


def test_successful_alternate_is_preferred_on_next_request(monkeypatch):
    provider = MapProviders()
    request = Mock(side_effect=[ProviderError('timeout'), {'elements': []}, {'elements': []}])
    monkeypatch.setattr(provider, '_request', request)
    provider._overpass_request('one')
    provider._overpass_request('two')
    assert [c.args[0] for c in request.call_args_list] == [provider.overpass, provider.overpass_fallback, provider.overpass_fallback]


def test_cached_alternate_avoids_retrying_failed_primary(monkeypatch):
    provider = MapProviders()
    value = {'elements': []}
    provider.cache[provider._cache_key(provider.overpass_fallback, None, 'roads')] = (time.monotonic(), value, 20)
    request = Mock(side_effect=AssertionError('Cache should be used'))
    monkeypatch.setattr(provider, '_request', request)
    assert provider._overpass_request('roads') is value


def test_payload_limit_does_not_trigger_another_download(monkeypatch):
    provider = MapProviders()
    request = Mock(side_effect=ProviderLimitError('Too large'))
    monkeypatch.setattr(provider, '_request', request)
    with pytest.raises(ProviderLimitError):
        provider._overpass_request('large')
    assert request.call_count == 1


def test_failed_servers_cool_down_instead_of_repeated_long_waits(monkeypatch):
    provider = MapProviders()
    request = Mock(side_effect=ProviderError('timeout'))
    monkeypatch.setattr(provider, '_request', request)
    with pytest.raises(ProviderError):
        provider._overpass_request('one')
    with pytest.raises(ProviderError, match='minute'):
        provider._overpass_request('two')
    assert request.call_count == 2


def test_occupied_healthy_server_is_revisited_after_alternate_fails(monkeypatch):
    provider = MapProviders()
    request = Mock(side_effect=[ProviderBusyError('nearby running'), ProviderError('timeout'), {'elements': []}])
    monkeypatch.setattr(provider, '_request', request)
    assert provider._overpass_request('roads') == {'elements': []}
    assert provider.overpass not in provider.failed_until
    assert request.call_args.args[0] == provider.overpass
