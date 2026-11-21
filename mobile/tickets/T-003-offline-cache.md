# T-003 Offline cache and connectivity banner

## Web source

- `frontend/src/components/OfflineBanner.svelte`
- `frontend/src/lib/apiCache.ts`
- `frontend/src/lib/onlineStore.ts`
- `frontend/sw.js` (fetch handler, strategies, `purgeApiCache`)
- `frontend/src/lib/sw.test.ts`

## What it does

- The browser service worker (`frontend/sw.js`) caches same-origin `GET /api/*` responses in one cache (`partiu-api-<version>`), at most 150 entries (oldest inserted are trimmed). The cache key is the request URL only; it holds no user id.
- `GET /api/auth/*` is network-first: it tries the network, caches an OK response, and only on a network failure falls back to the cached copy (so `GET /api/auth/me` can be served from cache when offline). With no cached copy it answers a synthetic `503` `{"error":"Offline"}`.
- All other `GET /api/*` are stale-while-revalidate: a cached copy is returned immediately and a background request refreshes the cache (the page is not told, so the refreshed data shows on the next read). With no cached copy the app waits for the network; if that fails it gets the synthetic `503` `{"error":"Offline"}`. Only OK responses are cached.
- Non-GET `/api/*` requests pass through. If the response is OK the whole API cache is purged and awaited before the response is returned, so the re-read after an edit cannot get the old copy. A failed mutation leaves the cache alone (`sw.test.ts`): the purge runs only when the response is OK (`sw.js:74`), so an HTTP 500 answer to a PUT leaves every cached entry in place (a rejected write changed nothing on the server). The order is: the network call finishes first, then the purge, then the response goes back to the page (`sw.test.ts` expects the timeline `network`, `purge`). The service-worker purge empties the current-version API cache (`sw.js:169-177`); the page-side `purgeApiCache()` below removes every version.
- Service worker version and activation (web behaviour, `sw.js:15-17, 23-36`): the caches carry a version (`v21` today) in the names `partiu-static-<v>` and `partiu-api-<v>`. A new worker takes over immediately (`skipWaiting` on install, `clients.claim` on activate) and on activate deletes every cache whose name is not the current static or API cache, so a deploy that bumps the version drops all old cached API data and assets. The API cache is therefore purged in four situations: a successful non-GET API call, sign-in, sign-out, and a service-worker version change (plus the 150-entry trim).
- Static assets (web behaviour, `sw.js:96-117`): `/assets/*` (content-hashed JS, CSS, fonts) is cache-first from a second cache, `partiu-static-<v>`, at most 80 entries (oldest trimmed). A cached copy is returned without asking the network; a miss is fetched and cached if OK; if the network is down the answer is a bare HTML page `<h1>Offline</h1>` (content type text/html). This static cache is not touched by `purgeApiCache` or by sign-out (it holds no user data).
- App shell (web behaviour, `sw.js:96-99, 123-132`): everything else same-origin that is not `/api/` or `/assets/` (the HTML shell, icons, manifest) is network-first. Online it always fetches the latest and stores it in the static cache (trimmed with the API limit of 150 even there, a web quirk); offline it serves the last stored copy, so the web app still starts with no connection; with nothing stored it returns the JSON `503` `{"error":"Offline"}`. A new deploy is picked up on the next online load. User-visible result offline: the app opens, cached screens show their last data (stale-while-revalidate), uncached screens fail with the offline error and the amber banner is shown. Native must show the same: opening the app offline shows the last stored session user and last stored lists (see Native additions).
- Cross-origin requests (map tiles) are not handled by the service worker (`sw.js:53`): the worker never answers them, so a dropped map tile reaches the page as an ordinary network error and is not replaced by the worker's JSON `503` (which the basemap would read as "blocked").
- `purgeApiCache()` (`apiCache.ts:18-31`) deletes every cache whose name starts with `partiu-api-`, whatever its version (for example both `partiu-api-v20` and `partiu-api-v21`: an install that has not yet activated the new worker still holds the previous account's answers). Caches with any other name are left alone: `partiu-static-v21` (the app shell and assets, the same for every user, so clearing them would only cost a cold start) and unrelated names such as `other-app-cache`. Where `CacheStorage` does not exist (`typeof caches === 'undefined'`) it does nothing. It never fails: any error while listing or deleting is swallowed, so signing in or out can never be blocked by a cache that will not clear (the worst case is one stale read that the background refresh corrects). It is called after a successful sign-in (password and 2FA paths) and on sign-out, because the cache is not per-user (one account once saw another's visited countries).
- Offline banner (`OfflineBanner.svelte`): a sticky amber strip with the text "You're offline — showing cached data" (English only, not translated) shown while `navigator.onLine` is false, driven by the browser `online`/`offline` events (`onlineStore.ts`).
- Writes made while offline are not queued; they fail with the network error.
- Images (trip cover, boarding pass and document page images) are `GET /api/...` URLs, so the service worker caches them like any other API GET; the web has no separate image cache. A trip cover URL carries `?t=` after a refresh (T-009).

## API calls

- None of its own. It applies to every `GET /api/*` call.

## Android notes

