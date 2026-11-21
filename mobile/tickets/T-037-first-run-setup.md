# T-037 First-run setup

## Web source

- `frontend/src/pages/SetupPage.svelte` (script 1-39, markup 41-109)
- `frontend/src/App.svelte` lines 41, 45 (route `/setup`, listed as an auth route that hides the navigation) and 74-106 (start-up auth check and redirect)
- `frontend/src/api/client.ts` lines 100-105 (503 `setup_required` marker) and 127-129 (`authApi.setup`)
- `backend/auth/routes.py` lines 74-84 (`POST /api/auth/setup` sets the session cookie, limited to 5 per minute)

## What it does

- How the screen is reached: at start-up the app calls `GET /api/auth/me`. If the server answers `503` with `setup_required: true` the client raises the special error `setup_required` and the app navigates to `/setup`. Any other failure (401 etc.) goes to `/login`, unless the app is already on `/setup`. A signed-in user who opens `/setup` or `/login` is sent to `/trips`. The shell shows no navigation on this screen.
- Screen: logo, title "Welcome to Partiu", subtitle "Create your admin account to get started".
- Fields: username (label "Username", placeholder "admin", min 2 characters, required), password (label "Password", placeholder "At least 8 characters", min 8, required), confirm password (label "Confirm Password", placeholder "Repeat password", required; `SetupPage.svelte:70-90`), and "Forwarding email address (optional)" (email type, placeholder "trips@yourdomain.com") with the hint "If using the inbound SMTP server, forward flight emails to this address."
- Submit "Create Admin Account" (`setup.submitting`, "Creating account…", while busy, button disabled). In code: nothing happens if the trimmed username or the password is empty. Then, in this order, "Passwords do not match" if password differs from confirm, "Password must be at least 8 characters" if shorter than 8; both are shown in an inline error box and no request is sent. (The min-length and required checks above also come from the browser's form validation.)
- Request: `POST /api/auth/setup` with `{ username (trimmed), password, smtp_recipient_address (trimmed, omitted when empty) }`. The confirm field is not sent. The response is the new user and the server sets the session cookie. On success the web stores the user as the current user and navigates to `/trips`.
- On failure the server message (or "Setup failed") is shown in the inline error box and the user stays on the screen; there is NO automatic redirect to sign-in. When a user already exists the server refuses the call, so this is the path the user sees; reaching `/login` happens only through the start-up check on the next app load.
- No other permission gates; the endpoint is public until the first user exists.

## API calls

- `POST /api/auth/setup` (authApi.setup) body `{ username, password, smtp_recipient_address? }` returns the `User`
- `GET /api/auth/me` (authApi.me), used at start-up; a `503` with `setup_required: true` is what routes here

## Android notes

Same as shared code.

## iOS notes

Same as shared code.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- ViewModel and UI state (C08): one ViewModel exposing a sealed UI state, not booleans (`SOFTWARE_PATTERNS.md`; `FlowState` in `core-data/.../AppFlowSupport.kt`) (checking, setup required, submitting, done) ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt)
- HTTP client (C01): `KtorAuthApi` in `backend-client/.../backend/client/Clients.kt` (`GET /api/auth/me` answering 503 `setup_required`, then the setup call); the session cookie needs the `HttpCookies` plugin (not in base) ; copy [PeopleInSpace: `Koin.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/di/Koin.kt) (`createHttpClient`, no cookies)
- Small settings (C05): `multiplatformSettings` is declared in `core-data/build.gradle.kts` but unused: wrap it in a `core-data` repository (the server URL is stored here (T-001)) ; copy [Confetti: `AppSettings.kt`](https://github.com/joreilly/Confetti/blob/main/shared/src/commonMain/kotlin/dev/johnoreilly/confetti/AppSettings.kt)
- Stored server URL (C32): save the address once in the `core-data` repository from T-001 ; copy no sample

## Tests

- Validation test: mismatched passwords show "Passwords do not match" and a 7-character matching password shows "Password must be at least 8 characters"; neither sends a request. With both wrong the mismatch message wins.
- Body test: with the email field blank the request has no `smtp_recipient_address`; with " a@b.c " it is sent trimmed; the confirm password is not in the body.
- Flow test: a `GET /api/auth/me` returning `503 {setup_required: true}` routes to setup; after a successful setup the user is stored as signed in and the app is on Trips.
- Failure test: a refused setup (for example 4xx with a message) shows the message in the error box and stays on the screen.
- Busy test: while the request runs the button shows "Creating account…" and is disabled.
- Form test: the screen shows the username, password and confirm-password fields (plus the optional forwarding-email field) and the "Create Admin Account" button (web test: "renders the setup form").
- Mismatch test: username "admin", password "password123", confirm "different", submit: the error "Passwords do not match" is shown and no request is sent (web test: "shows error when passwords do not match").
- Short password test: password and confirm both "short" (5 characters): the error "Password must be at least 8 characters" is shown and no request is sent (web test: "shows error when password is too short").
- Request test: username "admin", password "password123", confirm "password123", submit: one `POST /api/auth/setup` whose body has `username` "admin" and `password` "password123" (web test: "calls authApi.setup with correct values").
- Success test: the user the server returns is stored as the signed-in user (web test: "sets currentUser on successful setup").
- Server error test: the server refuses with the message "Username taken": that text is shown in the error box (web test: "shows error message on API failure").
Web tests mirrored: frontend/src/pages/SetupPage.test.ts

## Depends on

- T-001
- T-002
