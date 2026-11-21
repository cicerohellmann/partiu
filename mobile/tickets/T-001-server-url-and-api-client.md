# T-001 Server URL and API client

## Web source

- `frontend/src/api/client.ts` lines 55-117 (`_request`, `ApiError`, `UnauthorizedError`), 244-310 (raw `fetch` uploads)
- `frontend/src/api/types.ts` (`PublicConfig` at 25-29)
- `backend/main.py` (CORS at ~152)

## What it does

- The web client uses `BASE = ''`: every call is a relative `/api/...` path on the page's own origin, with `credentials: 'include'`.
- Every JSON call goes through `_request(method, path, body)`. The `Content-Type: application/json` header and a JSON body are set only when a body is passed (`null`/omitted means no body and no header). Helpers: `get`, `post`, `put`, `patch`, `del`.
- A `204` answer returns `null` without reading a body. Any other answer is parsed as JSON; if parsing fails the body is treated as `{}` (so a non-JSON `200` returns `{}`, and a non-JSON error falls through to `HTTP <status>`).
- Error mapping when `res.ok` is false, in this order:
  1. HTTP `503` and `setup_required: true` in the body: throws a plain `Error('setup_required')` (App.svelte compares the message to detect first run, T-002).
  2. `detail` is an object `{error, message, params}`: throws `ApiError(message || "HTTP <status>", error, params)`. This applies to any status, including `401`; it is never an `UnauthorizedError`.
  3. Otherwise the message is the string `detail`, else the body's `error`, else its `message`, else `HTTP <status>`. With status `401` this throws `UnauthorizedError(message)`; any other status throws a plain `Error(message)`.
- Multipart uploads do NOT use `_request`. Boarding pass upload, trip document upload and `.eml` upload build a `FormData` and call `fetch` directly with `credentials: 'include'` (no `Content-Type` header, so the boundary is set by the platform). Their errors are only `Error(detail || "HTTP <status>")` (eml: `detail ?? statusText`): no `401` or `ApiError` mapping, and an object `detail` is not unwrapped. Field names: `file` for boarding passes and documents, `files` (repeated) for `.eml`.
- `GET /api/auth/public-config` returns `{demo, demo_username, demo_password}`; the login screen uses it only to show the demo box (T-002). Its failure is silently ignored there.
- Types are hand-written in `frontend/src/api/types.ts`; the web has no generated models.
- The backend CORS middleware allows no origins (`allow_origins=[]`) because the web app is same-origin. The backend has no CSRF or Origin check.

## API calls

- `GET /api/auth/public-config` (authApi.publicConfig)
- Shared client behaviour for every other call in these tickets (no endpoint of its own).

## Android notes

Use Ktor (or equivalent) with a cookie storage plugin. Allow cleartext HTTP only if the user types an `http://` address, and warn: the session cookie is set with `Secure` unless the server sets `SECURE_COOKIES=false` (see `backend/auth/routes.py`), so an HTTP-only home server needs that setting. Network security config must not trust user-installed CAs unless the user opts in.

## iOS notes

App Transport Security blocks plain HTTP by default; add a per-domain exception only when the user enters an `http://` address, or document that HTTPS is required. Local-network servers need the Local Network usage description in `Info.plist`.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- HTTP client (C01): `backend-client/.../backend/client/Clients.kt` (`KtorAuthApi`) with `PlatformHttpClient.*.kt` expect/actual engines; not in base: add the Ktor `HttpCookies` plugin with your own `CookiesStorage` (add `ktor-client-cookies`) ; copy [PeopleInSpace: `Koin.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/di/Koin.kt)
- JSON models (C02): `@Serializable` data classes in `core-model` (e.g. `Sync.kt`), `Json { ignoreUnknownKeys = true }` as in `PlatformHttpClient.android.kt`; `PublicConfig` and the error body ; copy [PeopleInSpace: `PeopleInSpaceApi.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/remote/PeopleInSpaceApi.kt)
- Error mapping (C03): no HTTP-status mapping in base; add one mapper in `backend-client` (Ktor `HttpResponseValidator`) and show failures as a sealed `Error` UI state; enums for reasons as in `core-model/.../ConnectionDiagnostics.kt`; the three-step order in "What it does"; keep multipart upload errors separate ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt); [PeopleInSpace: `PeopleInSpaceRepository.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/repository/PeopleInSpaceRepository.kt)
- Small settings (C05): `multiplatformSettings` is declared in `core-data/build.gradle.kts` but unused; wrap it in a `core-data` repository; the server address ; copy [FantasyPremierLeague: `AppSettings.kt`](https://github.com/joreilly/FantasyPremierLeague/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/AppSettings.kt); [Confetti: `AppSettings.kt`](https://github.com/joreilly/Confetti/blob/main/shared/src/commonMain/kotlin/dev/johnoreilly/confetti/AppSettings.kt)
- Stored server URL (C32): the address is saved in one `core-data` repository and read by the API client on every call (first-run entry is T-037) ; copy no sample
- Unit tests (C20): `commonTest` in `core-data` (e.g. `SyncMergeTest.kt`) with `kotlin-test` and `kotlinx-coroutines-test`; fake HTTP with Ktor `MockEngine` (add); mocked responses for the error cases ; copy no sample
- Shared API wrapper and caching layer (C33): one `ApiClient` class owns the base URL, JSON and error mapping; screens never touch Ktor ; copy [MortyComposeKMM: `MortyRepository.kt`](https://github.com/joreilly/MortyComposeKMM/blob/main/shared/src/commonMain/kotlin/dev/johnoreilly/mortycomposekmm/shared/MortyRepository.kt)

## Native additions (not in web)

- A native app has no same origin, so on first launch the user enters the address of their Partiu server (for example `https://partiu.example.com`); it is stored on the device and prefixed to every path (the web `BASE`).
- Before accepting the address the app probes `GET /api/auth/public-config` (no sign-in needed). A network error, a non-JSON answer or a 404 shows an inline error and the address is not saved.
- Settings lets the user change the server address (signs them out) and show the server version from `GET /api/version` (T-032).
- Generate request/response models from the server's `/openapi.json` instead of hand-copying `types.ts`, and keep the generator command in the repo. A contract test regenerates and compiles to catch backend drift.

## Tests

- Request shape: a call with a body sends `Content-Type: application/json` and the JSON body; a call without a body sends neither; the session cookie is sent on every call.
- A `204` answer returns no body; a `200` with a non-JSON body returns an empty object.
- Error mapping, each against a mocked response: `503` with `setup_required: true` gives the `setup_required` error; `401` with string `detail` gives the unauthorized error with that message; `401` with an object `detail` gives a coded error (not unauthorized); object `detail` `{error, message, params}` gives a coded error with code and params; `detail` string, else `error`, else `message`, each shown as is; an empty or non-JSON error body gives `HTTP <status>`.
- Upload errors: a failed multipart upload throws the string `detail` (or `HTTP <status>`) and does not use the `401` mapping.
- Native additions: a mocked `public-config` `200` is accepted as a server address; a `404` and a connection failure each show an error and are not saved.

## Depends on

- Nothing.