The web service worker's version purge, `/assets/*` cache and app-shell rules have no Android equivalent to build: the assets are bundled in the APK, so no asset cache is needed and the app always opens offline. Clear the stored GET cache when the app version or cache schema version changes (the native equivalent of the version purge). Store responses in SQLDelight or Room (shared module preferred). Observe connectivity with `ConnectivityManager.registerDefaultNetworkCallback`. Use Coil's disk cache for images and clear it with the API cache on sign-out.

## iOS notes

The web service worker's version purge, `/assets/*` cache and app-shell rules have no iOS equivalent to build: the assets are bundled in the app, so no asset cache is needed and the app always opens offline. Clear the stored GET cache when the app version or cache schema version changes. Observe connectivity with `NWPathMonitor`. Use URLCache or the image library's disk cache for images and clear it with the API cache on sign-out. Do not rely on `URLSession` default caching for authenticated JSON.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- Offline cache (C04): `core-data` repositories over KStore JSON files (`KStoreRepositories.kt`, `StoreFactory.kt`, `PlatformStoreFactory.*.kt`); fine for small caches, add SQLDelight or Room if you need queries over many rows; JSON per GET keyed by account and URL; cap about 150 entries ; copy [PeopleInSpace: `PeopleInSpace.sq`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/sqldelight/com/dev/johnoreilly/peopleinspace/PeopleInSpace.sq)
- HTTP client (C01): reuse the shared client in `backend-client/.../backend/client/Clients.kt` (`KtorAuthApi` style: one small API class per area); a caching layer wrapping the client; purge on any successful non-GET ; copy [PeopleInSpace: `Koin.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/di/Koin.kt)
- Shared API wrapper and caching layer (C33): the caching layer wraps the one API client from T-001 ; copy [MortyComposeKMM: `MortyRepository.kt`](https://github.com/joreilly/MortyComposeKMM/blob/main/shared/src/commonMain/kotlin/dev/johnoreilly/mortycomposekmm/shared/MortyRepository.kt)
- Platform adapters (C22): `expect`/`actual` like `PlatformHttpClient.*.kt` and `PlatformStoreFactory.*.kt`, small inputs and outputs (`SOFTWARE_PATTERNS.md` Adapter); connectivity (Android `ConnectivityManager`, iOS `NWPathMonitor`) ; copy no sample
- Unit tests (C20): `commonTest` in `core-data` (e.g. `SyncMergeTest.kt`) with `kotlin-test` and `kotlinx-coroutines-test`; fake HTTP with Ktor `MockEngine` (add) ; copy no sample
- Repository (`SOFTWARE_PATTERNS.md`): one `ApiCache` hides storage and refresh; the offline banner reads a sealed connectivity state ; copy no sample

## Native additions (not in web)

- Persist the latest successful JSON per GET, keyed by account and URL, so one account never sees another's data even without a purge; also clear it on server-address change.
- Tell the screen when the background refresh finishes so it can update (the web does not).
- Cache `GET /api/auth/me` is not required natively; a stored session user may be used to open the app offline.
- Cap and eviction policy may differ from 150 entries.
- The offline banner follows the platform reachability API (Android `ConnectivityManager`, iOS `NWPathMonitor`), as the web follows `navigator.onLine` events (`onlineStore.ts`): it appears when the device goes offline and disappears on reconnect. The web's service-worker offline shell page has no native equivalent.

## Tests

- Stale-while-revalidate: a GET answered once is served from the cache when the network fails; with no cache and no network the call fails with an offline error; only OK responses are cached.
- Invalidation (mirrors `sw.test.ts`): after a successful POST, PATCH, PUT or DELETE the cache is empty before the call returns; a failed mutation leaves the cache untouched.
- Sign-in (password and 2FA) and sign-out each clear the whole cache.
- Banner: shown with the text "You're offline — showing cached data" when connectivity is lost and hidden when it returns.
- Offline write: a mutation made offline fails and is not queued.
- Native additions: after sign-out and sign-in as another user the first screen never shows the previous user's data.
- Version test: after the app or cache schema version changes, all stored GET responses are gone on first launch.
- Offline launch test: with the network off, the app opens, shows the last stored session user and the last stored lists, an uncached screen shows the offline error, and the offline banner is visible.
- Invalidation failure case: a mutation answered with HTTP 500 leaves the stored GET responses untouched (web test: "leaves the cache alone when the mutation fails").
- Invalidation order: a successful PUT on a URL whose GET is stored removes the stored response before the PUT's result is delivered to the caller, so an immediate re-read cannot get the pre-edit copy; the sequence is network call, then clear, then return (web test: "purges the API cache before a mutation resolves, not after").
- Third-party requests (for example map tiles from another host) are not intercepted by the app's cache layer: a failed tile request surfaces as a plain network error, not as an offline JSON error (web test: "does not handle cross-origin requests at all").
- Sign-in/sign-out clearing: with stored GET responses under schema versions 20 and 21, signing in or out removes both (web test: "drops every versioned API cache"); stored data that is not API responses (static assets, any other cache) is left (web test: "leaves the static caches alone").
- Clearing is safe: if the response store is missing or throws while clearing, the clear does nothing and sign-in or sign-out still completes with no error (web test: "does nothing where CacheStorage is unavailable", web test: "never rejects, so it cannot block signing in or out").
- Web tests mirrored: frontend/src/lib/apiCache.test.ts, frontend/src/lib/sw.test.ts

## Depends on

- T-001
- T-002
