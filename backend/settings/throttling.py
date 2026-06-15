"""Custom DRF throttles backed by the dedicated ``throttle`` cache alias.

DRF's built-in throttles use the *default* cache (Redis here). If Redis is down
that turns every throttled request — including login — into a 500. Routing the
counters through the ``throttle`` cache (local memory by default) keeps
brute-force protection working without a hard Redis dependency.
"""

from django.core.cache import caches
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle

_throttle_cache = caches["throttle"]


class CacheAnonRateThrottle(AnonRateThrottle):
    cache = _throttle_cache


class CacheScopedRateThrottle(ScopedRateThrottle):
    cache = _throttle_cache
