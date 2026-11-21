# T-018 Boarding passes

## Web source

- `frontend/src/pages/FlightDetailPage.svelte` (lines 38-41, 100-130 logic; 560-605 list and upload; 672-695 full-screen overlay)
- `frontend/src/pages/TripDetailPage.svelte` (lines 283-335 logic; 997-1030 Documents grid; 1340-1380 viewer)
- `frontend/src/api/client.ts` (247-269, `boardingPassesApi`)

## What it does

There are two places in the web app, with different behaviour.

Flight detail page (T-017):
- A "Boarding passes" section. The list comes from `GET /api/flights/{flightId}/boarding-passes` (loaded with the flight; a failure is silently ignored). Each pass is a button `🎫 {passenger_name or flight.bp_passenger_unknown}` ("Passenger") and, only when `seat` is set, ` · {flight.bp_seat}` ("Seat {seat}"), joined by space, middle dot U+00B7, space (`FlightDetailPage.svelte` 572-573), plus a remove button showing the glyph ✕ (U+2715, not the letter X) with the tooltip `flight.bp_delete` ("Remove") that asks "Remove this boarding pass?" and then calls `DELETE /api/boarding-passes/{id}` and removes it from the list. With no passes the text "No boarding passes yet. They are added automatically from check-in emails." is shown.
- "Upload manually" opens a file picker restricted to PNG and JPEG (no PDF). The chosen file is sent as multipart form data, field name `file`, `POST /api/flights/{flightId}/boarding-passes` with the session cookie; the label shows "Uploading…" and the input is disabled meanwhile; on success the list is reloaded; on failure an alert "Upload failed: {message}" is shown (the message is the server `detail` or `HTTP {status}`).
- Tapping a pass opens a full-screen black overlay (title "Boarding Pass", close "X", tapping the black background closes it) showing `GET /api/boarding-passes/{id}/image` scaled to fit.
- Upload and delete here are not gated by role (unlike the flight's Edit and Delete buttons).

Trip detail page, Documents section (`TripDetailPage.svelte`):
- The trip's passes are loaded with `GET /api/trips/{tripId}/boarding-passes` (a failure gives an empty list) together with the trip documents, and are shown first in the Documents grid as thumbnails of the image with the label `🎫 {flight_number} {DEP}→{ARR}` (ticket emoji, space, flight number, space, departure code, real arrow U+2192 with no spaces, arrival code; `TripDetailPage.svelte` 1018-1020). Tapping one opens a viewer dialog with the image; the viewer has a close button and a delete button that is shown only when `trip.is_owner !== false`. Delete asks the document delete confirmation and then calls `DELETE /api/boarding-passes/{id}`. This section is hidden when printing.
- The image endpoint is also used directly as an `img` source, so it relies on the session cookie.

What the web does NOT do: it does not show a barcode separately, does not show a boarding group, does not read or display a sequence number, does not keep the screen bright, does not accept PDFs for passes, and does not take sent-in files from the OS share sheet. The `BoardingPass` object has only `id`, `flight_id`, `passenger_name`, `seat`, `source_page` and `created_at`; the trip variant adds `flight_number`, `departure_airport`, `arrival_airport`. How the server creates passes (from check-in emails) is not visible in the web code.
- Locale keys on the flight screen (`FlightDetailPage.svelte:593`): the upload button label is `flight.bp_upload` ("📎 Upload manually"), replaced by `flight.bp_uploading` ("Uploading…") while the upload runs.

## API calls

- `GET /api/flights/{flightId}/boarding-passes` (boardingPassesApi.list)
- `POST /api/flights/{flightId}/boarding-passes` (boardingPassesApi.upload)
- `GET /api/boarding-passes/{bpId}/image` (boardingPassesApi.imageUrl)
- `DELETE /api/boarding-passes/{bpId}` (boardingPassesApi.delete)
- `GET /api/trips/{tripId}/boarding-passes` (boardingPassesApi.listForTrip)

## Android notes

Pick the image with the photo picker (PNG and JPEG, as in the web). Load images with the session cookie.

## iOS notes

Pick with `PhotosPicker` or `fileImporter` (PNG and JPEG). Load images with the session cookie.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- File pick and upload (C14): not in base: add an `expect`/`actual` picker (Android photo/document picker, iOS `PhotosPicker`/`fileImporter`) and Ktor `submitFormWithBinaryData` in `backend-client`; PNG and JPEG only ; copy no sample
- Image loading (C13): Coil 3 in `composeApp` (`coil`, `coil-network-ktor`) and `composeApp/.../kmpstartup/ImagePrimitives.kt`; wire Coil to the shared Ktor client so the session cookie is sent; pass images with the session cookie ; copy [Confetti: `SpeakerItemView.kt`](https://github.com/joreilly/Confetti/blob/main/shared/src/commonMain/kotlin/dev/johnoreilly/confetti/ui/speakers/SpeakerItemView.kt)
- HTTP client (C01): reuse the shared client in `backend-client/.../backend/client/Clients.kt` (`KtorAuthApi` style: one small API class per area); list, upload, delete ; copy [PeopleInSpace: `Koin.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/di/Koin.kt)
- Screen brightness (C27): keep screen brightness up while a pass is open (`expect`/`actual` adapter) ; copy no sample
- State machine (`SOFTWARE_PATTERNS.md`): full-screen viewer as a sealed state ; copy no sample

## Tests

- List test: the flight screen requests `GET /api/flights/{id}/boarding-passes` and shows `🎫 passenger · Seat X` per pass; with none it shows the "No boarding passes yet" text; a failed list request shows nothing extra.
- Upload test: a picked image sends a multipart POST with field `file` to `/api/flights/{id}/boarding-passes`, then the list is reloaded; a server error shows "Upload failed: {message}".
- Viewer test: opening a pass shows `/api/boarding-passes/{id}/image` full screen with the session cookie; tapping the background or the close button closes it.
- Delete test: on the flight screen, the confirmation then `DELETE /api/boarding-passes/{id}`, and the pass leaves the list.
- Trip documents test: passes from `GET /api/trips/{id}/boarding-passes` appear first in the Documents grid with "flight number and route"; the viewer's delete button is hidden when `is_owner` is false.
- Pass label test: a pass with seat 12A reads `🎫 Ana · Seat 12A`; without a seat there is no separator; without a passenger name it reads `🎫 Passenger`; the remove control is ✕ with tooltip "Remove".
- Trip pass label test: the Documents thumbnail label is `🎫 TP123 LIS→OPO` (no spaces around the arrow).

## Native additions (not in web)

- Keep the screen at full brightness while a pass is open (Android `screenBrightness`, iOS `UIScreen.main.brightness`, restored afterwards).
- Accept PDFs and the OS share sheet (`ACTION_SEND`) only if the backend accepts them; unverified.
- Optional wallet passes need a server that signs them; the backend does not provide this today.

## Depends on

- T-017
