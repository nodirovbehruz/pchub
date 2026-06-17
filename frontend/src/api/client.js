// Centralized API helpers. Adds Authorization + X-Club-Id tenant header to every call.
// Auto-refreshes JWT on 401, falls back to logout if refresh fails.

// Empty string = same origin. Vite proxy forwards /api/* → http://127.0.0.1:8000
export const API_BASE = '';

export function getAuthHeaders() {
  const token = localStorage.getItem('access_token') || '';
  const clubId = localStorage.getItem('active_club_id') || '';
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (clubId) headers['X-Club-Id'] = clubId;
  return headers;
}

// In-flight refresh promise to dedupe concurrent calls.
let refreshing = null;

async function tryRefresh() {
  const refresh = localStorage.getItem('refresh_token');
  if (!refresh) return false;
  if (refreshing) return refreshing;

  refreshing = (async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/accounts/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh }),
      });
      if (!res.ok) return false;
      const data = await res.json();
      if (data.access) {
        localStorage.setItem('access_token', data.access);
        if (data.refresh) localStorage.setItem('refresh_token', data.refresh);
        return true;
      }
      return false;
    } catch {
      return false;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

async function doFetch(url, options, headers) {
  return fetch(url, { ...options, headers });
}

// ── Lightweight GET cache (stale-while-revalidate) ──────────────────────────
// Makes section-switching feel instant: a recently fetched GET returns its
// cached value immediately, and a fresh request runs in the background to
// keep the cache warm. Any mutating request (POST/PATCH/PUT/DELETE) clears
// the cache so the next read is fresh.
const _cache = new Map();          // key → { ts, data }
const _inflight = new Map();       // key → Promise (dedupe concurrent GETs)
const CACHE_TTL = 12_000;          // 12s — long enough for back-and-forth nav
// BUGFIX: monotonic epoch bumped on every mutation / cache clear. A GET captures
// the epoch before it starts; if a mutation lands while the GET is in flight the
// epoch changes, so the GET refuses to repopulate the (now-cleared) cache with
// its stale pre-mutation snapshot.
let cacheEpoch = 0;

function _cacheKey(url) {
  // Scope by access token (per-user) + active club so one account/club never
  // reuses another's cached data.
  const token = (typeof localStorage !== 'undefined' && localStorage.getItem('access_token')) || '';
  const club = (typeof localStorage !== 'undefined' && localStorage.getItem('active_club_id')) || '';
  // Use a short token tail to keep keys compact but user-specific.
  const tok = token ? token.slice(-12) : '';
  return `${tok}|${club}|${url}`;
}

export function clearApiCache() { _cache.clear(); _inflight.clear(); cacheEpoch++; }

export async function apiFetch(path, options = {}) {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;
  const method = (options.method || 'GET').toUpperCase();
  const isGet = method === 'GET';
  // noCache: skip the read-side cache entirely — for live polls / explicit refresh
  // where a stale (≤12s) snapshot would defeat realtime/manual updates.
  const useCache = isGet && !options.noCache;
  const key = _cacheKey(url);

  // Mutations invalidate the whole cache + drop in-flight GETs so a stale
  // pre-mutation response can't be served after the change.
  if (!isGet) { _cache.clear(); _inflight.clear(); cacheEpoch++; }

  // Snapshot the epoch before issuing the GET so we can detect a mutation that
  // clears the cache while this request is in flight (see _cache.set guard below).
  const epochAtStart = cacheEpoch;

  // Serve fresh-enough GETs straight from cache (deep-cloned to avoid mutation).
  if (useCache) {
    const hit = _cache.get(key);
    if (hit && (Date.now() - hit.ts) < CACHE_TTL) {
      try { return structuredClone(hit.data); } catch { return hit.data; }
    }
    // Dedupe identical concurrent GETs.
    if (_inflight.has(key)) return _inflight.get(key);
  }

  const run = _doRequest(url, options);
  if (useCache) {
    _inflight.set(key, run.then(d => d).catch(e => { throw e; }));
    try {
      const data = await run;
      // BUGFIX: only repopulate the cache if no mutation cleared it while this GET
      // was in flight — otherwise we'd serve a stale pre-mutation snapshot.
      if (cacheEpoch === epochAtStart) _cache.set(key, { ts: Date.now(), data });
      return data;
    } finally {
      _inflight.delete(key);
    }
  }
  return run;
}

async function _doRequest(url, options) {
  // FormData → let the browser set Content-Type with boundary automatically.
  const isFormData = options.body instanceof FormData;
  const baseHeaders = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...getAuthHeaders(),
    ...(options.headers || {}),
  };
  let res = await doFetch(url, options, baseHeaders);

  // On 401: try refresh, then retry once.
  if (res.status === 401) {
    const ok = await tryRefresh();
    if (ok) {
      const retryHeaders = {
        ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
        ...getAuthHeaders(),
        ...(options.headers || {}),
      };
      res = await doFetch(url, options, retryHeaders);
    } else {
      // Refresh failed — force logout to redirect to Login screen.
      forceLogout();
      const err = new Error('Сессия истекла');
      err.status = 401;
      throw err;
    }
  }

  if (!res.ok) {
    const text = await res.text();
    let parsed;
    try { parsed = JSON.parse(text); } catch { parsed = text; }
    // Subscription gate (402): broadcast so the app can show a "renew" screen
    // instead of a generic error toast.
    if (res.status === 402 && parsed && parsed.code === 'subscription_inactive'
        && typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('subscription-inactive', { detail: parsed }));
    }
    const err = new Error(`HTTP ${res.status}`);
    err.status = res.status;
    err.body = parsed;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

export function decodeJwt(token) {
  if (!token) return null;
  try {
    const base = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(decodeURIComponent(
      atob(base).split('').map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)).join('')
    ));
  } catch {
    return null;
  }
}

// Single source of truth for clearing all session keys on logout.
function clearSession() {
  [
    'access_token', 'refresh_token',
    'active_club_id', 'active_club_name', 'active_club_role',
    'username', 'impersonate_mode',
  ].forEach(k => localStorage.removeItem(k));
  clearApiCache();
}

function forceLogout() {
  clearSession();
  // Reload to land on Login screen
  if (typeof window !== 'undefined') window.location.reload();
}

export function logout() {
  const refresh = localStorage.getItem('refresh_token');
  if (refresh) {
    fetch(`${API_BASE}/api/v1/accounts/logout/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ refresh }),
    }).catch(() => {});
  }
  clearSession();
}
