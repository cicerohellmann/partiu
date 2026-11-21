# T-011 Trip documents

## Web source

- `frontend/src/pages/TripDetailPage.svelte` lines 253-310 (documents state, load, upload, delete), 983-1037 (Documents section), 1264-1379 (viewer modals)
- `frontend/src/api/client.ts` lines 245-295 (`boardingPassesApi`, `tripDocumentsApi`)
- `backend/trip_documents/service.py`, `backend/trip_documents/routes.py` (server limits)

## What it does

- The Documents section sits last in the main column of the trip page (T-010) and is hidden when printing. Its heading has an "add" button (`trip.doc_add`, "Add"; a file picker) and, when the trip has no documents and no boarding passes, a short "no documents" note beside it (`trip.doc_empty`, "No documents yet. Upload bus tickets, vouchers, or anything with a QR code.") (the section is shown compact). Compact rule (`TripDetailPage.svelte:979-1003`): the section is drawn compact (one header row holding the heading, the note and the Add button, and no thumbnail grid) exactly while there are no documents, no boarding passes and no upload error line; as soon as one document or one boarding pass exists the note disappears and the thumbnail grid is drawn in the normal (non-compact) section; an upload error line also ends the compact look (the note stays while the lists are empty).
- On load the page fetches `GET /api/trips/{id}/documents` and `GET /api/trips/{id}/boarding-passes` together; a failure of either is swallowed and shown as an empty list. The grid shows boarding passes first (thumbnail from `GET /api/boarding-passes/{id}/image`, label `🎫 {flight_number} {DEP}→{ARR}`, `TripDetailPage.svelte` 1018-1020), then documents (thumbnail from `GET /api/documents/{id}/view?page=0`, label = file name). Boarding passes added from a flight page (T-018) therefore also show here.
- Upload: the picker accepts `.pdf`, PNG, JPEG and WebP and takes ONE file. `POST /api/trips/{id}/documents` multipart, field `file`; the button reads `trip.doc_uploading` ("Uploading…") and is disabled while running; on success both lists reload. On failure the server's string `detail` (or "HTTP <status>", or the translated upload-error text if the message is empty) shows as a red line under the heading. The server rejects unsupported types and files over 20 MB (413 for size, 422 for an unsupported type or a file under 10 bytes) and returns 404 when the trip is not readable by the user. Any collaborator may upload, not only the owner.
- Viewer for a document: a modal with the file name, page controls (previous / next and `trip.doc_page`, "Page {current} of {total}") only when `page_count > 1`, a delete button and a close button; the image is `GET /api/documents/{id}/view?page=N` (page 0 first, previous disabled on the first page and next on the last). Tapping the backdrop closes it. Pages are fetched as images by changing the `page` query value; there is no swipe gesture in the web.
- Boarding pass viewer header (`TripDetailPage.svelte` 1340-1360): `🎫 {flight_number} {DEP}→{ARR}`, then, when `passenger_name` is set, ` · {passenger_name}`, then, when `seat` is set, ` · {flight.seat} {seat}` (the locale word `flight.seat` then the seat value). Separator is space, middle dot U+00B7, space.
- Delete a document: a browser confirm ("trip.doc_delete_confirm"), then `DELETE /api/documents/{id}` (204), removes it from the list and closes the viewer. A failure is not handled (no message).
- Viewer for a boarding pass: modal with "flight number DEP→ARR", passenger name and seat when present, the image, close, and a delete button shown only when `is_owner !== false`; delete asks the same confirm then `DELETE /api/boarding-passes/{id}`.
- Permission: the web shows the upload button and the document delete button to everyone who can open the trip, including collaborators; the server decides (read access is required; the view endpoint answers 404 for an unknown document and 403 "Access denied" without access). The web adds no owner check on documents themselves.

## API calls

- `GET /api/trips/{tripId}/documents` (tripDocumentsApi.list)
- `POST /api/trips/{tripId}/documents` (tripDocumentsApi.upload; multipart field `file`)
- `GET /api/documents/{docId}/view?page=N` (tripDocumentsApi.viewUrl; `page` defaults to 0)
- `DELETE /api/documents/{docId}` (tripDocumentsApi.delete)
- `GET /api/trips/{tripId}/boarding-passes` (boardingPassesApi.listForTrip)
- `GET /api/boarding-passes/{bpId}/image` (boardingPassesApi.imageUrl)
- `DELETE /api/boarding-passes/{bpId}` (boardingPassesApi.delete; owner only in the UI)

