# T-034 Settings: trusted users, trash, activity and guest address book

## Web source

Owned part of `frontend/src/pages/SettingsPage.svelte` (the other parts belong to T-032, T-033 and T-035; the split is listed in T-032):

- Trusted users `:1742-1777`, script `:652-688`
- Guest address book `:1786-1900`, script `:690-796`
- Trash and activity are mounted at `:1782-1783` as their own components:
  - `frontend/src/components/TrashPanel.svelte` (whole file)
  - `frontend/src/components/ActivityPanel.svelte` (whole file)

On the page the order is: trusted users, trash, activity, guests.

## What it does

Gates: none of these sections is admin- or demo-gated on the web; every signed-in user sees them and they act on the caller's own data. Each section loads and fails on its own; a failure in one does not affect the rest of the page.

Trusted users:
- Title "Trusted Users" with the description "Invitations from trusted users are accepted automatically." So adding someone means that when they share a trip with you, the invitation is accepted without a prompt (T-031).
- Loaded with `GET /api/settings/trusted-users` (rows `{user_id, username, created_at}`); a load failure is ignored (list stays empty). Shows a loading text, then "No trusted users yet." or the list of usernames, each with a "Remove" button.
- Add: a text field (placeholder "Username") and an "Add" button (`settings.add_trusted_user` "Add"; disabled while a request runs; an empty or blank field does nothing; Enter in the field does nothing on the web, only the Add button submits, unlike the guest field; native may also submit on keyboard Done). On the web the loading line shows the raw text `settings.failed_emails_loading` while `GET /api/settings/trusted-users` runs (the key exists in neither locale file and `init()` in `lib/i18n.ts` sets no handleMissingMessage, so svelte-i18n prints the key itself; the same line shows again during the reload after an add; `SettingsPage.svelte:1748-1764`). See "Native additions" below for what native shows. The error line is not cleared until the next add attempt. The username placeholder "Username" and the empty text "No trusted users yet." are hard-coded English with no locale key; native copies them exactly in every language and notes them as web bugs to report upstream. `POST /api/settings/trusted-users` with `{username}` (trimmed); on success the field is cleared and the list reloaded; on failure the server message (for example an unknown user) is shown in red above the list.
- Remove: `DELETE /api/settings/trusted-users/{userId}` immediately, no confirmation, and the row is removed locally. A failure is not handled or shown.

Trash (`TrashPanel`):
- Title "Trash" with the text "Deleted trips and flights are kept here with everything that was on them. Restore puts them back; a deleted booking can also simply be imported again.". `GET /api/trash` on mount: `trash.loading` ("Loading trash…") then "Nothing in the trash." when empty. Load, restore and purge errors all show the error message in one red line above the list (the list stays visible). Web bug: when the first load fails the list is empty and not loading, so the web shows the red error line AND "Nothing in the trash." under it (`TrashPanel.svelte:82-89`), which wrongly claims the trash is empty; native fixes this (see Native additions).
- Each item (`{id, kind: 'trip'|'flight', entity_id, label, summary, deleted_at}`) shows the kind ("Trip" or "Flight"), the label, a detail line and "deleted DATE" (day and month). Detail line: for a flight the departure day and month; for a trip the date range, and counts "N flight(s)", "N stay(s)", "N expense(s)" when above zero, and a star, a space and the rating exactly as the server sends it when it is not 0 or missing ("★ 4.5", "★ 4"), joined with " · " (a middle dot with a space on each side, `TrashPanel.svelte:61`); the date range inside the first part uses an en dash, e.g. "12 Mar – 20 Mar".
- "Restore": `POST /api/trash/{id}/restore` (no confirmation). The answer `{kind, entity_id, label, restored, skipped}` drives a status line: `trash.restored` (`"LABEL" restored.`) or, when the sum of `skipped` values is above zero, `trash.restored_with_skips` (`"LABEL" restored; N item(s) already existed and were left as they are.`) The item leaves the list. The restore notice and the error line are independent: neither clears the other, the notice stays until the next restore replaces it, the error stays until the next list reload, and the notice is drawn above the error (`TrashPanel.svelte:26-47, 77-83`). Purge success shows nothing. Buttons of that row are disabled while its request runs.
- "Delete permanently": a `confirm` (`trash.purge_confirm`) `Delete "LABEL" permanently? This cannot be undone.`, then `DELETE /api/trash/{id}`; the item leaves the list.

