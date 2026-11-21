# T-021 Edit trip

## Web source

- `frontend/src/pages/EditTripPage.svelte`

## What it does

Web source line ranges: `EditTripPage.svelte` 1-201 (logic), 203-300 (form). The page has no owner, collaborator, admin or demo check (the trip page decides who sees the link to it; the server enforces access).

- Screen `/trips/{id}/edit`, title "Edit Trip", back link to the trip. Load: `GET /api/trips/{id}` (`trip.loading` "Loading trip…" meanwhile, in a placeholder block, `EditTripPage.svelte:207`; a failure shows the error message in red and no form).
- Prefill: name, start date and end date (empty when null), origin (`origin_place`, `origin_lat`, `origin_lon`, `origin_country`) and the destination list (name, lat, lon, country code each); with no stored destinations one empty row is shown. Edit order is Info (name), Dates (start, end), Route (origin, destinations, hint); Add Trip (T-020) order is Info, Route, Dates; keep each screen's own order. The form has the same fields and controls as add trip (T-020): name (required as the browser sees it: a name of only spaces passes, is trimmed to an empty string and sent, and the server decides; placeholder `add_trip.name_placeholder`), dates, origin and destinations pickers (kind `city`, add and remove destination), route hint. "+ Add destination" appends an empty row and typing in it simply stores the typed text as that row's place (name only, no coordinates), exactly like the rows loaded from the trip; it must never fail or blank the screen (the web had a crash here once, so keep the test).
- Seeding from flights: after load, if the origin name is empty and the trip has an `origin_airport`, the origin is filled from `GET /api/airports/{iata}` (city name trimmed at the first "(" or ",", falling back to the IATA code; with the airport's coordinates and country code). Likewise, if none of the destinations has a name and the trip has a `destination_airport`, the destination list becomes that one place. A failed lookup leaves the field empty. When at least one was filled, the hint `trips.route_seeded` ("Filled in from this trip’s flights — save to keep it.") is shown. Nothing is saved unless the user saves.
- Span warning (advisory, never blocks): the page computes the earliest and latest local date of the trip's flights (departure and arrival dates in each airport's timezone, from the trip data), ground segments (`GET /api/trips/{id}/segments`, dates in each place's timezone) and stays (`GET /api/trips/{id}/stays`, the stored check-in and check-out dates); a failed segments or stays request counts as none. The warning shows only when BOTH a content start and a content end exist (at least one dated flight, leg or stay) AND ((a start date is typed AND it is later than the earliest content date) OR (an end date is typed AND it is earlier than the latest content date)); a blank date field never triggers it (`EditTripPage.svelte` 45-51, 168-169). Dates compare as `YYYY-MM-DD` strings and the warning re-evaluates live as the dates are edited. The earliest value is the minimum over all departure dates and stay check-ins, the latest the maximum over all arrival dates and stay check-outs. The warning "This trip has legs running from {start} to {end}, so it will keep covering those dates. Remove or move the leg to shorten the trip." is shown. There is NO end-before-start validation. {start} and {end} are the raw `YYYY-MM-DD` keys of the earliest and latest content date (not localised). The hint `edit_trip.span_held_by_legs` is shown in a yellow warning box above the buttons; it never blocks Save.
- Save ("Save Changes", "Saving…" and disabled while sending) always sends the whole form: `PATCH /api/trips/{id}` with `{name (trimmed), start_date (null when empty), end_date (null when empty), origin: {name, lat, lon, country_code}, destinations: [...non-blank]}`. The body never contains `booking_refs`, `origin_airport` or `destination_airport`: this screen has no airport or booking-reference field, so the trip-level booking references and the derived airport pair stay exactly as the server holds them (`EditTripPage.svelte:182-198`; the seeding above only fills the form's city fields, it never sends an airport). Then the app returns to the trip.
- A server or network error is shown in red above the buttons. Cancel is a plain link back to the trip; there is NO unsaved-changes confirmation.

## API calls

- `GET /api/trips/{id}` (tripsApi.get)
- `PATCH /api/trips/{id}` (tripsApi.update)
- `GET /api/airports/{iata}` (airportsApi.get; only for seeding the route)
- `GET /api/trips/{id}/segments` (segmentsApi.list; for the span warning)
- `GET /api/trips/{id}/stays` (staysApi.list; for the span warning)
- `GET /api/cities/search?q=` (via the place picker, T-015)

## Android notes

Same as shared code.

## iOS notes

Same as shared code.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- ViewModel and UI state (C08): one ViewModel exposing a sealed UI state, not booleans (`SOFTWARE_PATTERNS.md`; `FlowState` in `core-data/.../AppFlowSupport.kt`) with a form state (fields, saving, error) and one save event ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt)
- Date, time and time zone (C17): `kotlinx-datetime` in `core-model` (`Instant` in `Sync.kt`); add zone-aware helpers in `core-model`; span warning from flight dates ; copy [FantasyPremierLeague: `GameFixture.kt`](https://github.com/joreilly/FantasyPremierLeague/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/model/GameFixture.kt)
- Repository (`SOFTWARE_PATTERNS.md`): `TripRepository` hides the API calls (get, update, segments, airport); the screen never calls Ktor
- JSON models (C02): `@Serializable` data classes in `core-model` (`Trip` PATCH body); `Json { ignoreUnknownKeys = true }` already set in `PlatformHttpClient.android.kt` ; copy [PeopleInSpace: `PeopleInSpaceApi.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/remote/PeopleInSpaceApi.kt)

## Tests

- Prefill test: the form shows the stored name, dates, origin and destinations; with no stored destinations one empty row is shown.
- Seed test: a trip with an empty origin and an `origin_airport` fills the origin from the airport's city, shows the "Filled in from this trip's flights" hint, and does not overwrite a typed origin.
- Save test: saving sends one `PATCH /api/trips/{id}` with the whole body (name, dates with null for empty, origin, non-blank destinations), then returns to the trip.
- Span warning test: moving the end date earlier than the last leg or stay shows the warning but still allows saving.
- Error test: a failed load shows the error and no form; a failed save shows the message.
- Order test: the edit screen shows Info, Dates, Route in that order (add trip: Info, Route, Dates).
- Span text test: the warning shows raw date keys such as "2026-03-31 to 2026-04-01".
- Warning condition test: with no dated content, or with the date fields blank, no warning shows; a start date after the earliest content date alone, or an end date before the latest alone, shows it, and clearing the field hides it.
- Blank name test: a whitespace-only name is trimmed and sent as an empty string; the server's answer is shown.
- Load states test: while `GET /api/trips/{id}` is pending the screen shows the placeholder "Loading trip…" (`trip.loading`) and no form (web test: "shows loading state before trip loads"); a failing load shows its message ("Not found") and no form (web test: "shows load error when tripsApi.get fails"); after loading, the name field holds "Tokyo 2025" (web test: "renders form with trip data after loading").
- Prefill and links test: the two date inputs hold "2025-03-01" and "2025-03-14" (web test: "renders two date inputs pre-filled"); the Cancel link goes to `/trips/trip-99`, the trip itself (web test: "cancel link points back to the trip").
- Save body test: editing the name to "Tokyo 2025 Updated" sends `PATCH /api/trips/trip-99` with that name (web test: "calls tripsApi.update with edited name on submit"); the request body has no `booking_refs` (web test: "leaves the trip-level booking references alone") and no `origin_airport` (web test: "leaves the derived origin alone when saving"); the screen shows no airport field at all (web test: "offers no airport fields at all"); a successful save opens `/trips/trip-99` (web test: "navigates back to trip detail on success"); a failed save ("Save failed") shows that message (web test: "shows error message when update fails").
- Route prefill test: a trip with `origin_place` "Florianópolis" and destinations São Paulo and Rio de Janeiro shows three city fields with those values in that order; saving unchanged sends `origin: {name: "Florianópolis", ...}` and `destinations` São Paulo (with `country_code` "BR") then Rio de Janeiro (web test: "pre-fills the typed ends and sends them back as places"); adding a destination row and typing "Belém" keeps "Belém" in that field and the screen stays usable (web test: "accepts typing in a new destination row").
- Span warning test: with a car leg held in the trip (13 March 08:00 to 14 March 09:00 São Paulo time, stored as UTC) and the end date changed from 2025-03-14 to 2025-03-13, the yellow warning appears, naming the content dates 2025-03-13 and 2025-03-14 (web test: "warns, naming the dates the legs hold"); with the original dates covering the leg no warning shows (web test: "does not warn while the dates still cover every leg"); saving with the warning showing still sends the PATCH (web test: "never blocks the save"); when the segments request fails there is no warning (web test: "says nothing when the leg lookup fails").
- Seed from flights test: a trip with no typed origin or destinations, `origin_airport` "GRU", and an airport lookup answering city "São Paulo", country "BR", latitude -23.43 fills the first field with "São Paulo" and a save sends `origin: {name: "São Paulo", country_code: "BR", lat: -23.43, ...}` (web test: "fills the cities in from the airports"); the hint `trips.route_seeded` is then shown (web test: "says where the values came from"); a trip that already has typed places keeps "Florianópolis", makes no airport lookup and shows no seeded hint (web test: "never overwrites what the traveller already typed"); when the airport lookup fails the field stays empty and never shows the IATA code (web test: "leaves the field empty when the airport is unknown").
Web tests mirrored: frontend/src/pages/EditTripPage.test.ts

## Depends on

- T-010
- T-020
