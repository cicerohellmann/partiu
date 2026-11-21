# T-014 Trip transport list: flights, ground segments and layovers

## Web source

- `frontend/src/components/ConnectionBadge.svelte`
- `frontend/src/components/DateDivider.svelte`
- `frontend/src/components/FlightRow.svelte`
- `frontend/src/components/LegDivider.svelte`
- `frontend/src/components/SegmentRow.svelte`
- `frontend/src/components/TripTransport.svelte`

## What it does

Web source line ranges: `TripTransport.svelte` 1-176 (logic), 178-220 (list), 222-317 (form); `lib/utils.ts` 280-600 (`splitTransport`, `splitLegs`, `legStats`, `connectionInfo`, `dateDividerInfo`). The component has no permission gate: there is no owner, collaborator, admin or demo check; the Add transport link and the segment edit form are always shown (the server enforces access).

- Transport section of the trip detail page (`TripDetailPage.svelte` 860-865, collapsible under the heading "Transport"). It receives the trip, its flights and a `flightBasePath` (`trips`, or `history` when the trip page was opened from history, so flight links become `#/history/{tripId}/flights/{id}`).
- On mount it calls `GET /api/trips/{id}/segments`; the result is passed up to the trip page (it feeds the map and the day planner). A failed load shows the error message in red text; while loading nothing else is shown. Segments are reloaded after every save or delete.
- Grouping (`splitTransport`): with no flights, the ground segments are shown as one flat list sorted by departure, with no group headings. With flights: flights are split into Outbound and Return only when there are at least 2 flights, the last arrival airport equals the first departure airport, and the largest gap between consecutive flights is at least 12 hours (the flights from that gap on are Return). Otherwise all flights are Outbound and there is no Return. Ground segments are placed by departure time: before the end of the outbound flights goes into Outbound, at or after the start of the return flights goes into Return (only if a Return exists), anything else goes into "Getting around" (shown between the two, only when non-empty). Each group is sorted by departure. Heading labels: "Outbound", "Getting around", "Return" (with a return arrow; `trip.return`, "↩ Return", `TripTransport.svelte:211`). With no flights and no segments (after loading) the text "No transport in this trip yet." is shown.
- Group heading (`LegDivider`): `{label}` followed by `info` (`LegDivider.svelte` 13-17). `info` is empty unless the flying time (sum of leg durations) is above 0 minutes. When it is, `info` = ` · {formatDuration(flying)} {trip.travelling}` (space, middle dot U+00B7, space), and when the total elapsed time from first departure to last arrival is greater than the flying time it continues with ` · {formatDuration(total)} {trip.total}`. The separator is a middle dot, not a hyphen. The total is 0 (not shown) when any gap between consecutive legs in the group exceeds 24 hours.
- Between two consecutive legs in a group: if the previous leg's arrival date (first 10 characters of the stored ISO value) differs from the next leg's departure date, a date divider shows the next departure day (weekday, short month, day, in the departure timezone). Otherwise a connection badge shows "{label} layover at {place}" where label is `Xh Ym` or `Ym` and place is the previous leg's arrival place (IATA code or station name). The badge is not shown when either time is missing or the gap is not positive. There is NO minimum-layover warning and NO airport-change warning in the web.
- Flight row (`FlightRow`): a link to the flight detail (T-017). Shows departure local time and day-month, from and to IATA codes, "Arrives {time}" in the arrival timezone, duration when known, airline code badge when present, flight number (the time is in the leg's own zone, but the day-month under it, `formatDayMonth`, takes no zone, so it is the date in the device zone; the date divider between legs, by contrast, uses the next leg's departure zone; FlightRow 37, `lib/utils.ts` 48), and a single status badge chosen in this order: Cancelled, Diverted (live status), `+{minutes}min` departure delay (no space, for example `+15min`, shown only when `live_departure_delay` is greater than 0; `FlightRow.svelte` 30, 62), Rescheduled (only if the flight is not completed and it is rescheduled or has a schedule change notice), a check mark when completed, "In flight" when active. No cabin class and no booking reference appear on the row. Completed flights (arrival in the past) are drawn dimmed (about 62 percent opacity); a cancelled row gets a light red tint; the row class is `cancelled` when cancelled, else completed / active / upcoming (`app.css` 1231-1251). Badge colours: Cancelled = danger, Diverted, +N min and Rescheduled = warning, check mark = success, In flight = accent.
- Segment row (`SegmentRow`): a button (not a link) that opens the inline editor. Shows departure local time and day-month, from and to place names with an arrow, "Arrives {time}" and duration, a type icon (train, bus, ferry, car), operator and number joined by a space, and the seat when set. The day-month is the device-zone date here too (SegmentRow 30). Notes and booking reference are not shown on the row.
- Inline editor (opened by tapping a segment row; there is no inline add). Fields: type (train, bus, ferry, car; default train), operator, number, from place and departs (datetime-local), to place and arrives, seat (hidden for car), booking reference. The place fields use the place picker (T-015) with the segment type as the `kind` filter. The datetimes are prefilled as wall-clock time at each station (stored UTC converted with the station timezone). Save is disabled while sending or until both place names (non-blank) and both datetimes are filled. There is no check that arrival is after departure, and no notes field. Unlike add transport (T-016), the two date-time fields have no min/max from the trip dates and no trip-range hint (TripTransport 225-296).
- Save sends the whole form (not only changed fields): `{type, departure:{name,lat,lon,country_code}, arrival:{...}, departure_datetime, arrival_datetime, operator, number, booking_reference, seat}` where the three text fields and seat are trimmed and sent as `null` when empty, and seat is always `null` for car. The datetimes are naive local strings (for example `2026-10-04T08:00`) that the backend converts to UTC. Edit uses `PATCH`; create is never called from this component. On success the form closes and the list reloads; on error the message is shown in red above the buttons.
- The editor has Save, Cancel and (when editing) Delete. Delete asks `Delete {departure.name} → {arrival.name}?` (real arrow U+2192, not `->`; `TripTransport.svelte` 166-167) (browser confirm), then calls `DELETE`, closes the form and reloads; a failure shows the error in the form.
- When the editor is closed, a button "+ Add transport" links to the add screen (T-016, `#/trips/{id}/add-transport`).
- There is no total travelled distance summary.
- Locale keys in this section: the row badge `flight.in_flight` ("● In flight") appears on a flight row whose status is `active` and which has no cancelled, diverted, delayed or rescheduled badge before it (`FlightRow.svelte:68`). The inline editor's type dropdown labels come from `segments.type_train`, `segments.type_bus`, `segments.type_ferry` and `segments.type_car` (Train, Bus, Ferry, Car; `TripTransport.svelte:229`); its "To" label is `segments.to` and its number placeholder is `segments.number_placeholder` ("G87", `TripTransport.svelte:241`, `265`). The delete confirm above is `segments.delete_confirm` ("Delete {route}?", `TripTransport.svelte:167`). (`segments.add` ("Add ground transport") is not used by the web.)

