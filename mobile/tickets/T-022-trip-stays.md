# T-022 Stays (accommodation)

## Web source

- `frontend/src/components/StayRow.svelte`
- `frontend/src/components/TripStays.svelte`

## What it does

Web source line ranges: `TripStays.svelte` 1-294 (logic), 296-427 (list and form); `StayRow.svelte` 1-50; `lib/utils.ts` `accommodationGaps` 893-908, `stayOutsideTravel` 933-956. Neither component has any owner, collaborator, admin or demo check; the "Add a stay" button and the editor are always shown (the server enforces access).

- Stays section of the trip detail page (collapsible, heading "Stays"). On mount `GET /api/trips/{id}/stays`; the list is passed up to the trip page (day planner) and reloaded after each save or delete. A failed load shows the error message in red. With no stays (and no error, after loading) the text "No accommodation in this trip yet." is shown.
- Stay row (a button; tapping opens the inline editor): kind icon (hotel, airbnb, hostel, other), name, "{formatDate(check_in_date)} → {formatDate(check_out_date)}" (real arrow U+2192) followed by "· N night(s)" (middle dot U+00B7; nights from the server; 1 gives "1 night", 0 gives "· Day use", nothing when null), address when set, a details line of room type and "N guest(s)" (only when guests is truthy) joined with " · ", (`StayRow.svelte:39-52`) "Booking reference: X" when set, and a warning line when applicable. Confirmation, contact and notes are not shown on the row.
- Warning on a row (advisory, never blocks), computed from the stored check-in and check-out dates against the dates of all flight and segment departures and arrivals (first 10 characters of the stored UTC value): "This stay ends before the trip's transport starts." (check-out before the first date), "This stay starts after the trip's transport ends." (check-in after the last date), "This stay runs past the trip's last transport." (check-out after the last date). No warning when there is no transport. A check-in before the first transport is not flagged.
- Gaps banner below the list: only when there is at least one stay, the trip has start and end dates, and some night has no stay covering it. Nights are the dates from the trip start up to but not including the trip end date; a date is covered when `check_in_date <= date < check_out_date`. Text "No accommodation booked for N night:" or "No accommodation booked for {count} nights:" followed by the missing dates.
- Gaps line format (`TripStays.svelte:308-313`): the missing dates are each formatted with formatDate and joined with ", " in a separate span after the count text; the singular key is used when exactly one night is missing (`stays.gaps` vs `stays.gaps_plural`). The line renders below the stay list and above the form/Add button.
- "+ Add a stay" opens the inline form (replacing the button). Add defaults (`TripStays.svelte:215-228`): type Hotel; check-in `{trip start_date}T14:00` when the trip has a start date; check-out `{last transport arrival date, or the trip end date when no transport}T11:00`. Example: a trip 2026-05-10 to 2026-05-14 with no transport seeds `2026-05-10T14:00` and `2026-05-14T11:00`; with one flight arriving 2026-05-12 check-out is seeded `2026-05-12T11:00`, not the trip end, so the form never opens already showing the after-transport error (the trip end date counts other stays, the last transport does not). A trip with no start date and no end date (and no transport) leaves both fields empty. Editing prefills from the stay, with check-in and check-out shown as wall-clock time at the property (`place.timezone`).
- Form fields: Type (hotel, airbnb, hostel, other), Name (place picker, kind `stay`, T-015; picking a result fills name, address, coordinates and country code; typing clears coordinates and country and keeps the typed address), Address (free text, editable after picking), Check-in and Check-out (datetime-local), Room, Guests (number, 1-100), Booking reference, Confirmation, Contact, Notes (single-line).
- Check-out picker bounds (`TripStays.svelte:159-175`): minimum is `{check-in date}T00:00` (midnight of the check-in day, so the check-in day itself stays selectable, whatever the check-in time), and it moves whenever check-in changes (check-in 2026-05-10T14:00 gives `2026-05-10T00:00`, changing check-in to 2026-06-01T18:00 gives `2026-06-01T00:00`); with check-in empty there is no minimum at all (not an empty value). Maximum is `{last transport arrival date}T23:59` (the end of that day, so checking out on the morning you fly home works; flights and segments only, not stays); it is left off when there is no transport, and when the check-in date is later than the last transport date (the range would be inverted); in that last case the minimum still follows check-in (check-in 2026-05-20 with last transport 2026-05-12 gives min `2026-05-20T00:00` and no maximum). A native picker that cannot grey out days must still enforce the same range through the validation below.
- Last transport date (`TripStays.svelte:137-146`, `187-192`): `lastTravelDate` is the latest value among the first 10 characters of flights' and segments' `arrival_datetime` (the UTC ISO string, arrivals only; this differs from the row warning, which also uses departures), compared as strings; null when no arrival exists. The `{date}` in the "Check-out is after the trip's last transport ({date}). Add the leg home first, or move the check-out." error is formatDate(lastTravelDate).
- Place pick rule for the address (`TripStays.svelte:107-121`): a pick sets address to the result's address; if the result has no address and has coordinates the address is cleared to ""; if it has no address and no coordinates (the free-typing case) the existing typed address is kept.
- Placeholders and hint (`TripStays.svelte:326-370`): Name "Search a hotel, or type an address"; Address "Street, city" with the hint "Auto-filled when you pick a result. Used for the calendar export, so the entry opens in a maps app."; Room "Double, sea view"; Contact "Host phone or email". Type select options read "{icon} {label}" with icons 🏨 🏡 🛏️ 📍 (kind icon falls back to 📍). Strings come from locale keys `stays.*` (T-004).
- Validation (Save is disabled until valid): name non-blank, both datetimes filled, check-out strictly after check-in (string comparison of the naive values; error `stays.error_check_out_order` "Check-out has to be after check-in." when equal or earlier, shown only while both fields are filled; nothing is shown while the order is right or check-out is empty; with check-out equal to check-in, 2026-05-10T14:00 for both, the message shows and Save stays disabled), and check-out date (the first 10 characters, so a check-out at 10:00 on the last transport's day is allowed and one on the next day is not) not after the last transport arrival date (error "Check-out is after the trip's last transport ({date}). Add the leg home first, or move the check-out."). When the trip has no transport the second rule does not apply. The server error is also shown in the form. Save shows "Saving…" while sending.
- Save sends the whole form, not only changed fields: `{kind, place:{name (trimmed), address (trimmed, null when empty), lat, lon, country_code}, check_in_datetime, check_out_datetime, booking_reference, confirmation, contact, room_type (trimmed, null when empty), guests (integer when a positive number, else null), notes (trimmed, null when empty)}` with `POST` for a new stay and `PATCH` when editing.
- Check-in and check-out are naive local datetimes (for example `2026-10-04T15:00`). The backend converts them to UTC using the timezone derived from the stay's coordinates and stores the local calendar dates, so the app must send the wall-clock value the user typed and never convert it on the device.
- Delete is a button inside the editor: browser confirm "Delete {name}?", then `DELETE`, close the form and reload. Cancel closes the form without confirmation. If DELETE fails the message is shown in the form (formError) and the form stays open (`TripStays.svelte:281-293`).
- Single form (`TripStays.svelte:300-302`, `424-428`): only one form exists; it renders below the list and the gaps line, rows stay visible, and tapping another row while the form is open re-seeds it from that stay without confirming (unsaved edits are discarded). The "+ Add a stay" button is hidden whenever the form is open (add or edit). Rows are shown in API order with no client-side sorting.
- The delete confirm above is `stays.delete_confirm` ("Delete {name}?", `TripStays.svelte:285`, `{name}` = the stay's place name). The place picker inside the form uses the stay wording for its feedback, `places.searching`, `places.located`, `places.no_coords_hint` and `places.lookup_failed` (T-015).

## API calls

- `GET /api/trips/{tripId}/stays` (staysApi.list)
- `POST /api/trips/{tripId}/stays` (staysApi.create)
- `PATCH /api/trips/{tripId}/stays/{stayId}` (staysApi.update)
- `DELETE /api/trips/{tripId}/stays/{stayId}` (staysApi.delete)

## Android notes

Same as shared code.

## iOS notes

Same as shared code.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- ViewModel and UI state (C08): one ViewModel exposing a sealed UI state, not booleans (`SOFTWARE_PATTERNS.md`; `FlowState` in `core-data/.../AppFlowSupport.kt`) for the list plus one inline editor state ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt)
- Date, time and time zone (C17): `kotlinx-datetime` in `core-model` (`Instant` in `Sync.kt`); add zone-aware helpers in `core-model`; naive check-in and check-out, nights and gaps per day ; copy [FantasyPremierLeague: `GameFixture.kt`](https://github.com/joreilly/FantasyPremierLeague/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/model/GameFixture.kt)
- Repository (`SOFTWARE_PATTERNS.md`): `StayRepository` hides `GET/POST/PATCH/DELETE` for stays; warnings and gaps are pure functions in `core-model`

## Tests

- Time test: entering check-in 15:00 for a stay in a UTC-10 location sends the naive value `...T15:00` unchanged, and the form after reload shows 15:00 (the stored UTC value converted with the property timezone).
- Defaults test: "Add a stay" on a trip starting 2026-10-04 and whose last transport arrives 2026-10-10 prefills check-in `2026-10-04T14:00` and check-out `2026-10-10T11:00`.
- Gap test: a trip of 5 nights with one 3-night stay shows "No accommodation booked for 2 nights:" with the two missing dates; with no stays no banner is shown.
- Validation test: check-out equal to or before check-in disables Save and shows "Check-out has to be after check-in."; a check-out date after the last transport arrival shows the add-the-leg-home error; with no transport that rule does not apply.
- Warning test: a stay ending before the first transport date, one starting after the last, and one running past the last each show the matching warning; a check-in before the first transport shows none.
- Payload test: empty optional fields are sent as `null`, guests as an integer or null; Save on an existing stay uses `PATCH` with the whole body.
- Delete test: Delete in the editor asks "Delete {name}?" then calls `DELETE` and reloads.
- Row format test: a 3-night stay shows "4 Oct → 7 Oct · 3 nights"; 0 nights shows "· Day use"; null nights shows no label; room and guests join with " · ".
- Gaps format test: two missing nights show the plural text then both dates joined with ", "; one missing night uses the singular text.
- Last-transport test: departures after the last arrival do not move the check-out bound; the error shows the formatted last arrival date.
- Pick test: picking a result without address but with coordinates clears the address; free-typing keeps it.
- Delete failure test: a failing DELETE shows the message in the form and keeps it open; tapping another row while the form is open re-seeds it, and "+ Add a stay" is hidden while it is open.
- Check-out floor test (trip 2026-05-10 to 2026-05-14, no transport): the add form seeds check-in `2026-05-10T14:00`, so the check-out minimum is `2026-05-10T00:00`; changing check-in to `2026-06-01T18:00` moves it to `2026-06-01T00:00`; on a trip with no dates the minimum is absent (web tests: "greys out every day before the check-in day", "moves the floor when check-in changes", "sets no floor while check-in is empty").
- Check-out ceiling test: with one flight arriving 2026-05-12T13:00Z the check-out maximum is `2026-05-12T23:59`; with no transport there is none; with check-in changed to `2026-05-20T14:00` (after the last transport) there is no maximum and the minimum is `2026-05-20T00:00` (web tests: "greys out every day after the last transport", "sets no ceiling when the trip has no transport", "drops the ceiling rather than inverting the range").
- Seed test: with no transport the form seeds `2026-05-10T14:00` and `2026-05-14T11:00`; with the flight arriving 2026-05-12 check-out is `2026-05-12T11:00` and no after-transport error shows; a trip with no dates leaves both fields empty (web tests: "seeds the standard hotel day at both ends", "seeds check-out from the last transport, not the trip end", "leaves both ends empty on a trip with no dates at all").
- Naive datetime test: entering check-out `2026-05-12T09:30` and saving sends `check_in_datetime: "2026-05-10T14:00"` and `check_out_datetime: "2026-05-12T09:30"` unchanged, with no timezone conversion (web test: "sends the local datetime straight through").
- After-transport validation test (flight arriving 2026-05-12): check-out `2026-05-13T10:00` shows "Check-out is after the trip's last transport" and Save is disabled, and tapping Save sends nothing; check-out `2026-05-12T10:00` shows no error and Save is enabled; with no transport, check-out `2027-01-01T10:00` is accepted (web tests: "blocks a check-out after the last transport, and says why", "allows a check-out on the day of the last transport", "bounds nothing when the trip has no transport yet", "refuses to save a stay that would outrun the transport").
- Check-out order test: check-out equal to check-in (`2026-05-10T14:00`) shows "Check-out has to be after check-in." and Save is disabled; with the seeded later check-out that message is not shown (web tests: "keeps save disabled for a check-out equal to check-in, and says why", "says nothing about ordering before check-out has been filled in").
- Row warning test: a stay checking in 2026-05-10 and out 2026-05-13 with a flight arriving 2026-05-12 shows "This stay runs past the trip's last transport."; with the flight arriving 2026-05-14 no warning shows (web tests: "warns when the check-out runs past the last transport", "stays quiet when the transport outlasts the stay").
Web tests mirrored: frontend/src/components/TripStays.test.ts

## Native additions (not in web)

- Offer the address as a maps intent (Android `geo:` URI, iOS `MKMapItem.openInMaps`); the web row only shows the address text.

## Depends on

- T-010
- T-015
- T-008
