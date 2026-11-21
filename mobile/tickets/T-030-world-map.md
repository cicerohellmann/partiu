# T-030 Countries-visited world map

## Web source

- `frontend/src/pages/WorldMapPage.svelte` (script 1-42, markup 44-111)
- `frontend/src/App.svelte` line 31 (route `/stats/map`); the link into it is on the Countries card of `StatsPage.svelte` line 177 (T-029)
- `frontend/src/api/client.ts` lines 315-337 (`statsApi.get`)

## What it does

- Screen `/stats/map`, a full-page layout with its own header (no shared top bar). No permission gate. The year comes from the page hash query (`#/stats/map?year=2020`); with no year, all time.
- On open it calls `GET /api/stats` (or `?year=Y`) and keeps only `visited_countries` (lower-cased codes; matched to the map shapes by the shape id, which is the lower-case ISO 2-letter code).
- Header: a "Back" button (arrow plus "Back") linking to the fixed route `/stats` with no query (not a history-back); the year chosen on Stats is not restored, Stats reopens on All time (T-029; `WorldMapPage.svelte:49-51`), the title "Countries Visited" with " . YEAR" appended when a year is in the URL, and a count pill with the number of visited codes (the size of the set, shown even while loading as 0).
- While loading the body shows `stats.loading` ("Crunching numbers…", the same key as the stats screen; `WorldMapPage.svelte:55`). There is NO error handling: if the request fails the loading text disappears, the map is drawn with nothing visited, the count stays 0 and no message is shown.
- Map: the bundled `@svg-maps/world` shapes (one path per country, with name and id), drawn in the map's own view box. Unvisited countries are muted grey at half opacity with a thin outline; visited ones use the accent colour at full opacity. No zoom or pan. The map has the accessibility label `stats.countries_visited` ("Countries Visited"); each country shape has its own accessibility label equal to its country name (the visited state is not part of it; `WorldMapPage.svelte:63-80`).
- Hover (mouse only): a floating label near the pointer with the country name and an accent check mark when visited. Where hover exists the shape also gets a slightly stronger tint. The label sits 12 px right and 8 px above the pointer, follows pointer moves, ignores pointer events itself and hides on leave; the visited check mark is found by looking the shape up by its NAME, not its id (`WorldMapPage.svelte:23-33, 98-103, 209-228`). It is drawn only for mouse hover; a phone has no equivalent (use tap).
- Tap (touch): tapping a country shows its NAME centred below the map; tapping the same country again clears it. The tap label has NO check mark and does not say whether the country is visited (the check mark exists only in the hover label).
- Layout: the page fills the viewport height; the header adds the top safe-area inset to its top padding and the chip list adds the bottom safe-area inset to its bottom padding, so nothing sits under the notch or home bar (`WorldMapPage.svelte:106-117, 197`).
- Below the map a wrap of chips with the visited country names, ordered by code (alphabetical by ISO code, not by name). A visited code that has no shape in the map is counted but gets no chip.

## API calls

- `GET /api/stats` / `GET /api/stats?year=YYYY` (statsApi.get; only `visited_countries` is used)

## Android notes

Render the same country shapes as vector paths (convert the SVG map to Compose `Path` data at build time) or use MapLibre with a countries layer. Tap picks the country under the finger.

## iOS notes

Same as Android; convert the SVG paths to SwiftUI `Path` or use a shared canvas.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- ViewModel and UI state (C08): one ViewModel exposing a sealed UI state, not booleans (`SOFTWARE_PATTERNS.md`; `FlowState` in `core-data/.../AppFlowSupport.kt`) for the visited-countries set and the selected country ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt)
- Vector world map (C24): not in base: draw the bundled world shapes (SVG paths) and tap hit-testing; the web uses `@svg-maps/world`, which the app must replace with its own bundled shape data with Compose `Canvas` (`compose.foundation`) ; copy no sample
- Repository (`SOFTWARE_PATTERNS.md`): `StatsRepository` reads `GET /api/stats` (only `visited_countries`)

## Tests

- Visited test: with `visited_countries = ["pt","it"]` exactly the shapes with ids `pt` and `it` are filled and the counter shows 2; the chips list Italy before Portugal (ordered by code `it` < `pt`).
- Case test: codes returned in upper case still fill the right shapes.
- Year test: `#/stats/map?year=2020` requests `GET /api/stats?year=2020` and the title reads "Countries Visited . 2020"; with no year it requests `GET /api/stats` and the title has no year.
- Tap test: tapping a country shows its name below the map; tapping it again hides the name.
- Loading test: while the request is pending the loading text is shown; if it fails the map shows with nothing visited and no error (web behaviour).
- Back test: from `/stats/map?year=2020` Back opens `/stats` with no year and Stats shows All time.
- Hover label test: a pointer move shows the label 12 px right and 8 px above the pointer, it follows moves and hides on leave; no hover label on touch.
- Safe-area test: on a device with a notch and home bar the header and the chip list are inset by the safe areas.
- Accessibility test: the map exposes "Countries Visited" and each shape exposes its country name as its accessibility label.

## Depends on

- T-029