## API calls

- `GET /api/trips/{tripId}/segments` (segmentsApi.list)
- `POST /api/trips/{tripId}/segments` (segmentsApi.create; defined here, called from T-016)
- `PATCH /api/trips/{tripId}/segments/{segmentId}` (segmentsApi.update)
- `DELETE /api/trips/{tripId}/segments/{segmentId}` (segmentsApi.delete)

## Android notes

Same as shared code.

## iOS notes

Same as shared code.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- ViewModel and UI state (C08): `SOFTWARE_PATTERNS.md` state machine (sealed interfaces, not booleans), `FlowState` in `core-data/.../AppFlowSupport.kt`, `composeApp/.../kmpstartup/FlowStateCard.kt`, androidx `ViewModel`; list plus an inline editor state (Closed, Editing, Saving, Error) ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt); [FantasyPremierLeague: `PlayerListViewModel.kt`](https://github.com/joreilly/FantasyPremierLeague/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PlayerListViewModel.kt)
- Date, time and time zone (C17): `kotlinx-datetime` already in `core-model`, `core-data`, `backend-client` (`Instant` in `core-model/.../Sync.kt`); add zone-aware helpers in `core-model`; local times, layover and day-change text per airport zone ; copy [FantasyPremierLeague: `GameFixture.kt`](https://github.com/joreilly/FantasyPremierLeague/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/model/GameFixture.kt); [FantasyPremierLeague: `FixturesListView.kt`](https://github.com/joreilly/FantasyPremierLeague/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/ui/fixtures/FixturesListView.kt)
- JSON models (C02): `@Serializable` data classes in `core-model` (e.g. `Sync.kt`), `Json { ignoreUnknownKeys = true }` as in `PlatformHttpClient.android.kt`; one `Leg` model for flights and segments ; copy [PeopleInSpace: `PeopleInSpaceApi.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/remote/PeopleInSpaceApi.kt)
- Error mapping (C03): no HTTP-status mapping in base; add one mapper in `backend-client` (Ktor `HttpResponseValidator`) and show failures as a sealed `Error` UI state; enums for reasons as in `core-model/.../ConnectionDiagnostics.kt`; save and delete errors ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt); [PeopleInSpace: `PeopleInSpaceRepository.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/repository/PeopleInSpaceRepository.kt)
- Repository (`SOFTWARE_PATTERNS.md`): `SegmentRepository` hides the segment calls ; copy no sample

## Tests

- Grouping test: a round trip with an outbound flight, a return flight at least 12 hours later with the same origin as final arrival, and a train between them shows Outbound, Getting around (the train) and Return, each in departure order. A one-way trip shows only Outbound. A trip with only ground segments shows a flat list with no headings.
- Layover test: two flights on the same day with a 45-minute gap show "0h"-less label `45m layover at {code}`; a 5-hour gap shows `5h 0m layover at {code}`; legs on different dates show a date divider instead of a badge; a zero or negative gap shows nothing.
- Row test: a cancelled flight shows the Cancelled badge; a segment row shows operator and number and seat but no booking reference.
- Segment edit test: opening a segment prefills local times in the station timezone; Save sends `PATCH` with the whole body (trimmed, empty strings as null, seat null for car); Save is disabled until names and both datetimes are set.
- Delete test: Delete in the editor asks for confirmation, then calls `DELETE` and reloads the list; cancelling the confirm does nothing.
- Error test: a failed list load shows the error text; a failed save shows the error in the form.
- Row zone test: a flight leg's time is in the airport zone while the day-month under it is the device-zone date.
- Row state test: a completed flight row is dimmed, a cancelled one is tinted red.
- Editor bounds test: the segment editor's date-times accept dates outside the trip range and show no range hint.
- Heading test: a group with 2h 30m flying and 5h elapsed reads `Leg 1 · 2h 30m travelling · 5h total` (middle dot, not a hyphen); with total equal to flying only the first part shows; with no flying time the heading is the bare label.
- Delay badge test: a 15 minute departure delay reads `+15min` (no space); badge priority is cancelled, diverted, delay, rescheduled (not when completed), check mark, in flight.
- Delete confirm test: the text is `Delete Lisbon → Porto?` with U+2192.

## Native additions (not in web)

- None. A minimum-layover or airport-change warning, total distance and a notes field would be new behaviour and are not part of this ticket.

## Depends on

- T-008
- T-010
- T-015
- T-016
