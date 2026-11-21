# T-023 Car rentals

## Web source

- `frontend/src/components/CarRentalRow.svelte`
- `frontend/src/components/TripCarRentals.svelte`

## What it does

Web source line ranges: `TripCarRentals.svelte` 1-248 (logic), 250-355 (list and form); `CarRentalRow.svelte` 1-50. Neither component has any owner, collaborator, admin or demo check; the "Add a car rental" button and the editor are always shown (the server enforces access).

- Car rental section of the trip detail page (collapsible, heading "Car rental"). On mount `GET /api/trips/{id}/car-rentals`; the list is passed up to the trip page (day planner) and reloaded after each save or delete. A failed load shows the error message in red. With no rentals (and no error, after loading) the text "No hired car in this trip yet." is shown.
- Rental row (a button; tapping opens the inline editor): car icon, company, the place (just the pick-up name for a return hire; "{pickup name} → {dropoff name}" when `is_one_way` (`CarRentalRow.svelte:56-58`)), "{formatDate(pickup_date)} HH:MM → {formatDate(dropoff_date)} HH:MM" (real arrow; 24 h in each counter's own timezone; em dash when a time is missing) followed by "· N day(s)" (middle dot; only when days is non-null and not 0; `CarRentalRow.svelte:20-31`), the vehicle when set, "Booking reference: X" when set. Driver and notes are not shown on the row.
- "+ Add a car rental" opens the inline form (replacing the button). Add defaults: pick-up `{trip start_date}T09:00` and drop-off `{trip end_date}T09:00` when the trip has those dates; "returning to the same counter" is on. Editing prefills from the rental, with times shown as wall-clock time at each counter (`pickup.timezone`, `dropoff.timezone`) and the same-counter switch set to `!is_one_way`.
- Form fields: Company (free text with suggestions Hertz, Sixt, Europcar, Avis, Enterprise, Budget; any text is allowed), Vehicle, Pick-up counter (place picker, kind `stay`, so it searches accommodation and addresses via `GET /api/places/search`, T-015; picking fills name, address, coordinates and country code, typing clears coordinates and country), switch "Returning it to the same counter" (default on; when on the drop-off counter field is hidden, when off a Drop-off counter picker appears), Pick-up and Drop-off (datetime-local; the drop-off minimum is `{pick-up date}T00:00`, midnight of the pick-up day, not the pick-up time, so the pick-up day itself stays selectable: pick-up `2026-03-29T09:00` gives minimum `2026-03-29T00:00`, changing pick-up to `2026-06-01T18:00` moves it to `2026-06-01T00:00`; with an empty pick-up there is no minimum at all; there is no maximum) (`TripCarRentals.svelte:121-130`), Booking reference, Driver, Notes (single-line). The form has no separate address field for the counters.
- Validation (Save is disabled until valid): company non-blank, pick-up counter name non-blank, drop-off counter name non-blank when the switch is off, both datetimes filled, and drop-off strictly after pick-up (string comparison of the naive values; error `car_rentals.error_dropoff_order` "The drop-off has to be after the pick-up." when equal or earlier). The error shows as soon as both datetimes are filled and the order is wrong (for example drop-off `2026-03-28T09:00` with pick-up `2026-03-29T09:00`), independently of pressing Save, and disappears when the order is right (`TripCarRentals.svelte:132-138, 347-349`). The server error is also shown in the form. Save shows "Saving…" while sending.
- Save sends the whole form, not only changed fields: `{vendor (trimmed), pickup:{name (trimmed), address (trimmed, null when empty), lat, lon, country_code}, dropoff:{same shape}, pickup_datetime, dropoff_datetime, booking_reference, vehicle, driver_name, notes}` (the last four trimmed, `null` when empty). When the switch is on, `dropoff` is an exact copy of `pickup`, so the backend computes `is_one_way` false; the switch itself is never sent. `POST` for a new rental, `PATCH` when editing.
- Pick-up and drop-off are naive local datetimes (for example `2026-10-04T09:00`), converted to UTC by the backend from the place coordinates, like stays. The app must send the typed wall-clock value and never convert it on the device.
- Place pick rule (`TripCarRentals.svelte:107-121`): a pick sets name, lat, lon, country_code and address = the result's address; with no result address, the existing typed address is cleared to "" when the result has coordinates and kept when it has none (the typing case, so a previously picked address survives later typing of the name). There is no address field, but the address is still sent in the payload.
- Placeholders (`TripCarRentals.svelte:267-300`): Company "Hertz, Sixt, Europcar…"; Vehicle "Fiat 500 or similar"; Pick-up counter and Drop-off counter "Search an airport or branch, or type an address". "Returning it to the same counter" is a checkbox. Strings come from locale keys `car_rentals.*` (T-004).
- Tapping a rental row opens the editor prefilled from it (the Company field shows the stored vendor, for example "Hertz"). The Delete button exists only in the editor of an existing rental; the add form has no Delete button (`TripCarRentals.svelte:360-364`).
- Delete is a button inside the editor: browser confirm "Delete the {vendor} rental?", then `DELETE`, close the form and reload. Cancel closes the form without confirmation. If DELETE fails the message appears in the form (formError) and the form stays open (`TripCarRentals.svelte:235-247`). Rentals are shown in API order with no client-side sort. Only one form exists, below the list; tapping another row while it is open re-seeds it without confirmation, and "+ Add a car rental" is hidden while it is open (`254-256`).
- Rentals appear in the day planner (T-024, `TripDayCard.svelte`) as "Pick up car: {vendor}" and "Return car: {vendor}" entries and as "day N of M" on the days between.
- The delete confirm above is `car_rentals.delete_confirm` ("Delete the {vendor} rental?", `TripCarRentals.svelte:239`). The "N day(s)" text on a row is `car_rentals.days` ("{count} day", pluralised, `CarRentalRow.svelte:21`). The counter pickers use the stay wording for their feedback (`places.*`, T-015).

## API calls

- `GET /api/trips/{tripId}/car-rentals` (carRentalsApi.list)
- `POST /api/trips/{tripId}/car-rentals` (carRentalsApi.create)
- `PATCH /api/trips/{tripId}/car-rentals/{rentalId}` (carRentalsApi.update)
- `DELETE /api/trips/{tripId}/car-rentals/{rentalId}` (carRentalsApi.delete)

## Android notes

Same as shared code.

## iOS notes

Same as shared code.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- ViewModel and UI state (C08): one ViewModel exposing a sealed UI state, not booleans (`SOFTWARE_PATTERNS.md`; `FlowState` in `core-data/.../AppFlowSupport.kt`) for the list plus one inline editor state ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt)
- Date, time and time zone (C17): `kotlinx-datetime` in `core-model` (`Instant` in `Sync.kt`); add zone-aware helpers in `core-model`; naive pick-up and drop-off converted to UTC by the backend ; copy [FantasyPremierLeague: `GameFixture.kt`](https://github.com/joreilly/FantasyPremierLeague/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/model/GameFixture.kt)
- Repository (`SOFTWARE_PATTERNS.md`): `CarRentalRepository` hides the API; validation (company, counters non-blank) is a pure function

## Tests

- Defaults test: "Add a car rental" on a trip 2026-10-04 to 2026-10-10 prefills pick-up `2026-10-04T09:00`, drop-off `2026-10-10T09:00` and the same-counter switch on.
- Same-counter test: with the switch on, the payload's `dropoff` equals `pickup` (name, address, coordinates, country code) and the drop-off field is hidden; with it off the drop-off counter is required and sent separately.
- Validation test: a drop-off equal to or before the pick-up disables Save and shows "The drop-off has to be after the pick-up."; a blank company or pick-up counter also disables Save.
- Time test: the wall-clock time typed is sent unchanged as a naive value, and the form after reload shows the stored UTC time converted with each counter's timezone, regardless of device timezone.
- Payload test: empty optional fields are sent as `null`; editing uses `PATCH` with the whole body.
- Row test: a return hire shows one place name; a one-way hire shows "pick-up → drop-off".
- Delete test: Delete in the editor asks "Delete the {vendor} rental?" then calls `DELETE` and reloads.
- Row format test: the window line reads "4 Oct 09:00 → 10 Oct 09:00 · 6 days" with a middle dot; days 0 or null shows no day count; a one-way place line uses the arrow.
- Pick test: picking a result with coordinates but no address clears the typed address; free-typing keeps it; the address is still in the payload.
- Delete failure test: a failing DELETE shows the message in the form and keeps it open; tapping another row re-seeds the form.
- Rentals empty test: with no rentals the text "No hired car in this trip yet." shows (web test: "shows the empty state when the trip has no rental").
- Rentals upward test: after the list loads, the rental list is passed up to the trip page exactly as loaded (web test: "reports the loaded list upward so the header and planner see it").
- Return-hire form test: in the add form the drop-off counter picker is hidden while "Returning it to the same counter" is on, and appears when it is switched off (web test: "hides the drop-off counter for a return hire").
- Return-hire payload test: with a company "Hertz" and pick-up counter "Vienna Airport" and the switch on, `POST` sends `pickup.name` and `dropoff.name` both "Vienna Airport" (web test: "sends the pick-up counter as both ends of a return hire").
- Drop-off floor test (trip 2026-03-29 to 2026-04-01): the seeded pick-up `2026-03-29T09:00` gives a drop-off minimum of `2026-03-29T00:00`; changing pick-up to `2026-06-01T18:00` moves it to `2026-06-01T00:00`; on a trip without dates (empty pick-up) there is no minimum (web tests: "greys out every day before the pick-up day", "moves the floor when the pick-up changes", "sets no floor while the pick-up is empty").
- Drop-off order message test: drop-off `2026-03-28T09:00` with pick-up `2026-03-29T09:00` shows "The drop-off has to be after the pick-up." (web test: "says what is wrong when the drop-off is before the pick-up").
- Rental editor test: tapping the "Hertz" row opens the editor with Company "Hertz" and a Delete button (web test: "opens the editor with the stored rental").
Web tests mirrored: frontend/src/components/TripCarRentals.test.ts

## Depends on

- T-010
- T-015
- T-008
