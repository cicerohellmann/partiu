# T-017 Flight detail

## Web source

- `frontend/src/pages/FlightDetailPage.svelte`

## What it does

Web source line ranges: `FlightDetailPage.svelte` 1-250 (logic), 250-345 (hero), 345-400 (detail grid, email source), 400-560 (notes, maps, boarding passes), 560-640 (actions), 640-741 (modals). Helpers: `lib/utils.ts` `seatMapUrl` 269-276, `cabinLabel` 165-173.

- Screen `/trips/{tripId}/flights/{flightId}` and the `/history/{tripId}/flights/{flightId}` variant (the base path decides the back link, edit link and the post-delete destination). Title `{dep} → {arr}` with the real arrow U+2192; a missing airport code is shown as `?` (for example `? → LIS`) (`FlightDetailPage.svelte` 218), or "Loading flight…". Back goes to the trip (or the trip list when there is no trip id).
- Load: `GET /api/flights/{flightId}`. Loading shows a loading screen; a failure shows "Failed to load flight" (warning-sign icon) with the error message and a Back button. The same screen is shown when the request succeeded but returned no flight; the description is then the literal "Unknown error" (FlightDetailPage 258-264). Back goes to the trip, or to the list when there is no trip id. After the flight loads, three requests start in parallel and fail silently: the aircraft lookup, `GET /api/airports/{iata}` for departure and arrival, and `GET /api/flights/{id}/boarding-passes`.
- Hero card: airline code badge, flight number, status badge (the flight's `status`, default `flight.status_upcoming`, "upcoming"; the badge and the detail-grid status value are printed as `$t(flight.status)`, see Native additions for the web bug this causes; `FlightDetailPage.svelte` 280, 471). Departure and arrival columns with IATA code, local time in the airport timezone, long date (the arrival date only when it differs from the departure date), timezone line, "Terminal X" and "Gate X" when set; duration between them when known. The long date under each time (`formatDateLong`, FlightDetailPage 222-224, 290, 334; `lib/utils.ts` 73) takes NO time zone, so it is the calendar date in the device zone, unlike the time, which is in the airport zone. The "arrival date only when it differs" test compares these two device-zone strings. A native build using airport-local dates will differ from the web on red-eye flights; decide and note it. The timezone line (293-301, 337-345) is a muted small line showing `formatTimezone(iso, tz)` (short zone name such as `GMT+1`, en-GB style, see T-008); if that returns null the raw IANA string (e.g. `America/Sao_Paulo`) is shown; the line is hidden when the flight has no timezone for that end. The title shows `?` for a missing departure or arrival code. Status dot on the hero badge: completed = success, cancelled = danger, ongoing = accent, otherwise neutral.
- Aircraft line: if the flight already has `aircraft_type`, it is shown as `✈ {type}` (U+2708 and a space, for example `✈ Boeing 737`) followed by the registration in brackets `({registration})` only when one exists (`FlightDetailPage.svelte:364-374`), without any request. If not: when the arrival time is already in the past, "Aircraft type not available" with no request; otherwise "Looking up aircraft…" while `GET /api/flights/{id}/aircraft` runs, then the type name (and registration) when `type_name` is returned, else "Aircraft type not available". The response has only `type_name` and `registration`; there is no photo.
- Banners (first match wins): Cancelled (from the status or live status), Diverted, Incident, "Delayed N min" for a positive live departure delay (plus "Arr. delayed N min" when the arrival delay differs), or "On time" when live data was fetched and status is scheduled or active with no delay. Separately, a rescheduled flight shows "Rescheduled by the airline on {date}. Previously departed {day-month time} and arrived {day-month time}.", or, when only a schedule change notice exists, "The airline announced a schedule change for this booking on {date} without listing the new times. Check its email or app." In both, `{date}` is `formatDayMonth(rescheduled_at)` (day and short month, no year, app locale). Previous departure is `formatDayMonth(rescheduled_from_departure)` + a space + `formatTime(rescheduled_from_departure, departure_timezone)`; previous arrival is the same with `rescheduled_from_arrival` and `arrival_timezone` (each in its own airport's zone, 24 h `HH:mm`). The schedule-change notice `{date}` is `formatDayMonth(schedule_change_notice_at)` (405-422). Both use the warning (delayed) style. Banner colours carry meaning (`app.css` 1280-1303): Cancelled = danger (red) tint and border; Diverted, Incident, Delayed, Rescheduled and schedule-change = warning (amber); On time = success (green). Unlike the list row, the detail banners are not suppressed for completed flights.
- Detail grid, each item only when present: airline (name or code), flight number, booking reference (shown exactly as stored, in the monospace style, `FlightDetailPage.svelte:438-442`), passenger (shown exactly as stored, for example `JOHN DOE`, `444-448`), seat, class (economy, premium economy, business or "First Class"; unknown values shown as is), duration, status. Then the "Email Source" block, shown only when `email_subject` is set (`FlightDetailPage.svelte` 477-490): the subject is always shown inside it, and the date line `formatDateLong(email_date)` only when `email_date` is set, so a flight with a subject and no date shows the subject only. Notes card when `notes` is set. There is no distance field.
- Airport maps: when an airport has latitude and longitude, a button `🗺 Departure Airport Map — {code}` (`flight.dep_map`; arrival is `flight.arr_map`; the dash is an em dash, U+2014) toggles an embedded OpenStreetMap iframe (bounding box of 0.009 degrees around the airport with a marker) and the caption `{IATA} — {airport name}` followed by `, {city}` only when the city is set (em dash U+2014 with spaces, `FlightDetailPage.svelte` 507, 533). The iframe title is `{airport name} map`.
- Boarding passes: a section on this page lists the flight's passes (see T-018).
- Seat map: the "View Seat Map" button is shown only when the flight row itself has `aircraft_type` (stored value; `const mapUrl = seatMapUrl(flight?.aircraft_type)`, FlightDetailPage 200, 608). A type that arrives later from the lazy `GET /api/flights/{id}/aircraft` lookup is shown in the aircraft line but does NOT make the button appear (the web does not re-read the flight). The button opens `https://flightseatmap.com/aircraft/{slug}-seat-map` in a new tab, where the slug is the lower-cased type with every run of non-alphanumeric characters replaced by "-" and edge dashes trimmed.
- View raw email: a button (shown for everyone, disabled while loading) calls `GET /api/flights/{id}/email`; on failure an alert "Could not load email: {message}" is shown. On success a full-screen dialog opens with the subject (or "Raw Email") in the header and a close button; the body is the `html_body` in a sandboxed iframe (`sandbox="allow-same-origin"`, no scripts), or, when there is no HTML body, the text "No HTML body available for this flight." Tapping outside closes it.
- Owner gate: Edit, "Move to New Trip" and "Delete Flight" are shown only when `flight.user_id` equals the current user's id (string comparison). Collaborators, other users and admins who are not the flight's owner see only the seat map and raw email buttons. "Move to New Trip" additionally requires the flight to have a `trip_id`. There is no demo-specific check on this page.
- Edit: link to the edit screen (T-019).
- Move to New Trip: browser confirm "Move this flight to its own new trip?", then `POST /api/flights/{id}/ungroup` (no body); the response `{trip_id}` is opened (`#/trips/{trip_id}`). The button shows "…" while running; errors are shown as an alert.
- Delete: a confirmation dialog "Move this flight to the trash? You can restore it from Settings." with a red "Delete Flight" button; then `DELETE /api/flights/{id}` and the app goes to `#/{basePath}/{tripId}`, or to `#/{basePath}` (the list) when the route has no trip id (194-208). The confirm dialog closes after the request whether it succeeded or failed, and the page's Delete button is disabled while the request runs. The dialog's Cancel label is the fixed English text "Cancel" (not translated on the web); native should translate it. Errors are shown as an alert. (The trash is T-034.)
- `GET /api/flights` (the full list) is defined in the web client but no screen calls it.
- Locale keys for the states above: the loading text and title are `flight.loading` ("Loading flight…"); the aircraft line while the lookup runs is `flight.aircraft_loading` ("Looking up aircraft…"); the delay banner is `flight.live_delay_dep` ("Delayed {minutes}min") plus `flight.live_delay_arr` ("Arr. delayed {minutes}min"); the rescheduled banner is `flight.rescheduled_banner` ("Rescheduled by the airline on {date}. Previously departed {dep} and arrived {arr}.", `FlightDetailPage.svelte:407`). The airport map buttons are `flight.dep_map` / `flight.arr_map` ("🗺 Departure Airport Map — {code}" / "🗺 Arrival Airport Map — {code}"). The seat map button is `flight.seat_map` ("💺 View Seat Map"); the raw email button is `flight.view_email` ("📧 View Raw Email"), which reads `flight.btn_loading` while the request runs.

## API calls

- `GET /api/flights/{id}` (flightsApi.get)
- `GET /api/flights/{id}/aircraft` (flightsApi.aircraft; only when the type is unknown and arrival is in the future)
- `GET /api/airports/{iata}` (departure and arrival; fails silently)
- `GET /api/flights/{id}/boarding-passes` (see T-018)
- `GET /api/flights/{id}/email` (flightsApi.email)
- `POST /api/flights/{id}/ungroup` (flightsApi.ungroup; owner only)
- `DELETE /api/flights/{id}` (flightsApi.delete; owner only)
- `GET /api/flights` (flightsApi.list; defined in the web client but no screen calls it)

## Android notes

Same as shared code. The seat map and airport maps open in the system browser (or an in-app web view); the web uses an iframe for the airport map and a new tab for the seat map. Render the email HTML in a web view with JavaScript disabled.

## iOS notes

Same as shared code. The seat map opens in `SFSafariViewController`; render the email HTML in a `WKWebView` with JavaScript disabled.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- ViewModel and UI state (C08): `SOFTWARE_PATTERNS.md` state machine (sealed interfaces, not booleans), `FlowState` in `core-data/.../AppFlowSupport.kt`, `composeApp/.../kmpstartup/FlowStateCard.kt`, androidx `ViewModel`; sealed flight state (Loading, Error, Loaded); banners derived from status ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt); [FantasyPremierLeague: `PlayerListViewModel.kt`](https://github.com/joreilly/FantasyPremierLeague/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PlayerListViewModel.kt)
- Date, time and time zone (C17): `kotlinx-datetime` already in `core-model`, `core-data`, `backend-client` (`Instant` in `core-model/.../Sync.kt`); add zone-aware helpers in `core-model`; hero times and delay text ; copy [FantasyPremierLeague: `GameFixture.kt`](https://github.com/joreilly/FantasyPremierLeague/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/model/GameFixture.kt); [FantasyPremierLeague: `FixturesListView.kt`](https://github.com/joreilly/FantasyPremierLeague/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/ui/fixtures/FixturesListView.kt)
- Maps (C12): not in base: add an `expect fun` map composable per platform (osmdroid or maps-compose on Android, MapKit on iOS); MapLibre, great-circle arcs and raster tile URLs have no sample; airport maps: open in the system browser or a web view; an in-app map is optional ; copy [PeopleInSpace: `ISSMapView.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/ui/ISSMapView.kt); [PeopleInSpace: `ISSMapView.android.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/androidMain/kotlin/dev/johnoreilly/common/ui/ISSMapView.android.kt); [PeopleInSpace: `ISSMapView.ios.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/iOSMain/kotlin/com/surrus/common/ui/ISSMapView.ios.kt); [PeopleInSpace: `NativeISSMapView.swift`](https://github.com/joreilly/PeopleInSpace/blob/main/PeopleInSpaceSwiftUI/PeopleInSpaceSwiftUI/NativeISSMapView.swift)
- System browser / web view (C26): web view for the raw email (JavaScript off), system browser for the seat map ; copy [Confetti: `SpeakersUI.kt`](https://github.com/joreilly/Confetti/blob/main/shared/src/commonMain/kotlin/dev/johnoreilly/confetti/ui/speakers/SpeakersUI.kt) (`LocalUriHandler.openUri`); web view: no sample
- Repository (`SOFTWARE_PATTERNS.md`): `FlightRepository` hides flight, aircraft and email calls ; copy no sample

## Tests

- Detail test: a cancelled flight shows the Cancelled banner; a rescheduled flight shows the "Rescheduled by the airline on {date}. Previously departed {dep} and arrived {arr}." banner with the previous departure and arrival; terminal and gate appear only when set.
- Aircraft test: a flight with a stored `aircraft_type` makes no aircraft request; a future flight without one calls `GET /api/flights/{id}/aircraft` and shows the type; a flight that already landed shows "Aircraft type not available" without a request; a lookup with no `type_name` shows the same text.
- Owner gate test: when `flight.user_id` equals the current user, Edit, Move to New Trip and Delete are shown; for any other user only seat map and raw email are shown.
- Email test: `GET /api/flights/{id}/email` opens the dialog; an HTML body renders without running scripts; with no HTML body the "No HTML body" text is shown; a failure shows the error alert.
- Seat map test: the link slug for "Airbus A320-200" is `airbus-a320-200`.
- Move-to-new-trip test: confirm, call `POST /api/flights/{id}/ungroup`, then open the trip id from the response; declining the confirm does nothing.
- Delete test: confirm dialog, `DELETE /api/flights/{id}`, then return to the trip; a failure shows the error.
- Load error test: a failed `GET /api/flights/{id}` shows "Failed to load flight" and a Back button.
- Seat map gate test: a flight with a stored `aircraft_type` shows the button; a flight without one whose lookup returns `type_name` shows the type but no seat map button.
- Date zone test: the long date under each time is the device-zone date while the time is in the airport zone; a red-eye flight shows the arrival date only when the two device-zone dates differ.
- Timezone line test: shows `GMT+1`-style name; falls back to the raw IANA string; hidden without a timezone.
- Reschedule banner format test: `{date}` is day and short month; previous departure and arrival use their own airport zones.
- Load fallback test: a successful response with no flight shows "Failed to load flight" with "Unknown error"; a missing airport code shows `?` in the title.
- Banner colour test: Cancelled red, Delayed/Rescheduled amber, On time green.
- Delete without trip id test: the route without a trip id returns to the list; the dialog closes on failure too.
- Title test: the title is `LIS → OPO` with U+2192; a flight with no departure code shows `? → OPO`.
- Email Source test: a flight with `email_subject` and no `email_date` shows the subject only; with both, the subject and `formatDateLong(email_date)`; with no subject the block is absent.
- Airport map caption test: with a city it reads `LIS — Humberto Delgado Airport, Lisbon`; without a city there is no trailing comma; the button label uses an em dash.
- Unknown status test (native addition): `cancelled` shows `Cancelled` (`flight.live_status_cancelled`) in the badge and the detail grid; `completed` and `upcoming` show their translated labels; any other unknown status shows the raw key as the web does.
- Loading state test: while `GET /api/flights/{id}` has not answered, the loading screen is shown (web test: "shows loading screen initially").
- Load failure message test: when the request fails with "Not found", that message is shown on the "Failed to load flight" screen (web test: "shows error state when load fails").
- Content test: for flight `LA3001` GRU to MIA, stored times `2025-06-01T10:00:00` and `18:00:00`, passenger `JOHN DOE`, booking reference `ABC123` and aircraft type `Boeing 737` (no registration), the screen shows both airport codes `GRU` and `MIA` (web test: "renders departure and arrival airports"), the flight number `LA3001` (web test: "renders flight number"), the passenger `JOHN DOE` (web test: "renders passenger name"), the booking reference `ABC123` (web test: "renders booking reference") and `✈ Boeing 737` with no brackets (web test: "renders aircraft type when available").
- Back link test: once loaded, the screen has a back link whose target contains the trip id (`#/trips/trip-1`, taken from the `/trips` route) (web test: "renders a back link").
- Web tests mirrored: frontend/src/pages/FlightDetailPage.test.ts

## Native additions (not in web)

- Status label. The web prints the raw status key for `cancelled` and for any status other than `completed` or `upcoming`, because only those two exist as top-level locale keys (`FlightDetailPage.svelte` 280, 471; the backend does store `cancelled`, `sync/pipeline.py` 325). This is a web bug and is reported upstream. Native shows `cancelled` with the existing key `flight.live_status_cancelled` ("Cancelled") in both the hero badge and the detail grid; any other unknown status shows the raw key as the web does.

## Depends on

- T-014
- T-010
- T-018
- T-019