Activity (`ActivityPanel`):
- Title "Activity" with the description `activity.desc` ("What has been done to your trips: deletions, restores, merges, regroups and full syncs."). `GET /api/activity?limit=100` on mount: `activity.loading` ("Loading activity…") then "Nothing recorded yet." when empty; a failure shows the error message in red instead of the list. A scrolling list, newest as the server returns them, each entry starts with `<short month and day in the app locale> <HH:MM 24-hour, no AM/PM, device time zone>` of `created_at` (the same helpers as T-008, `formatDayMonth` + `formatTime`; `ActivityPanel.svelte:5, 63`), e.g. `12 Mar 14:05`, in muted tabular figures, then the sentence.
- The sentence is chosen by `action` (key `activity.` + action with the dot replaced by an underscore): `trip.trashed` -> `activity.trip_trashed` ("Trip \"LABEL\" moved to the trash"), `trip.restored` -> `activity.trip_restored` ("Trip \"LABEL\" restored from the trash"), `trip.purged` -> `activity.trip_purged` ("Trip \"LABEL\" deleted permanently"), `flight.trashed` -> `activity.flight_trashed` ("Flight LABEL moved to the trash"), `flight.restored` -> `activity.flight_restored` ("Flight LABEL restored from the trash"), `flight.purged` -> `activity.flight_purged` ("Flight LABEL deleted permanently"), `trips.merged` -> `activity.trips_merged` ("Trip \"SOURCE\" merged into \"LABEL\""; SOURCE is `details.source_name`), `trips.regrouped` -> `activity.trips_regrouped` ("Trips regrouped from scratch (auto-generated trips rebuilt)"), `sync.full` -> `activity.sync_full` ("Full email sync started"), `sync.rescan` -> `activity.sync_rescan` ("Parser updated (FROM → TO): mail since SINCE re-read"; uses `details.from_version`, `details.to_version`, `details.since`). Any other action shows `activity.unknown` ("ACTION LABEL"). `label` is the entry's label (empty if null). The web does not show who did an action.

Guest address book (the user's own travel companions without an account):
- Title "Guests" with the description "Non-account trip companions you can add as expense payers or participants." `GET /api/guests` (rows `{id, name, created_at}`); load failure ignored. Shows `settings.guests_loading` ("Loading guests…"), then "No guests yet." or the list, each row with the name and "Edit" and "Delete" buttons.
- Add: a text field (placeholder "Guest name"; Enter also submits) and `settings.add_guest` ("Add"; disabled while empty or in flight). `POST /api/guests` with `{name}` (trimmed). If the answer has `created: true`, the new guest is added to the list, kept sorted by name (locale compare). If `created: false` the name already named one of the user's guests (the server compares folded names and returns the existing one) and nothing is added; a note "NAME was already in your guests." (NAME is the stored spelling returned) is shown. The field is cleared either way. Errors show the server message in red.
- Rename: "Edit" turns the row into a text field filled with the guest's current name, with "Save" and "Cancel" (Enter saves, Escape cancels; Save is disabled for a blank name). `PATCH /api/guests/{guestId}` with `{name}` (trimmed); the returned guest replaces the row and the list is re-sorted. Only one row is editable at a time: pressing Edit on another row switches the edit to it and abandons the first row's unsaved edit without asking (`SettingsPage.svelte:740-751`). If the server answers with error code `guest_name_taken` (with params) the message is `settings.guest_name_taken_error` ("You already have a guest named NAME."); the two guests are not merged. Other errors show the server message.
- Delete: "Delete" sends `DELETE /api/guests/{guestId}` at once (no first confirmation). Outcomes:
  - success: the row is removed.
  - error code `guest_in_use` (an expense names the guest): message `settings.guest_in_use_error` ("Guest NAME is used in N existing expense(s)"); this cannot be forced.
  - error code `guest_on_trips` (the guest is on trip rosters): message `settings.guest_on_trips_error` ("NAME is on N trip(s): TRIPS. Deleting them takes them off those trips.") and a "Delete anyway" button appears; pressing it sends `DELETE /api/guests/{guestId}?force=true`. The button is cleared as soon as any other action starts (edit, add, another delete).
  - any other error (an error without a known code, for example a plain "Guest not found"): that message as it is. While the delete is refused the row stays in the list.
  The error codes come in the error body's `detail` object (`error`, `message`, `params`) and are read through `ApiError` in `client.ts`.
- Messages (error, note) clear when a new action starts.

## API calls

- `GET /api/settings/trusted-users` (sharesApi.listTrustedUsers)
- `POST /api/settings/trusted-users` `{username}` (sharesApi.addTrustedUser)
- `DELETE /api/settings/trusted-users/{userId}` (sharesApi.removeTrustedUser)
- `GET /api/guests` (guestsApi.list)
- `POST /api/guests` `{name}` (guestsApi.create; answer `{id, ok, created, name}`)
- `PATCH /api/guests/{guestId}` `{name}` (guestsApi.update; answer is the guest)
- `DELETE /api/guests/{guestId}` and `DELETE /api/guests/{guestId}?force=true` (guestsApi.delete)
- `GET /api/trash` (trashApi.list)
- `POST /api/trash/{id}/restore` (trashApi.restore)
- `DELETE /api/trash/{id}` (trashApi.purge)
- `GET /api/activity?limit=100` (activityApi.list)

## Android notes

Same as shared code.

## iOS notes

Same as shared code.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- ViewModel and UI state (C08): one ViewModel exposing a sealed UI state, not booleans (`SOFTWARE_PATTERNS.md`; `FlowState` in `core-data/.../AppFlowSupport.kt`) per panel (trusted users, trash, activity, guests) ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt)
- Offline cache (C04): `core-data` KStore repositories (`KStoreRepositories.kt`, `StoreFactory.kt`) fit the trash and activity lists only if shown offline; otherwise plain API calls; for many rows or queries add a SQL database ; copy [PeopleInSpace: `PeopleInSpace.sq`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/sqldelight/com/dev/johnoreilly/peopleinspace/PeopleInSpace.sq) (SQLDelight) if SQL is chosen
- Repository (`SOFTWARE_PATTERNS.md`): `TrustedUsersRepository`, `TrashRepository`, `ActivityRepository` hide the API; restore and purge are use cases

