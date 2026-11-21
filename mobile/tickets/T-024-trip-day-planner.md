# T-024 Day planner and day notes

## Web source

- `frontend/src/components/TripDayPlanner.svelte` (1-173): day list, note loading, legacy content parsing
- `frontend/src/components/TripDayCard.svelte` (1-436 script and markup): one day, timeline rows, note and checklist editor, autosave
- `frontend/src/pages/TripDetailPage.svelte:945-977`: the section, collapse toggle and the props it passes

## What it does

Section and days:
- The Day Planner section is rendered only when the trip has both a start and an end date. Its header toggles `plannerCollapsed`. When collapsed, only the "focus date" card is shown (`onlyDate`) and all cards start collapsed (`collapseAll`); when printing, every card is forced open (`forceExpanded`).
- If the planner component itself is given a trip without dates it shows "Set trip start and end dates to use the day planner."
- One card per calendar day from start date to end date inclusive.
- Focus date (`TripDetailPage.svelte:472-481`, `970-973`): computed from the trip status (inferTripStatus, T-008): upcoming gives trip.start_date; completed gives trip.end_date; ongoing gives today's device-local date when it lies between start_date and end_date inclusive, else start_date. It is null when the trip has no start or end date. The planner section is expanded by default (`plannerCollapsed` starts false); collapsing it is not persisted.
- Loading: "Loading…" until `GET /api/trips/{id}/day-notes` returns. If that call fails the planner shows the fixed English text "Failed to load planner notes." in red, with no retry and no cards.
- Only the card for today's date starts expanded (when not collapse-all); all other cards start collapsed. Every card can be expanded and collapsed by tapping its header. Nothing else marks today or ongoing trips.