## Android notes

Upload with the Storage Access Framework document picker or the photo picker (no storage permission needed). View: download to cache and open with `FileProvider` and `ACTION_VIEW`, or render PDFs in-app with `PdfRenderer`. 

## iOS notes

Upload with `fileImporter` or `PhotosPicker`. View with `QLPreviewController` or `PDFKit`. 

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- File pick and upload (C14): not in base: add an `expect`/`actual` picker (Android photo/document picker, iOS `PhotosPicker`/`fileImporter`) and Ktor `submitFormWithBinaryData` in `backend-client`; one file per upload, PDF/PNG/JPEG/WebP ; copy no sample
- File download, share and open (C15): not in base: add an `expect`/`actual` that saves to cache and hands over (Android `FileProvider` + `ACTION_VIEW`/`ACTION_SEND`, iOS share sheet/`QLPreviewController`); open and share a document ; copy no sample
- Image loading (C13): Coil 3 in `composeApp` (`coil`, `coil-network-ktor`) and `composeApp/.../kmpstartup/ImagePrimitives.kt`; wire Coil to the shared Ktor client so the session cookie is sent; page images and boarding passes through the cookie client ; copy [Confetti: `SpeakerItemView.kt`](https://github.com/joreilly/Confetti/blob/main/shared/src/commonMain/kotlin/dev/johnoreilly/confetti/ui/speakers/SpeakerItemView.kt)
- Error mapping (C03): no HTTP-status mapping in base; add one mapper in `backend-client` (Ktor `HttpResponseValidator`) and show failures as a sealed `Error` UI state; enums for reasons as in `core-model/.../ConnectionDiagnostics.kt`; upload and delete errors ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt); [PeopleInSpace: `PeopleInSpaceRepository.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/repository/PeopleInSpaceRepository.kt)
- State machine (`SOFTWARE_PATTERNS.md`): viewer as a sealed state (Closed, Document(page), BoardingPass) ; copy no sample

## Native additions (not in web)

- Accept shares of PDFs/images from other apps (Android `ACTION_SEND` filter, iOS Share Extension "Add to trip").
- Swipe between pages in the viewer (the web uses previous/next buttons); native PDF rendering with `PdfRenderer` / `PDFKit` is allowed as long as the server's page images stay the reference.

## Tests

- Upload test: a picked PDF produces one multipart POST with field `file`, then both lists reload and it appears; a 413 or 422 shows the server message under the heading; an empty list shows the "no documents" note.
- List test: boarding passes appear before documents; a failing list call shows an empty section.
- View test: opening a document requests `/api/documents/{docId}/view?page=0` with the session cookie; a 3-page document requests `page=1` and `page=2` with next, previous disabled on page 1 and next disabled on page 3; a 1-page document shows no page controls.
- Delete test: the confirm gates `DELETE /api/documents/{id}`; after success the thumbnail is gone and the viewer closes.
- Boarding pass test: the viewer shows passenger and seat when present; the delete button is hidden when `is_owner` is false.
- Boarding pass viewer header test: the header reads `🎫 {flight_number} {DEP}→{ARR}`, then ` · {passenger_name}` when set, then ` · {flight.seat} {seat}` when set (space, middle dot U+00B7, space); the same `🎫 {flight_number} {DEP}→{ARR}` is the thumbnail label.
- Documents compact test: with no documents and no boarding passes the Documents section is the compact variant, its header row carries the note "No documents yet. Upload bus tickets, vouchers, or anything with a QR code." and there is no thumbnail grid (web test: "compacts the documents section when there is nothing in it"); once the list answers one document (visa.pdf) the thumbnail grid shows, the section is no longer compact and there is no note (web test: "drops the compact treatment once a document exists").
Web tests mirrored: frontend/src/pages/TripDetailPage.test.ts

## Depends on

- T-010
