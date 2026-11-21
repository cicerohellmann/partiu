# T-013 Trip map

## Web source

- `frontend/src/components/TripMap.svelte`

Web tests mirrored: frontend/src/components/TripMap.test.ts

## What it does

- Map section of the trip detail page (`TripDetailPage.svelte` 823-826 renders `TripMap` only when the trip has at least one flight or one ground segment). Props: the trip's flights and ground segments. Stays and car rentals are NOT plotted.
- Airport coordinates: for each distinct departure/arrival IATA code of the flights, `GET /api/airports/{iata}` (`airportsApi.get`) is called in parallel; a failed lookup is ignored (that airport is skipped). The web does no caching of its own beyond the browser. An airport is usable only when `latitude` and `longitude` are non-null.
- Flights: each flight whose two airports both resolved is drawn as a great-circle arc (80 interpolated points), blue `#3b82f6`, two polylines (glow: weight 10, opacity 0.15; main: weight 2.5, opacity 0.9). Flights are not joined to each other; one arc per flight, no lines between consecutive stops.
- Airport markers: one round blue marker per resolved distinct airport with the IATA code as label; tooltip `CODE · city` (city falls back to the code).
- Ground segments: only segments with lat and lon at both ends are drawn (hand-typed places without coordinates are silently skipped). Each is a straight dashed line (weight 3, dash 7/6), coloured by type: train `#10b981`, bus `#f59e0b`, ferry `#06b6d4`, car `#8b5cf6` (other types fall back to blue). Each end gets a small square marker in that colour with a tooltip of the place name (HTML-escaped).
- The view fits to all airport and segment points, padding 40px. If no airport resolved and no segment is drawable, no map is created (the container stays empty; no explicit message).
- Tiles: with a key (`carto_api_key` on the current user), CARTO Voyager raster tiles `https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png?key=<url-encoded key>`, subdomains abcd, maxZoom 19. Without a key it uses OpenStreetMap tiles `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png` (maxZoom 19). It does NOT use free CARTO tiles. The fallback applies only to a keyed CARTO layer (TripMap.svelte:19-23, 159-182). It counts tile failures cumulatively, not "in a row": after the 4th failed tile (`UNREACHABLE_TILE_FAILURES`) with no tile ever loaded, the CARTO layer is removed and the OSM layer is added, once; earlier failures (1 to 3) change nothing. A single successful tile load, even before or between failures, turns the fallback off for good, so a flaky connection that lands one tile keeps CARTO however many tiles drop afterwards. After the swap, further errors do nothing (OSM is not added twice). Without a key there is no fallback: OSM is used from the start.
- Controls: zoom +/- control and attribution shown; mouse-wheel zoom off (it is always off). Pinch zoom and the +/- control keep working while dragging is locked; only dragging is toggled. The map is 280 px high and full width. Attribution text: OSM tiles show "(c) OpenStreetMap" (link to openstreetmap.org/copyright); CARTO tiles show "(c) OSM (c) CARTO" with links (TripMap 128-135, 139, 153, 320). On touch devices dragging starts off; a button at the top right toggles it (label "Move map" when pan is off, "Lock map" when on; i18n `map.unlock` / `map.lock`). On non-touch devices dragging starts on (touch means `ontouchstart` exists on window or `navigator.maxTouchPoints` > 0; TripMap.svelte:55-58). The button shows "🔒 Lock map" while dragging is on and "✋ Move map" while it is off, and exposes its state as pressed (`aria-pressed` = dragging on). Pressing it only calls enable/disable on the existing map's dragging handler (TripMap.svelte:62-67); the map is not rebuilt.
- Print: the toggle is hidden and the map redraws its size before printing. In print the map is 260 px high, square corners, no shadow, a thin border, and the attribution is hidden (363-381; the web also hides the map in Firefox print).
- Rebuild: the map is torn down and rebuilt whenever the flights list, the segments list or the current user's `carto_api_key` changes (the key may arrive after first paint, so the tile layer is picked from the latest key; 96-103). Toggling the drag lock must NOT rebuild the map or reset camera and zoom; it only enables or disables dragging.

## API calls

- `GET /api/airports/{iata}` (airportsApi.get)

## Android notes