Day card contents:
- Day header label (`TripDayCard.svelte:78-85`): "{weekday short}, {day} {month long}" in the app language: first letter of weekday and month upper-cased, a trailing "." removed from the weekday, day number without a leading zero, no year (for example "Mon, 14 March"). The chevron is ▲ when the card is open (expanded or forced) and ▼ when closed (`:338`). "Today" is the device-local date computed once when the planner is created and is not refreshed at midnight (`TripDayPlanner.svelte:117-118`); the header (not the body) toggles the card.
- Day assignment of legs (`TripDayPlanner.svelte:56-81`; `lib/utils.ts` `localDateKey`, `legRoleFor`, `legDateKeys`): uses the local calendar date of the departure in the departure zone (flight: departure_timezone; segment: departure.timezone) through the local calendar date of the arrival in the arrival zone, inclusive. If the arrival date is missing or not later than the departure date the leg counts as a single-day leg on the departure date. A span is capped at 366 days. Role on a day: first date = departs (no note), last date = arrives (note "arrives"), dates in between = transit (note "in transit"); a day that matches nothing defaults to departs. Flights come from the trip payload (`trip.flights`), ground segments from the segments list loaded by the trip page.
- Stay band (`TripDayCard.svelte:313-321`; `lib/utils.ts` `staysForDay`): reads "{kind icon} {place name} {night N of M}" (key `stays.night_of`). A stay is shown on every date d with check_in_date <= d < check_out_date, using the stored local dates; N = days since check_in_date plus 1; M = the stay's `nights` field, or the date difference when it is null. The check-out day is not a night (it only gets a "Check-out" entry). Kind icons: hotel 🏨, airbnb 🏡, hostel 🛏️, other 📍 (unknown also 📍).
- Car rental band (`TripDayCard.svelte:322-331`; `lib/utils.ts` `rentalsForDay`): reads "🚗 {vendor} day D of N" (key `car_rentals.day_of`). A rental is held on every date d with pickup_date <= d <= dropoff_date (stored local dates, drop-off day INCLUDED, unlike stays); D = days since pickup_date plus 1, N = days between pickup_date and dropoff_date plus 1. The "Pick up car" entry appears on pickup_date and "Return car" on dropoff_date.
- Timeline entry content (`TripDayCard.svelte:117-130`, `153-232`): flight entry: icon ✈︎, bold flight number, optional role note, then "{departure_airport} HH:MM → {arrival_airport} HH:MM" (IATA codes, not place names). Segment entry: icon 🚆 train, 🚌 bus, ⛴️ ferry, 🚗 car (default 🚆), title = operator and number joined by a space (non-empty parts only) else the localised type name (`segments.type_*`), route "{departure.name} HH:MM → {arrival.name} HH:MM". Stay entries use the stay kind icon and are listed on check_in_date / check_out_date (stored local dates) but sorted on the real instant. Rental entries use 🚗. Times use the day card's own formatter: 24 h in the place's zone (device zone when the zone is null), an EMPTY string (not the em dash of `formatTime`) when the datetime is missing, and the first five characters of the time part of the ISO string if formatting throws.
- Header: weekday short name, day and month name in the app language (for example "Sat, 28 March"), then a band for each stay covering that night ("night N of M") and each car rental held that day ("day N of M"), a "Saving…" text while a save is running or a check mark for 1.5 s after it, and a chevron.
- Timeline (read-only, always shown, one chronological list sorted by real instant): flights, ground segments (train, bus, ferry, car), stay check-in, stay check-out, car pick-up and car drop-off. A flight or segment that spans several days appears on every day it covers; on days that are not its first it carries a note "arrives" (the arrival day, sorted at arrival time) or "in transit" (a day wholly in between, sorted first). A flight or segment whose departure datetime is empty appears on no day (it is skipped by the day grouping: `localDateKey(null)` is null, so `legDateKeys` returns no dates; `TripDayPlanner.svelte:56-66`, `lib/utils.ts` `legDateKeys`, `TripDayCard.svelte:111-116`). Among the entries that do appear, an entry whose sort instant is missing or unparseable sorts last (never first). Times are shown 24 h in the place's own time zone. Rows show an icon, title (flight number; segment operator and number, or the transport type if both are empty; "Check-in"/"Check-out"; car rental pick-up/drop-off with vendor) and a route text with place name and time.
- Collapsed (read) mode: shows the note text if not blank and the checklist with checkboxes (an item with empty text shows an ellipsis). The checkbox can still be toggled and saves. If the day has no note, no items, no timeline rows and no stay nights, a "Tap to plan this day…" button is shown, and tapping it expands the card.
- Print layout (only relevant if a print/PDF export is kept; see T-010; `TripDayCard.svelte:655-662`): when printing, the day card hides the save status, "+ Add item", the item delete buttons and the chevron, avoids a page break inside a card and draws a 1px #ccc border. The Packing, Expenses and shared-note sections carry `no-print` and are left out.
- Checklist details (`TripDayCard.svelte:268-276`, `368-395`): deleting an item (✕, accessibility label "Delete item") removes it immediately with no confirmation and schedules an autosave. Checkbox accessibility labels are "Mark as done" / "Mark as undone" (`planner.check` / `planner.uncheck`); the item text field's placeholder is "Item…". Items have no ids and no reordering.
- Expanded (edit) mode: a multi-line note field (placeholder "Write something…"), the checklist (each item: checkbox, auto-growing multi-line text field with placeholder "Item…", delete button) and an "Add item" button. Adding appends an item with empty text, unchecked.

Saving (autosave, no save button):
- Every edit (note typing, item text typing, toggling, adding, deleting) restarts a 600 ms timer. When it fires the card sends `PATCH /api/trips/{id}/day-notes/{date}` with body `{content}` where `content` is the string `JSON.stringify({note, items})` and `items` is an array of `{text, checked}`. The server stores `content` as opaque text.
- The payload is sent as the card holds it: empty items are not dropped and an empty note is sent as an empty string.
- A failed save shows nothing (silent); the next edit triggers another save of the full current state. There is no flush when the page is left, so edits made less than 600 ms before leaving can be lost on web.
- Each card takes a snapshot of its saved content at mount; later reloads of notes are not merged into an open card.

Reading content (`parseContent`) accepts, for each row's `content` string:
- empty string: no note, no items;
- a JSON object: `note` (default empty) and `items` (default empty array);
- a legacy JSON array of blocks: the first block of type `text` gives the note (its `value`), the first block of type `checklist` gives the items;
- any text that is not valid JSON: the whole text becomes the note, no items;
- any other valid JSON (number, string, null): no note, no items.
- Locale keys in the day card: the collapsed-mode button is `planner.add_notes_hint` ("Tap to plan this day…", `TripDayCard.svelte:421`) and the expanded note field's placeholder is `planner.note_placeholder` ("Write something…", line 363). Not used by the web: `planner.no_days` and `planner.day_prefix`.

