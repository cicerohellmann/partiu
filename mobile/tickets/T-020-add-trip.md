# T-020 Add trip

## Web source

- `frontend/src/pages/AddTripPage.svelte`

## What it does

Web source line ranges: `AddTripPage.svelte` 1-60 (logic), 62-149 (form). The page has no owner, admin or demo check; the server enforces access.

- Screen `/trips/new`, title "New Trip", back link to the trip list. Sections: Trip Info, Route, Dates.
- Trip name: required (browser validation, star), autofocused, placeholder `add_trip.name_placeholder` ("Paris — June 2025"; the edit screen reuses the same key, T-021). It is the only required field. Required means non-empty only as the browser sees it: a name of only spaces passes, is trimmed to an empty string and sent; the server decides (native may instead block a blank name, see Native additions).
- Route: "Origin" (one place picker, kind `city`, placeholder "City or town") and "Destinations" (a list of place pickers, kind `city`; each destination picker has the placeholder `trips.destination_placeholder`, English "City or town", the same text as the origin placeholder; `AddTripPage.svelte` 104). The destination list starts with one empty row; each row has an "x" remove button (aria "Remove destination") shown only when there is more than one row; "+ Add destination" appends an empty row. Hint: "Where the trip starts and ends. The destination also chooses the cover photo." The place picker (T-015) shows its own "saved as text" hint when nothing is picked.
- Dates: exactly two optional date inputs, Start date (`add_trip.start_date`) and End date (`add_trip.end_date`), both empty on open. There is NO check that the end is not before the start, and no inline date error; whatever is entered is sent and any server error is shown.
- Submit ("Create Trip", `add_trip.saving` "Creating…" and disabled while sending): `POST /api/trips` with `{name (trimmed), start_date (omitted when empty), end_date (omitted when empty), origin: {name (trimmed), lat, lon, country_code}, destinations: [{name, lat, lon, country_code}, ...]}`. The origin object is always sent, even with an empty name and null coordinates; destinations with a blank name are filtered out (so an untouched form sends an empty array). The place `address` is not sent. The body never contains `booking_refs`, `origin_airport` or `destination_airport`, and the screen has no airport picker and no booking-reference field: the airport pair is derived by the server from the trip's flights (a trip made by hand has none until a flight is added) and a booking reference is typed on the leg it belongs to, not on the trip (`AddTripPage.svelte:35-45`, web tests lock this in). The "Route" section therefore holds exactly two city pickers on first open: the origin and the first destination row. The response is `{id}` and the app opens `/trips/{id}` (T-010).
- A server or network error message is shown in red above the buttons and the form stays. Cancel is a plain link to the trip list.
- Trips are normally created automatically when a flight email is received (T-009); this screen is for manual trips.

## API calls

- `POST /api/trips` (tripsApi.create)
- `GET /api/cities/search?q=` (via the place picker, T-015)

## Android notes

Same as shared code. Use the Material date range picker.

## iOS notes

Same as shared code. Use the system date picker.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- ViewModel and UI state (C08): one ViewModel exposing a sealed UI state, not booleans (`SOFTWARE_PATTERNS.md`; `FlowState` in `core-data/.../AppFlowSupport.kt`) with a form state (fields, saving, error) and one save event ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt)
- Date, time and time zone (C17): `kotlinx-datetime` in `core-model` (`Instant` in `Sync.kt`); add zone-aware helpers in `core-model`; two optional dates ; copy [FantasyPremierLeague: `GameFixture.kt`](https://github.com/joreilly/FantasyPremierLeague/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/model/GameFixture.kt)
- JSON models (C02): `@Serializable` data classes in `core-model` (`POST /api/trips` body); `Json { ignoreUnknownKeys = true }` already set in `PlatformHttpClient.android.kt` ; copy [PeopleInSpace: `PeopleInSpaceApi.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/remote/PeopleInSpaceApi.kt)

## Native additions (not in web)

- Optional: block a blank (whitespace-only) trip name before submitting.

## Tests

- Required test: with an empty name the form cannot be submitted.
- Create test: a valid form sends one `POST /api/trips` with the trimmed name, `origin` and `destinations` (blank rows dropped, coordinates and country code of picked cities, null for typed text), and omits the dates that were left empty; the app then opens the new trip.
- Destinations test: a second row can be added; the remove button appears only with two or more rows and removes that row.
- Error test: a failed request shows the error message and keeps the entered values.
- Blank name test: a name of only spaces is trimmed to an empty string and still submitted; the server's answer is shown.
- Destination placeholder test: each destination row shows "City or town".
- Form layout test: the screen shows a required trip name field (web test: "renders form with required name field"), exactly two date inputs (web test: "renders two date inputs"), a submit button (web test: "renders submit button") and a Cancel link to the trip list `/trips` (web test: "renders cancel link pointing to /trips").
- Route fields test: the screen offers exactly two city pickers on open (origin and the first destination) and no airport picker (web tests: "does not ask for a route", "asks for the ends as cities, not airports"); a typed origin "Florianópolis" and destination "São Paulo" are sent as `origin: {name: "Florianópolis", ...}` and `destinations: [{name: "São Paulo", ...}]` (web test: "sends the typed ends as places").
- Create body test: a name typed as "  Paris 2025  " is sent trimmed as "Paris 2025" in `POST /api/trips` (web test: "calls tripsApi.create with trimmed name on submit"); the request body has no `booking_refs` field and the screen shows no booking-reference field (web test: "does not ask for booking references").
- Destinations rows test: with two rows added (three destination rows), "São Paulo" typed in the first, "Rio de Janeiro" in the second and the third left empty, the body's `destinations` lists only the non-blank rows in order, São Paulo then Rio de Janeiro (web test: "collects several destinations and drops the blank rows"); after adding a second row there are two rows and tapping the first row's remove button leaves one (web test: "can remove a destination row").
- Create result test: a failing request (message "Server error") shows that message and keeps the form (web test: "shows error message when API fails"); a successful request answering `{id: "new-trip-id"}` opens `/trips/new-trip-id` (web test: "navigates to new trip on success").
Web tests mirrored: frontend/src/pages/AddTripPage.test.ts

## Depends on

- T-009
