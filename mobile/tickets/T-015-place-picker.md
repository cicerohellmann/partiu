# T-015 Place and station search field

## Web source

- `frontend/src/components/PlaceInput.svelte`

## What it does

Web source line ranges: `PlaceInput.svelte` 1-161 (logic), 163-228 (markup). It is a controlled field: props `value` (name), `lat`, `lon`, `kind`, `placeholder`, and an `onchange(place)` callback. It has no permission gate.

- A text field with a dropdown of suggestions. Used by add transport (T-016), the segment editor (T-014), stays (T-022), car rentals (T-023), add and edit trip (T-020, T-021, kind `city`) and the people picker.
- `kind` is one of `train`, `bus`, `ferry`, `car`, `stay`, `city`. It selects the endpoint: `stay` calls `GET /api/places/search?q=` (accommodation and plain addresses); `city` calls `GET /api/cities/search?q=`; every other kind (including `car`) calls `GET /api/stations/search?q=...&kind={kind}`. The query is URL-encoded and trimmed.
- Result fields: `name`, `city`, `address`, `country`, `countrycode` (ISO alpha-2), `category` (`place` or `address`), `lat`, `lon`.
- Typing: every keystroke immediately calls `onchange({name: text, lat: null, lon: null, country_code: null, address: null})`, so coordinates, country and address are dropped as soon as the text is edited. Texts shorter than 3 characters (after trim) clear the results and close the dropdown without a request. Otherwise the search runs 300 ms after the last keystroke, using the trimmed text.
- Stale responses are ignored (a request counter); queries already answered are memoised per field instance, keyed by lower-cased text, and re-used without a request. There is no request cancellation.
- A spinner is shown while searching; when `lat` and `lon` are set a pin is shown (hover text depends on the kind: "Location found — this leg will show on the map" for station kinds, the stay or city wording otherwise).
- Dropdown: shown only when there is at least one result. Venues (`place`) are listed before streets (`address`), with an "Addresses" heading before the first street when it follows venues; relevance order is kept inside each group. Each row shows the name and a second line: for `city` and `car` kinds with category `place`, region (the result's `city`, omitted if equal to the name) plus country joined by ", "; for everything else the street address, or "city, country" when there is none.
- Choosing a result (click, or Enter on the highlighted row) calls `onchange({name, lat, lon, country_code: countrycode or null, address: address or null})` and closes the list. Keys act only while the list is open and has results (otherwise the key press is untouched); Enter with no row highlighted is not intercepted, so the surrounding form submits; typing resets the highlight to none. Arrow Down wraps past the last row to the first; Arrow Up from no highlight or from the first row goes to the last. Web bug (report upstream, do not copy): the web's arrow-key highlight index is applied to the unsorted `results` array, while the rows are drawn from the venues-first `grouped` list (`PlaceInput.svelte` 66-70, 146-155, 193, 201), so Enter can pick a different row than the highlighted one when street results come before venues in the server order. Arrow up and down move the highlight (wrapping), Escape closes, blur closes after 150 ms, focus reopens it when results exist. On pointer devices, hovering a row highlights it (same state as the keyboard highlight; PlaceInput 203). Not needed on touch.
- Duplicate points: every returned result gets its own row, even when several share an identical coordinate pair (the geocoder returns the same point under two labels, for example `Itaboraí` once with city `Itaboraí` and once with city `Rio de Janeiro`, both at -22.7496231, -42.8557428). Rows are keyed by their position in the list, not by coordinates (`PlaceInput.svelte:193`); keying on coordinates once crashed the whole screen behind the error boundary "This page didn't load." Native: never use latitude/longitude (or name) as the row identity; both rows are listed and both can be picked.
- Free text is allowed: the hint below the field reads "No station picked — saved as text, and left off the map." (station kinds), "Nothing picked — saved as plain text, and it won't count toward visited countries." (stay) or "No city picked — saved as text, with no country and no cover photo." (city) when the name is non-blank and there are no coordinates. The two hints share one slot (213-221): when the last search failed only the lookup-unavailable hint shows; the "saved as text" hint shows only when no search failure is pending, the trimmed name is non-empty and lat is null. A new search clears the failure flag; picking a result (coordinates set) or emptying the field hides the hint. The saved place then has null coordinates; the web does not geocode it later in this component.
- On a search error the results are emptied, the dropdown closes and the hint "Station lookup unavailable — you can still type the name." (stay and city: "Lookup unavailable — you can still type the name and address.") is shown; the typed text is kept and the form can still be saved.
- There is NO clear button.
- Locale keys for the field's feedback (`PlaceInput.svelte:179-219`): the spinner's accessibility label is `segments.searching` ("Searching stations…") for station kinds and `places.searching` ("Searching…") for stay and city; the pin's hover text is `segments.located` ("Location found — this leg will show on the map") or `places.located` ("Location found — this stay will show on the map and count toward visited countries"); the free-text hint is `segments.no_coords_hint` (station kinds), `places.no_coords_hint` (stay) or `cities.no_coords_hint` (city); the search-error hint is `segments.lookup_failed` (station kinds) or `places.lookup_failed` (stay and city). The texts are the ones quoted above; native uses the same keys per kind. The quoted texts are the exact `en.json` values (em dash U+2014; `en.json` 123, 706-712), and native must load them from the locale files (T-004), never retype them.

## API calls

- `GET /api/stations/search?q=&kind=` (stationsApi.search; kinds train, bus, ferry, car)
- `GET /api/places/search?q=` (placesApi.search; kind stay)
- `GET /api/cities/search?q=` (citiesApi.search; kind city)

## Android notes

Compose `ExposedDropdownMenu` with a debounced flow; ignore stale responses with a request counter (the web does not cancel requests).

## iOS notes

SwiftUI `searchSuggestions` or a custom list; ignore stale responses with a counter or `Task` cancellation.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- HTTP client (C01): reuse the shared client in `backend-client/.../backend/client/Clients.kt` (`KtorAuthApi` style: one small API class per area); `stations`, `places` and `cities` search ; copy [PeopleInSpace: `Koin.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/di/Koin.kt)
- ViewModel and UI state (C08): `SOFTWARE_PATTERNS.md` state machine (sealed interfaces, not booleans), `FlowState` in `core-data/.../AppFlowSupport.kt`, `composeApp/.../kmpstartup/FlowStateCard.kt`, androidx `ViewModel`; search state: Idle, Searching, Results, Error; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt); [FantasyPremierLeague: `PlayerListViewModel.kt`](https://github.com/joreilly/FantasyPremierLeague/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PlayerListViewModel.kt)
- Search debounce and stale-response handling (C29): `debounce` then `flatMapLatest` on the query flow, so an older response never replaces a newer one ; copy [FantasyPremierLeague: `PlayerListViewModel.kt`](https://github.com/joreilly/FantasyPremierLeague/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PlayerListViewModel.kt)
- Error mapping (C03): no HTTP-status mapping in base; add one mapper in `backend-client` (Ktor `HttpResponseValidator`) and show failures as a sealed `Error` UI state; enums for reasons as in `core-model/.../ConnectionDiagnostics.kt`; lookup unavailable hint ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt); [PeopleInSpace: `PeopleInSpaceRepository.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/repository/PeopleInSpaceRepository.kt)
- Unit tests (C20): `commonTest` in `core-data` (e.g. `SyncMergeTest.kt`) with `kotlin-test` and `kotlinx-coroutines-test`; fake HTTP with Ktor `MockEngine` (add); stale-response test ; copy no sample
- Adapter (`SOFTWARE_PATTERNS.md`): one `PlaceSearch` interface over the three endpoints ; copy no sample

## Native additions (not in web)

- Deliberate bug fix: Enter (and any keyboard or accessibility selection) picks the row that is highlighted on screen, i.e. the same item in the venues-first grouped list. Not the web behaviour; the web bug is to be reported upstream.

## Tests

- Short text test: typing 1 or 2 characters makes no request and closes the list.
- Debounce test: typing 5 characters quickly makes one request 300 ms after the last key, with the final trimmed text and the right endpoint and `kind` for the field.
- Typing test: each keystroke fires `onchange` with the text and null lat, lon, country_code and address.
- Selection test: choosing a result fires `onchange` with name, lat, lon, country code and address; the list closes.
- Grouping test: results with category `address` come after venues under an "Addresses" heading.
- Memo test: retyping an already searched text (any case) makes no second request.
- Stale test: a slow response for an earlier query does not replace the results of a later one.
- Error test: a failed search closes the list, shows the lookup-unavailable hint and keeps the typed text.
- Hint test: a non-blank name with no coordinates shows the "saved as text" hint for the field's kind.
- Hover test (pointer devices only): hovering a suggestion row gives it the same highlight as the arrow keys.
- Highlight test: with results [address A, venue B] (server order) the grouped list is [B, A]; ArrowDown once highlights B and Enter picks B.
- Key gating test: with the list closed or empty, arrow keys and Enter are not intercepted; Enter with nothing highlighted submits the form; typing resets the highlight.
- Hint precedence test: after a failed search only the lookup-unavailable hint shows, never both; a new search clears it; picking a result hides the hint.
- Locale string test: the hints are read from the locale files and contain an em dash.
- Duplicate coordinates test: two results with the same latitude and longitude produce two rows and no crash (web test: "renders results that share a coordinate pair without throwing").
- City endpoint test: with kind `city`, typing `Belém` calls the cities search with `Belém` (within the 300 ms debounce) and never the stations search (web test: "searches cities through the city endpoint").
- City label test: a city result named `Oslo` with region `Marshall`, country `United States` and address `Marshall` shows the second line `Marshall, United States`, not the address (web test: "labels a city with its region and country, not its address"); a result named `Oslo` with region `Oslo` and country `Norway` shows `Norway` only (web test: "drops the region from the label when it just repeats the name").
- Geocoder failure test: when the search fails the list is empty, the lookup-unavailable hint shows and the typed text stays (web test: "leaves what was typed in place when the geocoder fails").
- Web tests mirrored: frontend/src/components/PlaceInput.test.ts

## Depends on

- T-001
