# T-002 Sign-in, session cookie and two-factor code

## Web source

- `frontend/src/pages/LoginPage.svelte`
- `frontend/src/lib/authStore.ts`
- `frontend/src/lib/invitationStore.ts` (lines 29-38, the HTTP 401 handling)
- `frontend/src/components/TopNav.svelte` (sign out, lines 26-38)
- `frontend/src/App.svelte`
- `frontend/src/api/types.ts`

## What it does

- Sign-in form: username and password, both `required`, with autofill hints `autocomplete="username"` and `autocomplete="current-password"` (`LoginPage.svelte:183,196`; the code field uses `one-time-code`, line 229); Enter submits the form. `doLogin` does nothing if the trimmed username or the password is empty. The username is trimmed before sending; the button is disabled and reads `login.submitting` ("Signing in…") while the request runs. Under the title the screen shows the subtitle `login.subtitle` ("Sign in to your account") (`LoginPage.svelte:151`). A failure shows `err.message`, falling back to the literal "Login failed". The server rate-limits `POST /api/auth/login` (5 per minute per address, 120 per minute on a demo server) and locks out repeated failures; the web shows whatever message comes back. Labels `login.username` ("Username") and `login.password` ("Password"); placeholders `login.username_placeholder` ("username") and `login.password_placeholder` ("••••••••") (`LoginPage.svelte:176-199`; `locales/en.json:53,54`).
- `POST /api/auth/login` body `{username, password}` returns either `{requires_2fa: true}` or the same shape as `/api/auth/me` (`id`, `username`, `is_admin`, `smtp_recipient_address`, `totp_enabled`, `locale`, `accent`, `announcement`, `carto_api_key`, `demo`). On success the server sets an HttpOnly `session` cookie (30 days).
- On `requires_2fa` the screen switches to the code step (code cleared, error cleared, countdown started). The server has set a `pending_2fa` cookie (5 minutes) that `POST /api/auth/2fa/verify` needs, so the cookie jar must persist between the two calls.
- Code step: digits only, max 6; typing the sixth digit submits automatically; the submit button is also disabled until 6 digits and while loading. Above the field it shows the hint `totp.hint` ("Enter the 6-digit code from your authenticator app") and the countdown `totp.expires` ("Code expires in {s}s", `LoginPage.svelte:213-214`) where N = 30 - (unix seconds mod 30), refreshed every second. The submit button reads `totp.submitting` ("Verifying…") while the request runs. `POST /api/auth/2fa/verify` body `{code}` returns the user. A failure shows `err.message` (fallback "Invalid code") and clears the field. The back link `totp.back` ("← Back to sign in") stops the countdown, returns to the credentials step, and clears the code, its error and the password (not the username). The field has the label `totp.code_label` ("Authenticator Code"), a numeric keypad (`inputmode` numeric, `pattern` `[0-9]*`), placeholder `totp.code_placeholder` ("000000"), one-time-code autofill and takes focus when the step opens; it is disabled while the verify request runs. The button is `totp.submit` ("Verify") when idle and `totp.submitting` ("Verifying…") while busy (`LoginPage.svelte:211-248`; `locales/en.json:67-69`).
- After a successful sign-in (password-only or 2FA) the web: sets the user in the auth store (the server's answer is stored whole and unchanged, `LoginPage.svelte:83, 120`: signing in does not restart the app, so a field dropped here, such as `demo`, `announcement` or `carto_api_key`, would be missing until the next full launch; native must keep every field of the sign-in and verify answers, not only id and name), applies the user's locale (T-004) and accent (T-005), purges the API cache (T-003), calls `refreshInvitationCount()` (T-006) and navigates to `/trips`.
- Demo: the login screen calls `GET /api/auth/public-config` on mount; if `demo` is true it shows a box (title `login.demo_title`, hint `login.demo_hint`: "This is a public demo — sign in with the shared account…" as in en.json) with the demo username and password in plain text and a button `login.demo_signin` ("Sign in with the demo account"), which fills the two fields from the config and runs the normal sign-in. If the call fails the box is simply not shown. The demo username and password are shown in a monospace definition list under the labels `login.username`/`login.password`; tapping one selects the whole value (CSS `user-select: all`, `break-all`) so it can be copied. The sign-in-with-demo button is full width, secondary style, disabled while a sign-in is running, and does nothing without a demo config (`LoginPage.svelte:153-172, 322-332`).
- App start (`App.svelte`): `GET /api/auth/me`. On `200` it stores the user, applies locale and accent, refreshes the invitation count, clears the push badge (`POST /api/notifications/badge/clear`) and, if the hash is `/login`, `/setup` or empty, goes to `/trips`. On any error: if the message is `setup_required` go to `/setup` (T-037); otherwise go to `/login` unless already on `/setup`. While this check runs the web shows only the plain text "Loading..." (`App.svelte:119-123`), not a branded splash and not the login screen. Native may show a platform launch screen but must not show the app UI or the sign-in screen until the check ends.
- Sign out lives in the top navigation (`TopNav.svelte`): calls `POST /api/auth/logout`, ignores any failure, purges the API cache, clears the user, sets the invitation count to 0 and goes to `/login`. (The unread notification count is not reset here.) The button shows the glyph "↩" with title and accessibility label `signout` ("Sign out"); while the logout request runs it shows "…" and is disabled. No confirmation dialog and no toast (`TopNav.svelte:25-38, 53-61`).
- Session expiry is handled in one place only: the 30-second poll `refreshInvitationCount` (`invitationStore.ts:29-38`), which on an `UnauthorizedError` clears the user, zeroes both badge counts and goes to `/login`. Other screens that get a 401 just show the error message; the web has no global 401 handler.
- The top navigation (`.top-nav`, `app.css:657`) is `position: sticky; top: 0` and stays visible while content scrolls; the rail/dock stay pinned too (T-006).
- The current user is one store (`authStore.ts`: `currentUser`, `authLoading`) read by the rest of the app.

## API calls

- `POST /api/auth/login` (authApi.login)
- `POST /api/auth/logout` (authApi.logout)
- `GET /api/auth/me` (authApi.me)
- `POST /api/auth/2fa/verify` (authApi.verify2fa)
- `GET /api/auth/public-config` (authApi.publicConfig)
- `POST /api/notifications/badge/clear` (notificationsApi.clearBadge, after `me` succeeds)

## Android notes

Persist the cookie jar in encrypted storage: the `session` value is a bearer credential, so keep it in Android Keystore-backed storage (for example EncryptedSharedPreferences or a Keystore-wrapped DataStore), not in plain preferences. Offer optional biometric unlock on app start as a later improvement; it is not in the web app.

## iOS notes

Persist the cookie jar in the Keychain (accessibility `AfterFirstUnlock`, not synced to iCloud unless the user wants that). Optional Face ID unlock is a later improvement; it is not in the web app.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- Secure storage (C06): not in base: add an `expect`/`actual` `SecureStore` (Android Keystore-backed, iOS Keychain) in `core-data`; the `session` cookie value ; copy no sample
- HTTP client (C01): `backend-client/.../backend/client/Clients.kt` (`KtorAuthApi`) with `PlatformHttpClient.*.kt` expect/actual engines; not in base: add the Ktor `HttpCookies` plugin with your own `CookiesStorage` (add `ktor-client-cookies`); persist the jar so `pending_2fa` survives between login and verify ; copy [PeopleInSpace: `Koin.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/di/Koin.kt)
- ViewModel and UI state (C08): `SOFTWARE_PATTERNS.md` state machine (sealed interfaces, not booleans), `FlowState` in `core-data/.../AppFlowSupport.kt`, `composeApp/.../kmpstartup/FlowStateCard.kt`, androidx `ViewModel`; sealed `LoginState` (Credentials, TwoFactor, Busy, Error), not booleans ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt); [FantasyPremierLeague: `PlayerListViewModel.kt`](https://github.com/joreilly/FantasyPremierLeague/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PlayerListViewModel.kt)
- Error mapping (C03): no HTTP-status mapping in base; add one mapper in `backend-client` (Ktor `HttpResponseValidator`) and show failures as a sealed `Error` UI state; enums for reasons as in `core-model/.../ConnectionDiagnostics.kt` ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt); [PeopleInSpace: `PeopleInSpaceRepository.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/repository/PeopleInSpaceRepository.kt)
- Unit tests (C20): `commonTest` in `core-data` (e.g. `SyncMergeTest.kt`) with `kotlin-test` and `kotlinx-coroutines-test`; fake HTTP with Ktor `MockEngine` (add); fake server for the login flow ; copy no sample
- Repository (`SOFTWARE_PATTERNS.md`): `AuthRepository` hides the API calls and owns the current user (all fields of the answer) ; copy no sample

## Native additions (not in web)

- Persist the session cookie across app restarts (the browser does this for the web). Optional biometric unlock on start is a later improvement.
- Replace the web's hash redirects with the native navigation stack.

## Tests

- Login flow with a fake server: credentials step, then `requires_2fa`, then verify, ends with a stored user and the Trips tab; a wrong 6-digit code keeps the user on the code step, shows the server message and clears the field; "back" clears the code and password but keeps the username.
- Code field: non-digits are dropped, input is capped at 6, the sixth digit submits automatically.
- Empty username or password does not send a request; a failed login shows the server message, or "Login failed" when it has none.
- Demo: `public-config` with `demo: true` shows the credentials box and the button signs in with them; `demo: false` or a failed call shows no box.
- Launch: `GET /api/auth/me` `200` goes to Trips; `401` goes to sign-in; `503` with `setup_required` goes to setup.
- Sign out calls logout, still signs out when the call fails, purges the cache and zeroes the invitation count.
- Expiry: a `401` during the invitation/notification poll clears the user and returns to sign-in.
- Native addition: kill and restart the process, then `GET /api/auth/me` succeeds without signing in; after logout the stored cookie is gone.
- Autofill: the username field exposes the username hint, the password field the current-password hint, the code field the one-time-code hint; pressing Enter on the keyboard submits.
- Strings test: the sign-in button shows `login.submitting` while busy, the code step shows `totp.hint`, the `totp.expires` countdown and `totp.submitting`, and `totp.back` returns to the credentials step; the demo box shows `login.demo_hint` and `login.demo_signin`.
- Loading state: while `GET /api/auth/me` is pending neither the app UI nor the sign-in screen is visible (web: the text "Loading..." only).
- Sign out clears the current-user store and the API cache, so a second user signing in on the same device never sees the first user's trips.
- Sign-out button test: it is disabled and shows "…" while the logout call is pending; no confirmation and no toast.
- Code field test: the field is focused on step entry, numeric, with placeholder 000000 and disabled while verifying; the button reads "Verify" then "Verifying…".
- Sign-in field test: labels "Username"/"Password" and placeholders "username"/"••••••••"; demo credentials can be selected whole and copied.
- Form test: the sign-in screen shows a username field, a password field and a submit button (web test: "renders the login form").
- Request test: typing "admin" and "secret" and submitting sends one `POST /api/auth/login` with body `{username: "admin", password: "secret"}` (web test: "calls authApi.login with credentials on submit").
- Success test: when the server answers `{id: "1", username: "admin", is_admin: true}` that user is stored as the signed-in user and the app moves to Trips (web test: "sets currentUser and redirects on successful login").
- Whole-answer test: the server answers with `demo: true`, `announcement: "Back at 03:00"` and `carto_api_key: "carto-key"` besides the basic fields; the stored user holds all of them, so the demo banner, announcement and map key work with no relaunch (web test: "passes the server config on the login response into the user store").
- Failed sign-in test: the server answers with an error "Invalid credentials": that text appears in the error box (web test: "shows error message on failed login").
- Code step test: when login answers `{requires_2fa: true}` the code field appears (web test: "switches to TOTP step when requires_2fa is returned").
- Auto-verify test: on the code step, entering "123456" sends one `POST /api/auth/2fa/verify` with `{code: "123456"}` with no further tap (web test: "calls authApi.verify2fa when 6-digit TOTP code is entered").
- Wrong code test: the server refuses the code with "Invalid code"; an error is shown on the code step (web test: "shows TOTP error on failed verification").
- Demo absent test: `public-config` answers `demo: false`: no demo box is shown (web test: "shows nothing on an ordinary install").
- Demo credentials test: `public-config` answers `demo: true, demo_username: "demo", demo_password: "demo1234"`: the box shows exactly "demo" and "demo1234" as the two values (web test: "prints the demo credentials when the server publishes them").
- Demo button test: pressing the demo button sends one `POST /api/auth/login` with `{username: "demo", password: "demo1234"}` (web test: "signs in with those credentials when the button is used").
- Config failure test: `public-config` fails with an error: the username and password fields are still shown and there is no demo box (web test: "still renders the form when the config call fails").
Web tests mirrored: frontend/src/pages/LoginPage.test.ts

## Depends on

- T-001
