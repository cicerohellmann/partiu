# T-019 Edit flight

## Web source

- `frontend/src/pages/EditFlightPage.svelte` (load 41-70, submit 74-100, form 108-285)
- `frontend/src/components/AirportCombobox.svelte` (airport fields, see T-016)
- `frontend/src/lib/utils.ts` `toLocalInputValue` (114-131)

## What it does

- Screen `/trips/{tripId}/flights/{flightId}/edit` and the `/history/{tripId}/flights/{flightId}/edit` variant; the base path decides where Back, Cancel and a successful save go (the flight detail screen, T-017). Title "Edit Flight". The page itself has no owner, collaborator, admin or demo check; the Edit button on the flight detail screen is shown only to the flight's owner (T-017), and the server enforces access.
- Load: `GET /api/flights/{flightId}`. While loading the text "Loading flight…" is shown; a failed load shows the error message in red and no form.
- Prefilled fields (null becomes empty text): flight number, airline code (max 3 characters), airline name, departure airport (airport combobox, T-016), departure date and time, departure terminal, departure gate, arrival airport, arrival date and time, arrival terminal, arrival gate, booking reference, passenger name, seat, cabin class (none, economy, premium economy, business, first), notes. Option values are as in T-016 (`premium economy` with a space). If the stored `cabin_class` is not one of the five option values (for example `premium_economy` written by the email parser) the select shows no selection and saving sends an empty `cabin_class`, clearing it (EditFlightPage 245-256); native should either keep the unknown value selectable or warn. Empty-field placeholders: flight number `LA800`, airline code `LA`, airline name `LATAM Airlines`, departure airport `GRU`, arrival airport `SCL`, terminals `A` / `2`, gates `A12` / `B4`, booking reference `ABC123`, passenger `SILVA/JOAO`, seat `12A`, notes `Any additional info…` (`add_flight.notes_placeholder`). Flight number, airline code and booking reference are shown upper-case (display only; submit already upper-cases). The stored UTC times are shown as wall-clock time in each airport's timezone (`departure_timezone`, `arrival_timezone`); when the timezone is unknown the device zone is used. Required fields (marked with a star, browser-validated): flight number, both airports, both date and times. Sections in order (`EditFlightPage.svelte` 117-272): "Flight" (`add_flight.section_route`: flight number *, airline code, airline name), "Departure" (airport *, date and time *, terminal, gate), "Arrival" (same), "Booking Details" (booking reference, passenger name, seat, cabin class select), then an untitled section with the notes textarea (3 rows). No transport type picker, no trip range hint. Unlike add transport, there is no airline-code auto-fill and no trip date range limit.
- Save ("Save Changes", "Saving…" while sending, disabled while sending; there is no client-side check that arrival is after departure, and Save is not gated on validity beyond the browser `required` attributes: flight number, both airports, both date-times; 74-100) sends ALL the fields, not only changed ones: `PATCH /api/flights/{id}` with `flight_number` (trimmed, upper-cased), `airline_name` (trimmed), `airline_code` (upper-cased), `departure_airport` and `arrival_airport` (trimmed, upper-cased), `departure_datetime` and `arrival_datetime` (the naive local `YYYY-MM-DDTHH:mm` strings as shown in the form; the backend re-localises them), `booking_reference` (trimmed, upper-cased), `passenger_name`, `seat`, `cabin_class` (the raw option value, or empty), `departure_terminal`, `departure_gate`, `arrival_terminal`, `arrival_gate`, `notes` (all trimmed; empty fields are sent as empty strings). On success the app opens the flight detail screen, which reloads.
- A server or network error is shown in red above the buttons and the form stays.
- Cancel is a plain link back to the flight detail screen. There is NO unsaved-changes confirmation.
- Locale keys shared with add transport: the booking section title is `add_flight.section_booking` ("Booking Details", `EditFlightPage.svelte:218`); the airport labels are `add_flight.airport` ("Airport (IATA)") and the date-time labels `add_flight.datetime` ("Date & time"), each followed by a plain "*" (lines 161-165); the loading text is `flight.loading` ("Loading flight…", line 110).

