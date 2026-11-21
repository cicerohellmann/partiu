# T-028 History of past trips

## Web source

- `frontend/src/pages/HistoryPage.svelte` (script 1-99, markup 101-153)
- `frontend/src/lib/utils.ts` lines 254-267 (`inferTripStatus`)
- `frontend/src/App.svelte` lines 32-35 (routes `/history`, `/history/:id` is the shared trip detail page)
- Server side of the search index: `backend/trips/service.py` (`search_index` built in the list enrichment, lowercased and accent-stripped)

## What it does

- Screen `/history` with the top bar title string `history.title` (English "◷ History", with the glyph) and no back button. No permission gate: every signed-in user sees it, and it lists owned and accepted shared trips as returned by `GET /api/trips`.
- Loads `GET /api/trips` and `GET /api/settings` in parallel; a settings failure is ignored (Immich just counts as not configured). Only a trips failure shows the error state.
- A trip is "completed" by `inferTripStatus`, computed on the device from dates, not from any server status: it has an `end_date` and the start of the day after `end_date` (local time) is already in the past. A trip with no end date is never completed. Ongoing and upcoming trips are not shown.
- Order: the API list order reversed (the server orders by start date ascending, so newest start first). The page does no sorting of its own.
- Cards: the same `TripCard` as T-009 with status "completed", a "Completed" badge, star rating row (`showStars`), cover image with a refresh-on-error fallback, link to `#/history/{id}` (the trip detail page).
- Immich: when settings have `immich_url` and `immich_api_key_set`, each card gets an album button at the bottom (open the album if `immich_album_id` is set, otherwise create one with `POST /api/trips/{id}/immich-album`; see T-010; the Immich setting itself is T-033). After creation only that list item's `immich_album_id` is updated (no refetch). The button on a card sits in the card footer, full width, small font. Button behaviour (`ImmichAlbumButton.svelte:12-90`): one secondary button, disabled while creating or checking; label `immich.creating_album` ("Creating album…") while busy, `immich.open_album` ("Open Immich Album ↗") when an album id exists, else `immich.create_album` ("Create Immich Album"). Click calls preventDefault and stopPropagation so the surrounding card link does not navigate. Deep-link fallback: set `immich://album?id=<id>`, wait 1500 ms; if the page became hidden (visibilitychange: the Immich app took over) cancel the fallback, otherwise open `<base>/albums/<id>` in a new tab with noopener, where `<base>` is `immich_url` with trailing slashes removed. A create error shows as small red text under the button and is cleared on the next click.
- Search box (a sticky `type=search` input shown only when there is at least one completed trip), placeholder `history.search_placeholder` ("Search by trip, airport or booking ref…"). The query is trimmed, lowercased and accent-stripped (NFD, diacritics removed). A trip matches when:
  1. its `search_index` (server-built string; falls back to the normalised trip name when absent) contains the query as a substring; or
  2. the query is a prefix of a key in the page's built-in `COUNTRY_CODES` map (`HistoryPage.svelte:14-45`, 133 entries: lower-case English country name or alias to lower-case ISO 2-letter code; the complete table is listed below the search bullet; multi-word keys such as `costa rica` or `new zealand` are tested as whole strings with `name.startsWith(needle)`) AND the trip's index, split on whitespace, contains that country's 2-letter code as a whole token. So "ital" finds a trip with token "it", but the code "it" is not matched as a substring of other words by this rule.
  An empty (or whitespace-only) query shows all completed trips. The match is case-insensitive: "Rome", "NRT" and "RM001" typed in capitals find the trips whose index holds `rome`, `nrt` and `rm001` (`HistoryPage.svelte:84-95`). A whole country name can also match more than one trip at once: "brazil" matches every trip whose index has the token `br`.

  The complete `COUNTRY_CODES` table (`HistoryPage.svelte:14-45`, 133 entries):

  ```
  // Country name → ISO 2-letter code (lowercase). Lets users type "italy" and
  // match country_code "it" stored in the search_index.
  const COUNTRY_CODES: Record<string, string> = {
    "afghanistan":"af","albania":"al","algeria":"dz","angola":"ao","argentina":"ar",
    "armenia":"am","australia":"au","austria":"at","azerbaijan":"az","bahrain":"bh",
    "bangladesh":"bd","belarus":"by","belgium":"be","bolivia":"bo","bosnia":"ba",
    "botswana":"bw","brazil":"br","brasil":"br","bulgaria":"bg","cambodia":"kh",
    "cameroon":"cm","canada":"ca","chile":"cl","china":"cn","colombia":"co",
    "costa rica":"cr","croatia":"hr","cuba":"cu","cyprus":"cy","czech":"cz",
    "czechia":"cz","denmark":"dk","dominican republic":"do","ecuador":"ec",
    "egypt":"eg","el salvador":"sv","ethiopia":"et","finland":"fi","france":"fr",
    "georgia":"ge","germany":"de","ghana":"gh","greece":"gr","guatemala":"gt",
    "haiti":"ht","honduras":"hn","hungary":"hu","iceland":"is","india":"in",
    "indonesia":"id","iran":"ir","iraq":"iq","ireland":"ie","israel":"il",
    "italy":"it","jamaica":"jm","japan":"jp","jordan":"jo","kazakhstan":"kz",
    "kenya":"ke","kuwait":"kw","latvia":"lv","lebanon":"lb","libya":"ly",
    "lithuania":"lt","luxembourg":"lu","malaysia":"my","maldives":"mv","malta":"mt",
    "mauritius":"mu","mexico":"mx","moldova":"md","montenegro":"me","morocco":"ma",
    "mozambique":"mz","myanmar":"mm","namibia":"na","nepal":"np","netherlands":"nl",
    "new zealand":"nz","nicaragua":"ni","nigeria":"ng","norway":"no","oman":"om",
    "pakistan":"pk","panama":"pa","paraguay":"py","peru":"pe","philippines":"ph",
    "poland":"pl","portugal":"pt","qatar":"qa","romania":"ro","russia":"ru",
    "rwanda":"rw","saudi arabia":"sa","senegal":"sn","serbia":"rs","singapore":"sg",
    "slovakia":"sk","slovenia":"si","somalia":"so","south africa":"za",
    "south korea":"kr","spain":"es","sri lanka":"lk","sudan":"sd","sweden":"se",
    "switzerland":"ch","syria":"sy","taiwan":"tw","tanzania":"tz","thailand":"th",
    "tunisia":"tn","turkey":"tr","turkiye":"tr","uganda":"ug","ukraine":"ua",
    "united arab emirates":"ae","uae":"ae","emirates":"ae","united kingdom":"gb",
    "uk":"gb","britain":"gb","england":"gb","united states":"us","usa":"us",
    "america":"us","uruguay":"uy","uzbekistan":"uz","venezuela":"ve","vietnam":"vn",
    "zimbabwe":"zw",
  ```
