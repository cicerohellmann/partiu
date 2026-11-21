# T-036 Users administration

## Web source

- `frontend/src/pages/UsersPage.svelte` (script 1-105, markup 107-257)
- `frontend/src/App.svelte` line 37 (route `/admin/users`)
- `frontend/src/api/client.ts` lines 146-155 (`usersApi`); `UserListItem` in `frontend/src/api/types.ts` lines 3-50

## What it does

- Admin-only screen `/admin/users`, title "Users". Gate: on mount, if the signed-in user is not `is_admin` the app navigates to `/trips`. This is only a client redirect (the page can render for an instant); the server is the real gate. The screen is reached from settings only for admins (T-032). The top bar has the title "Users" and no back arrow (`backHref` is not passed, `UsersPage.svelte:110`); navigation back is via the tab bar or Settings.
- Demo gate: when the signed-in user has `demo === true` the list still loads and shows, but each row's action buttons are replaced by "Managing accounts is disabled on the demo — everyone signs in to the same shared account." and the Add User section shows the same sentence instead of the form. The server also refuses these writes with 403 on a demo instance.
- States (the "All Users" list and the "Add User" section are both inside the loaded branch, `UsersPage.svelte:113-117, 195-254`): while loading only the loading screen shows, and after a failed load only the error screen shows, so Add User is not available then. After create or delete the list reloads (`load()` sets loading again) and the whole screen, including the form, is replaced by the loading screen until the reload ends. Loading `users.loading` ("Loading users…"); a failed list shows "Failed to load users" with the error text (no Retry button); an empty list shows "No users found.".
- `GET /api/users` lists accounts. Row: username, an "Admin" badge when `is_admin`, a `users.badge_2fa` ("2FA") badge when `totp_enabled`, the forwarding email address when set. The caller's own row shows "(you)" in the action area and has NO Reset PW and NO Delete button; every other row (not demo) has "Reset PW" and "Delete".
- Reset password: "Reset PW" toggles an inline form under the row (a second press on the same row closes it; pressing it on another row moves the form to that row; every open, close or move empties the password field; the form's "Cancel" button also closes it and empties the field; `UsersPage.svelte:144-147, 181-186`). The form has a password field (placeholder "New password (min 8 chars)"), "Save Password" and "Cancel". Save with an empty field or fewer than 8 characters shows the error toast "Password must be at least 8 characters" and sends nothing. Otherwise `PATCH /api/users/{id}` with `{ "new_password": "..." }`; toast of the default (info) type "Password updated" and the form closes; failure shows the server message as an error toast and the form stays. The button reads "Saving…" while the request runs. The reset field is not inside a form, so Enter does not submit: only the "Save Password" button sends (native may add Enter-to-submit). The success toasts on this screen use the default (info) type, as in T-006 (`UsersPage.svelte:66, 83, 98`).
- Delete: `confirm(users.delete_confirm)` (`Delete user "NAME"? This cannot be undone.`), then `DELETE /api/users/{id}`; toast of the default (info) type `users.deleted` (`User "NAME" deleted`) and the list reloads; failure shows an error toast.
- Add user form ("Add User" section): username (placeholder "username", min 2 characters, required), password (placeholder "At least 8 characters", min 8, required), "Forwarding email address (optional)" (email type, placeholder "trips@yourdomain.com"), the word "(optional)" after that label is fixed English text, not translated (`UsersPage.svelte:229`), a "Grant admin privileges" checkbox (off by default) and a "+ Add User" button (`users.btn_adding`, "Creating…", while busy). The length rules come from the browser's form validation; in code the submit is only skipped when the trimmed username is empty or the password is empty. `POST /api/users` with `{ username (trimmed), password, is_admin (always sent as true/false), smtp_recipient_address (trimmed, omitted when empty) }`. Toast of the default (info) type `users.created` (`User "NAME" created`), the form is cleared and the list reloads; failure shows the server message as an error toast and keeps the form.

## API calls

- `GET /api/users` (usersApi.list) returns `[{ id, username, is_admin, smtp_recipient_address, totp_enabled, created_at, ... }]`
- `POST /api/users` body `{ username, password, is_admin, smtp_recipient_address? }` (usersApi.create)
- `PATCH /api/users/{id}` body `{ new_password }` here (the client type also allows `is_admin` and `smtp_recipient_address`, which this page does not send) (usersApi.update)
- `DELETE /api/users/{id}` (usersApi.delete)

## Android notes

Same as shared code.

## iOS notes

Same as shared code.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- ViewModel and UI state (C08): one ViewModel exposing a sealed UI state, not booleans (`SOFTWARE_PATTERNS.md`; `FlowState` in `core-data/.../AppFlowSupport.kt`) (loading, list, reset form open, delete confirm) ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt)
- HTTP client (C01): `KtorAuthApi` in `backend-client/.../backend/client/Clients.kt` (`GET/POST/PATCH/DELETE /api/users`); the session cookie needs the `HttpCookies` plugin (not in base) ; copy [PeopleInSpace: `Koin.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/di/Koin.kt) (`createHttpClient`, no cookies)
- Admin-only gate (C31): the admin flag comes from the signed-in user (T-002); hide the entry for others and check again before the screen opens ; copy no sample
- Repository (`SOFTWARE_PATTERNS.md`): `UsersRepository` hides the API; admin gate is checked before the screen opens

## Tests

- Create test: username "bob" with an 8-character password sends one `POST /api/users` with `is_admin: false` and no `smtp_recipient_address`; a success message names the user, the form clears and the list is reloaded. With the email filled in it is sent trimmed.
- Admin flag test: ticking "Grant admin privileges" sends `is_admin: true`.
- Guard test: the current user's row has no Reset PW and no Delete button and shows "(you)"; a non-admin who opens the screen is sent to the trips screen.
- Demo test: with `demo = true` the rows have no action buttons, the add form is replaced by the locked message and no write request is possible.
- Reset test: a 7-character password shows "Password must be at least 8 characters" and sends no request; 8 characters send `PATCH {new_password}` and show "Password updated".
- Delete test: confirming sends `DELETE` and reloads; cancelling sends nothing; a failure shows the error.
- Badge test: Admin, 2FA and email show on the right rows.
- Load-failure test: a failed `GET /api/users` shows the error screen and no Add User form; during a reload after create or delete the form is not shown.
- Top bar test: the Users screen shows the title "Users" and no back arrow; Enter in the reset-password field sends nothing.
- Loading test: while `GET /api/users` has not answered only the loading screen "Loading users…" is shown (web test: "shows loading screen initially").
- List test: `GET /api/users` returns "alice" and "admin" (the signed-in user): both names appear in the list (web test: "renders user list after loading").
- List error test: `GET /api/users` fails with "Forbidden": the error screen shows "Failed to load users" with the text "Forbidden" (web test: "shows error state when list fails").
- Form test: after loading, the Add User section shows a username field and a password field (web test: "renders the create user form").
- Own row test: in that list the signed-in user's own row shows "(you)" and has no "Reset PW" and no "Delete" (web test: "does not show delete/reset buttons for the current user").
- Delete request test: with the confirmation accepted, tapping "Delete" on the "alice" row (id `user-1`) sends `DELETE /api/users/user-1` (web test: "calls usersApi.delete when delete button is clicked").
- Delete message test: after that delete succeeds a success message is shown (web test: "shows toast on successful delete").
- Create request test: username "newuser" and password "secret123", submit: one `POST /api/users` with `username` "newuser" and `password` "secret123" (web test: "calls usersApi.create when form is submitted").
- Create message test: username "bob" and password "password123", submit: a success message is shown (web test: "shows toast on successful create").
- Create failure test: the server refuses the create with "Username taken": that text is shown as an error message (web test: "shows toast on create error").
- Reset toggle test: "Reset PW" on the "alice" row opens the password form under that row and pressing "Reset PW" again closes it (web test: "toggles the reset password form for non-current users").
Web tests mirrored: frontend/src/pages/UsersPage.test.ts

## Depends on

- T-002
- T-007