## Native additions (not in web)

- Trash load failure: when `GET /api/trash` fails the web also prints "Nothing in the trash." under the red error line (a false statement). Native shows only the error (with a way to retry) and no empty text.
- Trusted-users loading line: the web prints the raw key `settings.failed_emails_loading`, which is missing from every file in `frontend/src/locales/` (web bug to report upstream; `SettingsPage.svelte:1762`). Native shows the existing generic loading text, key `flight.btn_loading` ("Loading…", `en.json:257`; there is no `common.loading` key, so native may add one and use it here), in every language.

## Tests

- Trusted test: adding an unknown username shows the server error above the list and leaves the list unchanged; adding a known one clears the field and shows them; removing deletes at once and drops the row.
- Guest add test: a new name is inserted in sorted position; a name the server answers with `created: false` adds no row and shows "NAME was already in your guests." with the stored spelling.
- Guest rename test: a `guest_name_taken` error shows "You already have a guest named NAME."; success replaces and re-sorts the row; blank names cannot be saved.
- Guest delete test: a `guest_on_trips` error shows the message and "Delete anyway"; pressing it sends `?force=true` and removes the row; a `guest_in_use` error shows the message and no "Delete anyway"; starting an edit or add clears the "Delete anyway" button.
- Trash test: empty shows "Nothing in the trash."; restore posts to `/api/trash/{id}/restore`, removes the item and shows the restored (or "already existed") line; purge asks first and declining sends nothing; an API error shows one red line and keeps the list.
- Activity test: known actions render their sentence, unknown actions render "ACTION LABEL"; empty shows "Nothing recorded yet."; a failing load shows the error and no list.
- Trash message test: after a restore notice, a failing purge shows the error and keeps the notice (notice above error); a later successful purge keeps the error; a purge shows no success message; the detail line of a trip with 2 flights and 1 stay reads "12 Mar – 20 Mar · 2 flight(s) · 1 stay(s)" (the English strings are `{n} flight(s)` and `{n} stay(s)`, with the literal "(s)", `en.json:551-552`; a trip with a rating of 4.5 adds " · ★ 4.5").
- Trusted text test: the placeholder reads "Username" and the empty list reads "No trusted users yet." in every language.
- Trusted Enter test: pressing Enter in the username field sends nothing; only Add submits; the loading line reads "Loading…".
- Guest edit switch test: pressing Edit on a second guest while the first is being edited moves the edit to the second row and drops the first row's unsaved text without a prompt.
- Activity text test: each of the ten known actions renders its own sentence with the label, source and version values filled in.
- Activity time test: an entry created at 14:05 on 12 March shows `12 Mar 14:05` in en, with a 24-hour time and no AM/PM.
- Trash empty test: `GET /api/trash` returns an empty list: "Nothing in the trash." is shown (web test: "shows the empty state when nothing is trashed").
- Trash item test: one trashed trip `{id: 7, kind: "trip", label: "Stockholm → Reykjavík (Apr 2026)", summary: {start_date: "2026-04-02", end_date: "2026-04-08", flight_count: 4, rating: 4.5}}` shows its label, "4 flight(s)" and "★ 4.5" (web test: "lists a trashed trip with its label and contents").
- Trash restore test: tapping "Restore" sends `POST /api/trash/7/restore`; the answer `{restored: {trips: 1}, skipped: {flights: 2}}` removes the row and shows a status line holding the restored-with-skips sentence with the number 2 (web test: "restore calls the API, removes the row and reports skipped items").
- Trash purge decline test: tapping "Delete permanently" and declining the confirmation sends no `DELETE /api/trash/7` and the row stays (web test: "purge asks first and does nothing when declined").
- Trash load failure test: `GET /api/trash` fails with "boom": an error line containing "boom" is shown and the screen does not stay on "Loading trash…" (web test: "surfaces an API failure instead of hanging on loading"); native shows no "Nothing in the trash." beside that error.
- Activity sentences test: three entries, `sync.rescan` (details from_version "33", to_version "35", since "2026-06-18", no label), `trips.merged` (label "Target", details.source_name "Source") and `trip.trashed` (label "Reykjavík") each render their own sentence: the trashed trip names "Reykjavík", the merge names "Source" and "Target", the rescan names versions 33 and 35 and has no label (web test: "renders each known action through its own string").
- Activity unknown test: an entry with action `something.new` and label "x" renders the generic "something.new x" line (web test: "falls back to a generic line for an action it does not know").
- Activity empty test: `GET /api/activity?limit=100` returns an empty list: "Nothing recorded yet." is shown (web test: "shows the empty state").
- Guests list test: `GET /api/guests` returns one guest "Grandma": she is listed (web test: "renders existing guests").
- Guests empty test: `GET /api/guests` returns an empty list: "No guests yet." is shown (web test: "shows empty state when there are no guests").
- Guest add request test: with no guests, typing "Grandpa" and tapping "Add" sends `POST /api/guests` `{name: "Grandpa"}`; the answer `{id: 2, created: true, name: "Grandpa"}` puts "Grandpa" in the list (web test: "adds a guest and shows it in the list").
- Guest rename request test: "Edit" on "Grandma" shows a field holding "Grandma"; changing it to "Grandpa" and tapping "Save" sends `PATCH /api/guests/1` `{name: "Grandpa"}` and the row reads "Grandpa" (web test: "renames a guest").
- Guest delete request test: tapping "Delete" on "Grandma" sends `DELETE /api/guests/1` without `force`; the row disappears (web test: "deletes a guest").
- Guest reuse test: "Grandma" exists; typing "grandma" and tapping "Add" gets `{id: 1, created: false, name: "Grandma"}`: no second row is added, the "was already in your guests" note is shown, and the name appears once in the list (web test: "reuses the existing guest instead of listing the same person twice").
- Guest on-trips test: a delete refused with code `guest_on_trips` (params name "Grandma", count 1, trips "Lisbon") shows the on-trips message and keeps the row; "Delete anyway" then sends `DELETE /api/guests/1?force=true` and the row disappears (web test: "names the trips a guest is on before deleting them, then deletes on confirmation").
- Guest in-use test: a delete refused with code `guest_in_use` (params name "Grandma", count 3) shows "Guest Grandma is used in 3 existing expense(s)" from the locale string, not the server's raw text (web test: "shows a translated error message when delete fails because the guest is in use").
- Guest plain error test: a delete that fails with a plain error "Guest not found" shows exactly that text (web test: "falls back to the raw error message for errors without a known code").
Web tests mirrored: frontend/src/components/TrashPanel.test.ts, frontend/src/components/ActivityPanel.test.ts, frontend/src/pages/SettingsPage.test.ts

## Depends on

- T-012
- T-032