- States: loading (`history.loading`, "Loading history…"); error with title "Failed to load history", the error message and a Retry button that reloads; no completed trips at all: "No past trips" / "Completed trips will appear here." (no search box); completed trips but no match: "No trips match your search" / "Try a different keyword." (search box stays).

## API calls

- `GET /api/trips` (tripsApi.list) returns `{ trips: Trip[] }`; the page uses `data.trips`
- `GET /api/settings` (settingsApi.get), only for `immich_url`, `immich_api_key_set` (failure ignored)
- `POST /api/trips/{id}/immich-album` (tripsApi.createImmichAlbum), only from the album button; see T-010

## Android notes

Same as shared code.

## iOS notes

Same as shared code.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- ViewModel and UI state (C08): one ViewModel exposing a sealed UI state, not booleans (`SOFTWARE_PATTERNS.md`; `FlowState` in `core-data/.../AppFlowSupport.kt`) with a search query state ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt)
- Offline cache (C04): `core-data` KStore repositories (`KStoreRepositories.kt`, `StoreFactory.kt`) fit the completed trips for offline reading; for many rows or queries add a SQL database ; copy [PeopleInSpace: `PeopleInSpace.sq`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/sqldelight/com/dev/johnoreilly/peopleinspace/PeopleInSpace.sq) (SQLDelight) if SQL is chosen
- Date, time and time zone (C17): `kotlinx-datetime` in `core-model` (`Instant` in `Sync.kt`); add zone-aware helpers in `core-model`; completed status is inferred on the device from dates (`inferTripStatus`, T-008) ; copy [FantasyPremierLeague: `GameFixture.kt`](https://github.com/joreilly/FantasyPremierLeague/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/model/GameFixture.kt)
- Repository (`SOFTWARE_PATTERNS.md`): `TripRepository` (shared with T-009) supplies the list; the search filter and `COUNTRY_CODES` map are pure functions

## Tests

- Filter test: given one ongoing, one upcoming and two completed trips (end date before today), only the two completed ones show, in reverse API order.
- Boundary test: a trip whose `end_date` is today is not completed; one that ended yesterday is. A trip with a start date but no end date is not completed.
- Search test: the query is matched against `search_index` (name, airport codes, city and country names, booking refs); "lis" matches an index containing "lis"; a query with an accent ("sao" or "são") matches an index holding the normalised "sao paulo"; surrounding whitespace is trimmed.
- Country test: "ital" matches a trip whose index has the token "it"; it does not match a trip that only contains "it" inside another word.
- Empty test: no completed trips shows "No past trips" and no search box; a query with no hits shows "No trips match your search".
- Error test: a failing `GET /api/trips` shows the error with Retry; Retry reloads. A failing `GET /api/settings` still shows the list.
- Immich test: the album button is shown on each card only when settings report Immich as configured.
- Title test: the top bar shows "◷ History" in English and has no back button.
- Immich click test: tapping the button on a card does not open the trip; after creating an album only that card changes label to "Open Immich Album ↗".
- Alias test: "uae", "emirates" and "united arab" all match a trip whose index has the token `ae`; "brasil" and "brazil" both match token `br`; the table has exactly 133 entries.
- Loading test: while `GET /api/trips` and `GET /api/settings` have not answered, the loading screen with "Loading history…" is shown (web test: "shows loading screen initially").
- Card test: one completed trip "Rome 2024" (2024-05-01 to 2024-05-10) appears as a card with its name (web test: "renders completed trip card").
- No-trips test: the server returns an empty list: "No past trips" is shown (web test: "shows empty state when no completed trips exist").
- Upcoming-only test: the server returns one trip dated 2099-01-01 to 2099-01-10: the same "No past trips" screen is shown (web test: "shows empty state when all trips are upcoming").
- Load error test: `GET /api/trips` fails with "Load failed": that message is shown under "Failed to load history" (web test: "shows load error when API fails").
- No Immich test: settings with no `immich_url` and `immich_api_key_set` false: no card has an Immich button (web test: "does not show Immich button when Immich is not configured").
- Create button test: settings with `immich_url` "https://immich.local" and the key set, and a trip with no album: the card shows "Create Immich Album" (web test: "shows Create Immich Album button when Immich is configured").
- Open button test: same settings and the trip has `immich_album_id` "album-abc": the card shows "Open Immich Album ↗" (web test: "shows Open Immich Album button when album already exists").
- Create request test: tapping "Create Immich Album" sends `POST /api/trips/trip-1/immich-album` (web test: "calls tripsApi.createImmichAlbum when Create button is clicked").
- Link test: the card for trip `trip-1` opens the history trip detail route `/history/trip-1` (web: href `#/history/trip-1`) (web test: "card links point to /history/:id").
- Search box test: with at least one completed trip the search box is shown (web test: "renders search input when trips are loaded").
- Name search test: trips "Rome 2024" and "Tokyo 2023"; typing "Rome" shows only Rome 2024 (web test: "filters trips by name using search_index").
- Airport search test: typing "NRT" shows only Tokyo 2023, whose index holds `nrt` (web test: "filters trips by destination airport using search_index").
- Booking ref search test: typing "RM001" shows the Rome trip, whose `booking_refs` is `["RM001"]` and whose index holds `rm001` (web test: "filters trips by booking reference using search_index").
- Country name test: typing "italy" shows only the Rome trip (index token `it`), not Tokyo (web test: "filters by country name — "italy" matches country code "it" in search_index").
- Country prefix test: typing "ital" shows only the Rome trip (web test: "partial country name prefix — "ital" matches Italy trips").
- Trim test: typing "  italy  " (spaces around) gives the same result as "italy" (web test: "trims whitespace from query before matching").
- Whole-token test: typing "brazil" shows both trips, because both indexes hold the whole token `br`; the code is matched as a token, never as a part of a longer word (web test: "country code token-match does not cause false positive on substring").
- Accent test: typing "São" shows the trip whose index is "sao paulo 2022 gru cgb sao paulo br" and hides "Dublin 2022" (web test: "diacritic in query matches normalized search_index").
- No-match test: typing "ZZZNOMATCH" shows "No trips match your search" and the search box stays (web test: "shows no-results state when search_index has no match").
- Clear test: after a query with no match, emptying the box shows the trip again (web test: "shows all trips when query is cleared").
Web tests mirrored: frontend/src/pages/HistoryPage.test.ts

## Depends on

- T-009
