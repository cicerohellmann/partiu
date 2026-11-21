# T-029 Statistics and data export

## Web source

- `frontend/src/pages/StatsPage.svelte` (script 1-94, markup 96-314)
- `frontend/src/components/MonthlyChart.svelte` (1-87)
- `frontend/src/api/client.ts` lines 313-337 (`statsApi.get` and the response shape)

## What it does

- Screen `/stats`, title "★ Stats" (`stats.title`; the star is part of the string). No permission gate. `GET /api/stats` (no query) on open; choosing a year sends `GET /api/stats?year=YYYY`. "All time" (the default, `year` omitted) is a pill, not a request flag. The selected year is local screen state only (not in the route, not saved): every time the Stats screen is opened it starts at "All time", including when returning from the world map (`StatsPage.svelte:13, 31, 177`).
- While loading (first load AND every year change) the whole body, pills included, is replaced by the loading screen `stats.loading` ("Crunching numbers…"). A failed request shows "warning sign + message" only (no retry button, and the pills are gone until a later load succeeds; nothing to tap).
- Year pills ("All time" plus one per entry of `years`) are shown only when `years` has more than one entry. The active pill is highlighted. The year is NOT written into any heading.
- Empty state: shown when `total_flights == 0` AND `unique_countries == 0`: plane icon and "No flights yet. Add some trips to see your stats!". A rail-only account (no flights but countries) is therefore not empty.
- Hero: when `total_flights == 0` the hero shows `unique_countries` with "Countries Visited" and up to 6 country names (`visited_countries` codes such as `SE`, `NO` rendered as region names in the language the app is set to (Settings, T-004; the `locale` store, not the device language: "Sweden · Norway" in English), joined with " · ", "+N" for the rest when there are more than 6; a code the platform cannot name is shown as the code itself; `StatsPage.svelte:28-55`). Otherwise the hero shows total distance (`1.2M` from 1,000,000 up with one decimal, `45k` rounded thousands for >= 10,000, otherwise the number with the device locale's thousands separator such as `9,876`, then "km"; `StatsPage.svelte:65-69`). Longest flight, per-flight and Total km use the same locale grouping, e.g. "12,345 km" labelled "Total distance flown". Below it, only when `earth_laps > 0`: `stats.earth_laps` ("{n}× around the Earth", n = laps to one decimal, e.g. "2.3× around the Earth") if laps >= 1, otherwise "P% of the way around the Earth".
- Stat grid, in this order: Flights (`total_flights`), "In the air" (`total_hours` as `Dd Hh` when >= 24 h (days floored, remaining hours rounded to a whole number); below 24 h the server value (one decimal, `backend/stats/service.py:211`) is printed unrounded, "3.5h" or "12h"; `StatsPage.svelte:71-76`), Airports (`unique_airports`), Countries (`unique_countries`; this card is a link to the world map and appends `?year=Y` only when a year is selected, T-030). Then, each only when its value is above zero: Ground legs, Nights away, and `stats.co2` ("CO₂ emitted"; `total_co2_kg`, shown via `stats.co2_kg` "{n} kg CO₂" with n rounded, or `stats.co2_tonnes` "{n} t CO₂" with one decimal from 1000 kg; `StatsPage.svelte:90-93`).
- "Flights over time" bar chart, shown only when `flights_by_period` has any entry with `count > 0`. One bar per period, height = `count / max(count)` of the series (max at least 1) over a fixed 100-unit plot; a count label above each bar with count > 0 (zero bars are drawn faint with no number); bar labels under the axis: `YYYY-MM` periods become the short month name (locale), anything else (a year such as `2024`) is shown as is. When there are more than 12 bars only every 2nd label is shown (13 to 24 bars) or every 3rd (more than 24). The chart scrolls horizontally when wide. Geometry (`MonthlyChart.svelte:12-18, 48-85`): 24-wide bars, 6 gap, 100 plot height, 14 above for counts, 18 below for labels, 3 corner radius; zero bars are a 2-unit muted stub (40% opacity), other bars use the accent at 85% opacity; counts are 9 px tabular figures centred 3 above each non-zero bar; content width = n x 30 - 6, never scaled, at least the container width, scrolls horizontally when wider than the screen. The chart's accessibility label is the English text "Flights per period bar chart" on the web (native: localise).
- Sections shown only when their data is non-empty: Longest flight (when `longest_flight_km > 0`: route with the arrow spaced, and km); Top routes (rank, route, "N x" count); Busiest airports (rank, code, a bar whose width is the count relative to the first entry, count); "Distance per flight" (scrolling list of `flight_breakdown`: route, trip name when set, flight number when set, km or an em dash when km is 0, CO2 when above 0, followed by a "Total" row with `total_km` and `total_co2_kg`; per-flight and Total CO2 use the same format as the CO2 card, kg rounded or tonnes with 1 decimal from 1000 kg, `StatsPage.svelte:259-286`; the trip name is a small line under the route, truncated with an ellipsis; the flight number is monospace on the right); "Airlines flown" (chips: code, name = server `label` else a built-in fallback table (`StatsPage.svelte:78-85`: LA LATAM, SK SAS, DY Norwegian, LH Lufthansa, AD Azul, AA American, UA United, DL Delta, BA British Airways, AF Air France, KL KLM, IB Iberia, EK Emirates, QR Qatar, TK Turkish, FR Ryanair, U2 easyJet, W6 Wizz Air, G3 GOL; the server `label` wins; an unknown code shows the code itself) else the code, and count).
- Export: a link "↓ Export flights as CSV" (the arrow is part of the text, `StatsPage.svelte:307-309`) at the bottom (only when the page is not in the empty state). It is a plain browser link `GET /api/flights/export.csv` with the download name `flights.csv`, sent with the session cookie. It does not use the API client and it ignores the selected year (it always exports all flights).

## API calls

- `GET /api/stats` and `GET /api/stats?year=YYYY` (statsApi.get). Response: `total_km, total_co2_kg, total_flights, total_hours, unique_airports, unique_countries, ground_legs, nights_away, earth_laps, longest_flight_km, longest_flight_route, top_routes[{key,count}], top_airports[{key,count}], top_airlines[{key,count,label}], years[], visited_countries[], flights_by_period[{label,count}], flight_breakdown[{route,flight,km,co2_kg,trip_name}]`
- `GET /api/flights/export.csv` (opened directly by the page via an anchor, not through the API client)

## Android notes

Draw the monthly chart with a Compose canvas or a multiplatform chart library. Save the CSV through the Storage Access Framework (`ACTION_CREATE_DOCUMENT`, MIME `text/csv`) or share it with the share sheet.

## iOS notes

Draw the chart with Swift Charts (or a shared canvas). Export with `ShareLink` or `UIActivityViewController`.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- ViewModel and UI state (C08): one ViewModel exposing a sealed UI state, not booleans (`SOFTWARE_PATTERNS.md`; `FlowState` in `core-data/.../AppFlowSupport.kt`) (loading, empty, data, year selected) ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt)
- Charts and vector canvas (C23): not in base: bar chart "Flights over time" with Compose `Canvas` (`compose.foundation`); chart library optional ; copy no sample
- File download, share and open (C15): not in base: add `expect`/`actual` that saves to cache and hands over (CSV export via `GET /api/flights/export.csv`: Android `FileProvider` + `ACTION_SEND`, iOS share sheet) ; copy no sample
- Date, time and time zone (C17): `kotlinx-datetime` in `core-model` (`Instant` in `Sync.kt`); add zone-aware helpers in `core-model`; flight hours as `Dd Hh`, year pills ; copy [FantasyPremierLeague: `GameFixture.kt`](https://github.com/joreilly/FantasyPremierLeague/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/model/GameFixture.kt)

## Tests

- Year test: choosing 2024 requests `GET /api/stats?year=2024`; choosing "All time" requests `GET /api/stats` with no query; the pills show only when `years` has 2 or more entries.
- Empty test: 0 flights and 0 countries shows the empty text; 0 flights but 2 countries shows the countries hero and no km hero.
- Conditional card test: ground legs, nights away and CO2 cards show only when above zero; CO2 of 1500 reads "1.5 t CO2", 800 reads "800 kg CO2".
- Hero test: `earth_laps` 2.3 reads "2.3× around the Earth"; 0.4 reads "40% of the way around the Earth"; 0 shows no sub line.
- Chart test: with counts 2, 4, 0 the bar heights are 50, 100 and 0 of the 100-unit plot; `2024-03` is labelled with the short month; with 13 or more bars only every 2nd label shows.
- Countries link test: with year 2024 selected the map link carries `?year=2024`; with all time it carries none.
- Export test: the CSV request carries the session cookie, is not filtered by year, and the file is handed to the platform save or share flow.
- Error test: a failing request shows the message and no pills.
- Title test: the top bar reads "★ Stats" (star included).
- Number format test: `total_km` 1,250,000 reads "1.2M"; 45,000 reads "45k"; 9,876 reads "9,876" in an English locale; the Total row reads "12,345 km".
- Airtime test: `total_hours` 3.5 reads "3.5h"; 12.0 reads "12h"; 53.4 reads "2d 5h".
- Chart geometry test: with 3 bars the content width is 84 (3 x 30 - 6); a zero bar is a 2-unit stub; the accessibility label is set.
- Per-flight test: CO2 of 1500 kg on a flight row reads "1.5 t CO2"; a long trip name is truncated.
- Airline name test: code `LH` with no `label` shows "Lufthansa"; unknown code `XX` shows "XX"; a server `label` wins over the table.
- Year reset test: pick 2024, open the map, press Back: Stats shows All time and requests `GET /api/stats` with no year.
- Loading test: while `GET /api/stats` has not answered the loading screen "Crunching numbers…" is shown (web test: "shows loading screen initially").
- Failure test: `GET /api/stats` fails with "Server error": that message is shown (web test: "shows error when load fails").
- Empty screen test: stats with `total_flights` 0 and `unique_countries` 0 show "No flights yet. Add some trips to see your stats!" (web test: "shows empty state when there is nothing at all").
- Rail-only test: `total_flights` 0 and `unique_countries` 2 do not show the empty text, and the grid still shows the "Countries" card (web test: "renders stats for a rail-only account with no flights").
- Countries hero test: `total_flights` 0, `total_km` 0, `unique_countries` 2, `visited_countries` `["SE","NO"]` show the hero label "Countries Visited" with the names (English: "Sweden" among them), and no "Total distance flown" (web test: "swaps the hero to countries when there are no flights").
- Distance hero test: `total_flights` 10 keeps the hero "Total distance flown" and does not show "Countries Visited" (web test: "keeps the km hero when there are flights").
- Ground cards test: `ground_legs` 3 and `nights_away` 7 show the cards "Ground legs" and "Nights away" (web test: "shows ground legs and nights away only when non-zero").
- Flights-only test: `ground_legs` 0 and `nights_away` 0 show "Flights" but neither "Ground legs" nor "Nights away" (web test: "hides the ground cards for a flights-only account").
- Flights value test: `total_flights` 10 shows 10 in the Flights card (web test: "renders total flights when stats are loaded").
- Distance value test: `total_km` 15000 shows "15k km" in the hero (web test: "renders total distance").
- Year pills test: `years` `[2024, 2025]` show "All time", "2024" and "2025" (web test: "renders year pills when multiple years exist").
- Single year test: `years` `[2025]` shows no pills (web test: "does not show year pills when only one year").
- Year request test: tapping the "2024" pill sends `GET /api/stats?year=2024` (web test: "calls statsApi.get with year when a year pill is clicked").
- Year link test: after tapping "2024" the Countries card opens the world map with year 2024 (web: `#/stats/map?year=2024`) (web test: "countries link includes year query param when year is selected").
- All-time link test: with "All time" selected the Countries card opens the world map with no year (web: `#/stats/map`) (web test: "countries link has no year param when all-time is selected").
Web tests mirrored: frontend/src/pages/StatsPage.test.ts

## Depends on

- T-001
- T-002
- T-007
- T-008