## API calls

- `GET /api/trips/{tripId}/day-notes` (dayNotesApi.list; rows `{date, content, updated_at, updated_by_username}`)
- `PATCH /api/trips/{tripId}/day-notes/{date}` body `{content}` (dayNotesApi.upsert; `date` is `YYYY-MM-DD`)

## Android notes

Same as shared code.

## iOS notes

Same as shared code.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- ViewModel and UI state (C08): one ViewModel exposing a sealed UI state, not booleans (`SOFTWARE_PATTERNS.md`; `FlowState` in `core-data/.../AppFlowSupport.kt`) with one expanded/collapsed state per day card ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt)
- Date, time and time zone (C17): `kotlinx-datetime` in `core-model` (`Instant` in `Sync.kt`); add zone-aware helpers in `core-model`; day keys, weekday labels, stay and rental bands ; copy [FantasyPremierLeague: `GameFixture.kt`](https://github.com/joreilly/FantasyPremierLeague/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/model/GameFixture.kt)
- Offline cache (C04): `core-data` KStore repositories (`KStoreRepositories.kt`, `StoreFactory.kt`) fit day notes if they are cached for offline use (small, per trip); for many rows or queries add a SQL database ; copy [PeopleInSpace: `PeopleInSpace.sq`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/sqldelight/com/dev/johnoreilly/peopleinspace/PeopleInSpace.sq) (SQLDelight) if SQL is chosen
- Repository (`SOFTWARE_PATTERNS.md`): `DayNotesRepository` over `GET /api/trips/{id}/day-notes`; day assignment of legs is a pure function

## Tests

- Format test: for a note "Museum" and items `[{text:'Tickets', checked:true}]` the request body is `{"content":"{\"note\":\"Museum\",\"items\":[{\"text\":\"Tickets\",\"checked\":true}]}"}`, and reading it back yields the same note and items.
- Parse test: empty content, a JSON object, a legacy block array (`text` and `checklist` blocks), and non-JSON text (becomes the note) all parse as described above.
- Debounce test: ten edits each less than 600 ms apart produce one `PATCH` carrying the final state; an empty item is sent as `{text:'', checked:false}`.
- Failed save test: a failing `PATCH` shows no error and the next edit sends the full state again.
- Load test: a failing `GET .../day-notes` shows "Failed to load planner notes." and no day cards; a trip without dates shows the "Set trip start and end dates" message.
- Initial state test: only today's card starts expanded; a card with no content, no timeline and no stay shows "Tap to plan this day…" which expands it.
- Timeline test: a stay check-in at 15:00 and a flight at 09:00 on the same day appear as flight then check-in; a flight arriving the next day also appears on that day as "arrives" at its arrival time; a three-day drive shows "in transit" on the middle day.
- Focus date test: an upcoming trip focuses start_date, a completed one end_date, an ongoing one today; a trip without dates gives null.
- Day assignment test: a leg from 2026-03-31 to 2026-04-01 appears on both dates; a leg whose arrival date is before its departure date appears only on the departure date; a flight with an empty departure datetime appears on no day; a span longer than 366 days is capped.
- Band test: a stay 4-8 Oct shows "night 1 of 4" to "night 4 of 4" on 4-7 Oct and no band on the 8th (only "Check-out"); a rental 29 Mar-1 Apr is held on four days ending "day 4 of 4".
- Entry format test: a flight shows IATA codes and the flight number; a train segment shows 🚆 and "departure name HH:MM → arrival name HH:MM"; a missing time shows an empty string, not an em dash.
- Header test: the label is "Mon, 14 March" style with no trailing dot; the chevron is ▲ when open and ▼ when closed.
- Checklist test: ✕ deletes at once without confirmation and triggers one autosave; accessibility labels are "Delete item", "Mark as done" / "Mark as undone".
- Print test (only if a print/PDF export is kept; see T-010): the printed day card hides the save status, "+ Add item", item delete buttons and the chevron, avoids a page break inside a card and has a 1px #ccc border; the Packing, Expenses and shared-note sections are left out.

## Native additions (not in web)

- Flush a pending (unsent) debounced edit when the app goes to the background or the screen stops (Android `onStop`, iOS `scenePhase` to background), because a mobile app is suspended without warning.

## Depends on

- T-010
- T-022
- T-023
- T-014
- T-008