Use MapLibre Native or Google Maps Compose. To match the web tile source, use the OSM or keyed CARTO raster URLs above. Draw flight arcs by sampling a great-circle line into a polyline.

## iOS notes

Use MapLibre Native for iOS to match Android, or MapKit (`MKGeodesicPolyline` draws great circles natively). MapKit cannot use the CARTO or OSM raster tiles without an overlay.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- Maps (C12): not in base: add an `expect fun` map composable per platform (osmdroid or maps-compose on Android, MapKit on iOS); MapLibre, great-circle arcs and raster tile URLs have no sample ; copy [PeopleInSpace: `ISSMapView.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/ui/ISSMapView.kt); [PeopleInSpace: `ISSMapView.android.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/androidMain/kotlin/dev/johnoreilly/common/ui/ISSMapView.android.kt); [PeopleInSpace: `ISSMapView.ios.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/iOSMain/kotlin/com/surrus/common/ui/ISSMapView.ios.kt); [PeopleInSpace: `NativeISSMapView.swift`](https://github.com/joreilly/PeopleInSpace/blob/main/PeopleInSpaceSwiftUI/PeopleInSpaceSwiftUI/NativeISSMapView.swift)
- Platform adapters (C22): `expect`/`actual` like `PlatformHttpClient.*.kt` and `PlatformStoreFactory.*.kt`, small inputs and outputs (`SOFTWARE_PATTERNS.md` Adapter); one map composable per platform ; copy [PeopleInSpace: `ISSMapView.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/ui/ISSMapView.kt)
- HTTP client (C01): reuse the shared client in `backend-client/.../backend/client/Clients.kt` (`KtorAuthApi` style: one small API class per area); `GET /api/airports/{iata}` for each code ; copy [PeopleInSpace: `Koin.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/di/Koin.kt)
- Adapter (`SOFTWARE_PATTERNS.md`): the map takes plain lists of points and arcs, not trip models ; copy no sample

## Tests

- Map test: a trip with 2 flights between 3 resolved airports shows 3 airport markers and 2 arcs (one per flight, not lines between stops) and fits the camera to all points; a segment without coordinates is not drawn.
- Lookup test: each distinct IATA code of the trip is requested through `GET /api/airports/{iata}`; a failed lookup skips that airport without breaking the map.
- Hidden test: a trip with no flights and no segments does not show the map; flights whose airports all fail to resolve (and no drawable segments) produce no map.
- Tile test: with a `carto_api_key` the tile URL is the CARTO Voyager URL containing the URL-encoded key; without one it is the OSM URL.
- Segment colour test: a train segment with coordinates is a dashed green line with two end markers.
- Rebuild test: a late-arriving `carto_api_key` rebuilds the map with the CARTO layer; toggling the drag lock keeps camera and zoom.
- Attribution test: OSM tiles show the OpenStreetMap credit; CARTO tiles show the OSM and CARTO credits.
- Print test: the map is 260 px high with no attribution and no toggle.
- OSM-only test: with no `carto_api_key` the tile layer is the OpenStreetMap URL and no CARTO URL is ever requested (web test: "uses OpenStreetMap tiles only when no CARTO key is configured")
- CARTO key test: with the key `abc 123` the tile URL contains `rastertiles/voyager` and the query `?key=abc%20123` (the key is URL-encoded) (web test: "uses CARTO Voyager tiles with the key when one is configured")
- Pan toggle test: on a non-touch device the map starts pannable; pressing "Lock map" turns dragging off, pressing "Move map" turns it back on, and the map is created only once (no rebuild, so camera and zoom are kept) (web test: "turns dragging off and back on without rebuilding the map")
- Fallback test, one load: after one tile loads, ten failed tiles leave CARTO in place and OSM is never added (web test: "keeps CARTO when a few tiles drop but others load")
- Fallback test, burst: three failed tiles before any tile has loaded change nothing; OSM is not added (web test: "tolerates a burst of failures before any tile has loaded")
- Fallback test, blocked: four failed tiles with none loaded remove the CARTO layer once and add OSM once; six further failures do not add OSM again (web test: "falls back to OSM when every tile fails, as when CARTO is blocked")

## Native additions (not in web)

- Offline tile packs and a native map SDK key are native-only decisions; the web has neither.

## Depends on

- T-010
- T-001
