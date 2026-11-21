# T-031 Inbox: invitations and notifications

## Web source

- `frontend/src/pages/NotificationsPage.svelte` (script 1-68, markup 70-139)
- `frontend/src/pages/InvitationsPage.svelte` (1-70; no route uses it, see below)
- `frontend/src/lib/invitationStore.ts` (badge counts and `refreshInvitationCount`)
- `frontend/src/App.svelte` lines 38-39 (routes), 55-90 (badge polling and badge clearing)
- `frontend/src/api/client.ts` lines 228-240 (`sharesApi` invitations) and 345-374 (`notificationsApi` inbox)

## What it does

- Screen `/notifications`, title is the string `notifications.title` ("✉ Inbox" in English, with the envelope); the nav entry label is `nav.notifications` ("Inbox"); do not rename it "Notifications". The route `/invitations` mounts the same screen. `InvitationsPage.svelte` (a standalone list with a Back link to trips, a Retry button on error and the text "No pending invitations") is not mounted by any route; do not build it (it uses `invitations.title`, "Trip Invitations", for its top bar and loading text, `InvitationsPage.svelte:41,45`; the live screen never shows that string). No permission gate beyond being signed in.
- Load: `GET /api/trips/invitations` and `GET /api/notifications/inbox` in parallel. While loading it shows the loading screen with the text of `nav.notifications` ("Inbox"; `NotificationsPage.svelte:77`). If either fails the whole body is replaced by the error message in the danger colour (no Retry button).
- After loading, only if at least one notification is unread: `POST /api/notifications/inbox/read-all`, all rows are then shown as read locally, and the badge is refreshed. If nothing is unread, read-all is not called. The local list is flipped to read inside the same load, before the first render (`NotificationsPage.svelte:24-28`), so the unread highlight and unread dots are never shown on first paint; the nav badge goes to 0 through the shared count store. `read-all` runs inside the same try block as the two GETs: if it fails, the whole body is replaced by the error message (the already loaded invitations and notifications are not shown) and the badge is not refreshed. A failure of the later badge refresh is swallowed (`NotificationsPage.svelte:23-33`).
- Invitations block (only when there is at least one): section label "Invitations"; one highlighted card per invitation with a mail icon and "**INVITER** invited you to **TRIP NAME**", an Accept and a Reject button. Accept sends `POST /api/trips/invitations/{shareId}/accept`, Reject sends `POST .../{shareId}/reject` (no body). Afterwards the card is removed locally and the badge counts are refreshed. Neither call has a confirmation or error handling in the web (on failure nothing changes and nothing is shown). Accept does not itself reload the trips list; the trip shows up the next time the trips list loads.
- Activity block (only when there is at least one notification): label "Activity" is shown only when invitations are also present. Each card shows an icon by `type` (`new_flight` plane, `failed_parse` warning sign, `invitation` envelope, anything else a bell), the `title`, the `body` when not empty, the creation date (short month, day, hour, minute in the device locale), and unread ones are highlighted. A `notifications.view` ("View →") link to `notif.url` is shown unless the url is empty, `/` or `/#/`. `url` is a web hash link written by the server, for example `/#/trips/12` (`backend/notifications/reminder_job.py:101`); the web renders it as a plain link in the same tab (`NotificationsPage.svelte:119-121`). Native maps `/#/trips/{id}` to the trip screen and ignores any other value it cannot map. A delete "x" button sends `DELETE /api/notifications/inbox/{id}` and removes the row on success (no confirmation, no error message).
- Empty state when there are no invitations and no notifications: a bell, "You're all caught up", "No invitations or notifications yet."
- Navigation badge (T-006) = number of pending invitations + unread notifications. `refreshInvitationCount` calls `GET /api/trips/invitations` and `GET /api/notifications/inbox/count` (returns `{ unread }`) when a user is signed in. App.svelte runs it after sign-in check, on every navigation and every 30 seconds. Offline or 5xx errors keep the last counts; a 401 clears the user and the counts and goes to the sign-in screen. App.svelte also calls `POST /api/notifications/badge/clear` (and clears the OS app badge) on load and whenever the page becomes visible while signed in.
- `markRead` (`POST /api/notifications/inbox/{id}/read`) is defined in the client but nothing calls it.

## API calls

- `GET /api/trips/invitations` (sharesApi.listInvitations) returns `[{ id, trip_id, trip_name, invited_by_username, created_at }]`
- `POST /api/trips/invitations/{shareId}/accept` (sharesApi.acceptInvitation)
- `POST /api/trips/invitations/{shareId}/reject` (sharesApi.rejectInvitation)
- `GET /api/notifications/inbox` (notificationsApi.inbox) returns `[{ id, type, title, body, url, read, created_at }]`
- `GET /api/notifications/inbox/count` (notificationsApi.inboxCount) returns `{ unread }`
- `POST /api/notifications/inbox/read-all` (notificationsApi.markAllRead)
- `DELETE /api/notifications/inbox/{id}` (notificationsApi.deleteNotification)
- `POST /api/notifications/badge/clear` (notificationsApi.clearBadge), from App.svelte on load and when the app becomes visible
- Defined but not used by any screen: `POST /api/notifications/inbox/{id}/read` (notificationsApi.markRead)

## Android notes

Same as shared code.

## iOS notes

Same as shared code.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- ViewModel and UI state (C08): one ViewModel exposing a sealed UI state, not booleans (`SOFTWARE_PATTERNS.md`; `FlowState` in `core-data/.../AppFlowSupport.kt`) (loading, empty, invitations plus activity) ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt)
- App-icon badge (C28): the badge counts only invitations plus unread notifications from the API (T-006); remote push itself is T-035 ; copy no sample
- Repository (`SOFTWARE_PATTERNS.md`): `InboxRepository` hides invitations, notifications, accept, reject and read-all; the badge is derived in one place

## Tests

- Accept test: accepting sends `POST /api/trips/invitations/{id}/accept`, removes the card and lowers the badge count (a re-fetch of invitations and inbox count).
- Reject test: rejecting sends the `reject` call and removes the card.
- Read test: opening the screen with at least one unread notification calls `read-all` once, shows all rows as read and sets the unread badge part to 0; with no unread notification `read-all` is not called.
- Read-all failure test: a failing `POST .../read-all` shows only the error text.
- View link test: `/#/trips/12` opens trip 12; `/` and `/#/` show no View link.
- Activity label test: the "Activity" label shows only when invitations are present as well.
- View link test: a notification with url `/` or empty has no View link; one with a trip url has.
- Delete test: the x sends `DELETE` and removes the row.
- Empty test: no invitations and no notifications shows "You're all caught up".
- Error test: a failing load shows the error message in place of the lists.
- Badge test: the badge equals pending invitations plus unread count; a 401 during refresh sends the user to sign-in; a 5xx keeps the last counts.
- Dots test: opening the inbox with unread notifications renders every row as read (no unread highlight on first paint) and the nav badge unread part is 0.

## Native additions (not in web)

- Use `POST /api/notifications/inbox/{id}/read` when a single notification is opened from a push (the web client defines it but never calls it).
- Tapping a push notification (T-035) opens this screen or the related trip.

## Depends on

- T-006
- T-012