## API calls

- `GET /api/flights/{id}` (flightsApi.get)
- `PATCH /api/flights/{id}` (flightsApi.update)
- `GET /api/airports/search?q=` (airportsApi.search, from the airport fields)

## Android notes

Same as shared code.

## iOS notes

Same as shared code.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- ViewModel and UI state (C08): one ViewModel exposing a sealed UI state, not booleans (`SOFTWARE_PATTERNS.md`; `FlowState` in `core-data/.../AppFlowSupport.kt`) with a form state (fields, saving, error) and one save event ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt)
- Date, time and time zone (C17): `kotlinx-datetime` in `core-model` (`Instant` in `Sync.kt`); add zone-aware helpers in `core-model`; local date-times for each airport zone ; copy [FantasyPremierLeague: `GameFixture.kt`](https://github.com/joreilly/FantasyPremierLeague/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/model/GameFixture.kt)
- JSON models (C02): `@Serializable` data classes in `core-model` (`Flight` PATCH body, null becomes empty text); `Json { ignoreUnknownKeys = true }` already set in `PlatformHttpClient.android.kt` ; copy [PeopleInSpace: `PeopleInSpaceApi.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/remote/PeopleInSpaceApi.kt)

## Tests

- Prefill test: the form shows the stored times as wall-clock time in the airport timezone, not the device timezone; null fields appear empty.
- Save test: saving sends one `PATCH /api/flights/{id}` containing every field above (codes and booking reference upper-cased, text trimmed, empty ones as empty strings, naive local datetimes), then opens the flight detail screen.
- Error test: a failed save shows the message and keeps the form; a failed load shows the message and no form.
- Cancel test: Cancel returns to the flight detail screen without a request and without a confirmation.
- Cabin edit test: a stored `premium_economy` shows no selection and saving sends an empty `cabin_class`; a stored `premium economy` is preselected.
- No order check test: arrival before departure is still submitted.
- Placeholder test: empty fields show `LA800`, `GRU`, `SCL`, `12A` and the other examples.
- Section order test: the form shows Flight, Departure, Arrival, Booking Details, then the notes section, with no type picker and no range hint.
- Load and prefill test: opening the edit screen for flight `flight-7` calls `GET /api/flights/flight-7` and the flight number field shows `LA800` (web test: "loads the flight and prefills the form").
- Wall-clock prefill test: stored `2025-06-01T13:00:00+00:00` with zone `America/Sao_Paulo` shows `2025-06-01T10:00` in the departure field, and `2025-06-01T17:00:00+00:00` with `America/Santiago` shows `2025-06-01T13:00` in the arrival field (web test: "prefills datetimes as local wall-clock time at each airport").
- Save request test: changing seat `12A` to `14C` and saving calls `PATCH /api/flights/flight-7` with `flight_number: LA800`, `departure_airport: GRU`, `arrival_airport: SCL`, `departure_datetime: 2025-06-01T10:00` and `seat: 14C` (the other fields are sent too) (web test: "sends the edited fields to flightsApi.update").
- Success navigation test: after a successful save the app opens `/trips/trip-42/flights/flight-7` (from `/history/...` it opens the `/history/...` variant) (web test: "navigates back to the flight detail page on success").
- Save error test: a rejected save with "Invalid flight number format" shows that message and keeps the form (web test: "shows an error when the update fails").
- Load error test: a failed load with "Flight not found" shows that message and no form (web test: "shows a load error instead of the form when the flight cannot be fetched").
- Cancel link test: Cancel goes to `#/trips/trip-42/flights/flight-7` (web test: "cancel link points back to the flight detail page").
- Web tests mirrored: frontend/src/pages/EditFlightPage.test.ts

## Depends on

- T-017
- T-016
