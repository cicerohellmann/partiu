# T-012 Trip people, sharing, guests and the people picker

## Web source

- `frontend/src/components/TripPeople.svelte` (whole file, 1-413): People section, guest roster
- `frontend/src/components/PeoplePicker.svelte` (whole file, 1-297): token combobox reused by expenses (`TripExpenses.svelte:393,519`) and budget (`TripBudget.svelte:222`)
- `frontend/src/pages/TripDetailPage.svelte:392-432` (share state, `loadCollaborators`, `handleShare`, `revokeCollaborator`), `:540-556` (`leaveTrip`), `:566-572` (collaborators loaded with the trip), `:700-830` (Share / Leave buttons and share panel), `:905-925` (People section mounts `TripPeople`)

## What it does

People section (`TripPeople`, heading "People"):
- Props: the trip, the collaborator list (accepted and pending shares, owner-only data), and an `onchange(guests)` callback that reports the roster upward so the trip header guest count and the expense pickers refresh. It is called with the full guest roster after every successful load (first load and every reload after an add or remove), not when the roster call fails (`TripPeople.svelte:94`).
- Loading: shows the raw key text `common.loading` (a web bug: the key is in no locale file; native shows "Loading…") while `GET /api/trips/{id}/guests` and `GET /api/guests` run together. If the trip roster call fails, the error text is shown instead of the list. If only the address book (`GET /api/guests`) fails, it is treated as empty and the section still renders. While loading, the whole People body (list and add form) is replaced by the loading text; a roster error replaces the list and the add form (nothing else shown). Add and remove errors are a separate red line under the list, cleared at the next action (`TripPeople.svelte:80-100, 192-196`).
- List, in this order: the owner (name from `trip.owner_username`, falling back to the current user's username, then the word "Owner") with tag "Owner"; each accepted share with tag "Collaborator"; each pending share with tag "Invited"; each guest on the trip with tag "Guest" and a remove button (x). The owner row is always there, so a solo trip is never empty.
- Collaborator and invited rows are read-only here. A collaborator (non-owner) gets an empty collaborator list, because the shares endpoint is owner-only and the page does not call it for non-owners.
- Add a guest: one text field (placeholder "Name of a travel companion", key `trip_people.add_placeholder`) and an "Add" button (`trip_people.add`, "Add"; shows "…" while sending). It works as a type-ahead:
  - Suggestions are the user's address book (`GET /api/guests`) minus guests already on this trip, filtered by the typed text (trimmed) with accent and case folding (NFD, strip combining marks, lowercase; "joao" finds "João"). The match is "contains", not "starts with": "oa" finds "João" (`TripPeople.svelte:64-67`). Suggestions open on focus and on typing, even with an empty field (whole book); arrow up/down move the highlight (wraps), Escape closes, closes 150 ms after blur. ArrowDown also re-opens the list when it was closed (after Escape or blur) and moves the highlight down, wrapping at the end; ArrowUp moves up, wrapping, and from no highlight goes to the last row; both call preventDefault. Enter always calls preventDefault (a highlighted row adds that guest, otherwise it creates the typed name). Escape closes the list and clears the highlight. Typing clears the highlight (`TripPeople.svelte:145-165`).
  - Picking a suggestion (click, or Enter on a highlighted row) calls `POST /api/trips/{id}/guests` with `{guest_id}` only.
  - Typing a name that is not picked and pressing Enter or "Add" does two calls: `POST /api/guests` with `{name}` (the server reuses an existing guest with the same folded name and returns `created: false`, `id`, and the stored spelling in `name`), then `POST /api/trips/{id}/guests` with `{guest_id: id}`. The client does not check `created` here; it just uses the returned `id`.
  - After a successful add the field is cleared, the suggestions close, and both lists reload.
  - Validation: the Add button is disabled while the field is empty (after trim), while a request runs (shows "…"), or while the typed name (folded, whole-name match, so "JIMMY" matches "Jimmy") is already a guest on this trip; in that case the note `trip_people.already_on_trip` "NAME is already on this trip." is shown, where NAME is the roster guest's stored spelling, not the typed text (typing "JIMMY" shows "Jimmy is already on this trip."). Only the trip's guest roster is checked, not the owner or collaborators. Enter does nothing in those cases and no request is sent (`TripPeople.svelte:74-79, 125, 290, 298-302`).
  - Errors from add are shown as the server's message above the field.
- Remove a guest: the x button (accessibility label `trip_people.remove`, "Remove {name} from this trip") asks for confirmation (`trip_people.remove_confirm`, "Remove NAME from this trip? They stay in your guest list and on any other trip."); on yes `DELETE /api/trips/{id}/guests/{guestId}`, then reload. The button is disabled while that row is busy. On any error the app shows a fixed message "NAME is named by an expense on this trip, so they can't be removed." (not the server text).
- There is no owner, collaborator or demo gate: the add field and the remove (x) buttons are shown to everyone who can open the trip, including a collaborator. The server decides access (`TripPeople.svelte`, no check anywhere; `TripDetailPage.svelte:895-925`).
- A line of hint text under the form explains that guests added here are the people whose expenses can be paid by and split between (key `trip_people.hint`).

Share (trip detail page, owner only, `trip.is_owner !== false`):
- A "Share Trip" button toggles a panel with a username text field (placeholder `trip.share_username_placeholder`, "Enter username") and an "Invite" button (disabled while empty after trim or while sending). It calls `POST /api/trips/{id}/share` with `{username}` (the response carries `status`). On success it shows "✓ Invitation sent to NAME" in the success colour (hard-coded English, no locale key; native copies it exactly in every language and notes it as a web bug to report upstream), clears the field and reloads shares; on failure it shows the server's message in the danger colour. Typing in the field clears both messages. The Invite button label becomes "…" while the request runs. There is no Enter-key handler on the field; only the Invite button submits (native may also submit on keyboard Done) (`TripDetailPage.svelte:406-421, 748-767`).
- `GET /api/trips/{id}/shares` is loaded with the trip (not when the panel opens) and only for owners; a failure is treated as an empty list. The panel lists each share with the username and a status pill (accepted or pending) and a "Revoke" button that calls `DELETE /api/trips/{id}/shares/{userId}` immediately, with no confirmation, and removes the row locally. If the DELETE fails nothing is shown: the rejection is not caught, the row stays and the user sees no message (`TripDetailPage.svelte:423-428`). Revoking (and inviting) does not refetch the trip, so the header people and pending-invite counts (read from the trip payload) keep their loaded values until the trip is reloaded; only the share list and the People section rows change at once.
- With no shares the panel shows the hard-coded English text "No collaborators yet." (not in `en.json`; native copies it exactly in every language and notes it as a web bug to report upstream) (`TripDetailPage.svelte:815-818`).
- The Share, Merge and Delete buttons exist only for owners.

Leave (non-owner only):
- A non-owner sees "Leave trip" instead. It asks `confirm` ("Leave this shared trip? You will lose access."), calls `DELETE /api/trips/{id}/leave`, then navigates to `/trips`. The Leave button is disabled while the request runs (`TripDetailPage.svelte:719-725, 735`). On error an alert with the message is shown. A non-owner also sees "Shared by OWNER" under the trip header.

People picker (`PeoplePicker`, used for expense payer/split and for budget sharing):
- Inputs: list of people (`{type: 'user'|'guest', id, name}`), a selected set of `type:id` keys, a toggle callback, a label, optional hint, and a `display` function (callers use it to render the current user as "(you)" through the `expenses.you` text).
- Chosen people show as tokens with an x button (accessible label "Remove NAME"). The text field placeholder is "Type a name to add someone" when nothing is chosen and "Add someone else…" (`people.add_placeholder`) otherwise.
- At rest (no focus yet, or after Escape) no candidate list is drawn: the control shows only the tokens and the text field. Suggestions = people not yet chosen, filtered with the same accent-and-case folding as a "contains" match on the trimmed typed text ("car" finds "carlos"; "BARB" finds "barbara"; "a" finds every name with an a). They open on focus and on typing, and stay open after a pick, so picking two in a row is quick. A suggestion is picked on press (web: mouse-down, so the field's blur does not close the list first; native: a tap) (`PeoplePicker.svelte:70-76, 168-176`). Arrow up/down highlight, Arrow down from no highlight goes to the first row (so Down, Down, Enter picks the second row). Enter picks the highlighted row, or the only match when the typed text is non-empty (after trim) and matches exactly one person (with an empty field Enter never picks, even when only one person is left); Enter with no highlight and several (or zero) matches does nothing and does not call preventDefault, so the surrounding form's Enter behaviour is untouched (preventDefault only when it picks something). Tokens show `display(person)` (default: the name; the caller may append "(you)"). Mouse-over on a suggestion highlights it; typing resets the highlight and a pick resets it; focus only opens the list and leaves the highlight as it was; a pick clears the query and keeps the list open (`PeoplePicker.svelte:99-106, 154-158`). ArrowDown also opens a closed list; ArrowDown/ArrowUp wrap, and ArrowUp from no highlight goes to the last row. Suggestion rows show `display(person)` (so the current user reads "NAME (you)"), but the typed text is matched against the plain `name`, not the display text, so "you" matches nothing. The token remove button's accessibility label uses the plain name (`PeoplePicker.svelte:86-114, 170`). Escape closes. Chosen tokens are drawn in the order of the `people` list (the trip participant order), not in the order they were picked; Backspace in an empty field removes the last token shown, which is not necessarily the most recently picked (`PeoplePicker.svelte:64, 92-99, 124`).
- Empty dropdown messages: shown only while the list is open (focused or typing, not after Escape) and there are no suggestions: `people.all_added` "Everyone on this trip is already added." when the list of people is not empty and every person is chosen, otherwise `people.no_matches` "No one matches that name." (also for an empty `people` list). At rest nothing is shown (`PeoplePicker.svelte:184-190`).
- The picker holds no selection of its own: a pick or a token remove only calls the toggle callback with the person; a token appears or disappears only when the caller passes a changed `selected` set back in. The `selected` set passed in is never modified (`PeoplePicker.svelte:33-35`).
- Backspace takes back the last token only when the text field is completely empty and at least one token exists; with any text in the field (even spaces) Backspace just edits the text and calls nothing (`PeoplePicker.svelte:109-113`).

## API calls

- `GET /api/trips/{tripId}/guests` (guestsApi.listForTrip)
- `GET /api/guests` (guestsApi.list; address book for the type-ahead)
- `POST /api/guests` `{name}` (guestsApi.create; response `{id, ok, created, name}`)
- `POST /api/trips/{tripId}/guests` `{guest_id}` (guestsApi.addToTrip)
- `DELETE /api/trips/{tripId}/guests/{guestId}` (guestsApi.removeFromTrip)
- `POST /api/trips/{tripId}/share` `{username}` (sharesApi.shareTrip)
- `GET /api/trips/{tripId}/shares` (sharesApi.listTripShares; owner only)
- `DELETE /api/trips/{tripId}/shares/{userId}` (sharesApi.revokeTripShare)
- `DELETE /api/trips/{tripId}/leave` (sharesApi.leaveTrip)

## Android notes

Same as shared code. Invitation links are not part of the backend today: invitations are in-app only.

## iOS notes

Same as shared code.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- ViewModel and UI state (C08): `SOFTWARE_PATTERNS.md` state machine (sealed interfaces, not booleans), `FlowState` in `core-data/.../AppFlowSupport.kt`, `composeApp/.../kmpstartup/FlowStateCard.kt`, androidx `ViewModel`; sealed state for the people list and the add field; Share panel as its own state ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt); [FantasyPremierLeague: `PlayerListViewModel.kt`](https://github.com/joreilly/FantasyPremierLeague/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PlayerListViewModel.kt)
- JSON models (C02): `@Serializable` data classes in `core-model` (e.g. `Sync.kt`), `Json { ignoreUnknownKeys = true }` as in `PlatformHttpClient.android.kt`; guest, collaborator and share models ; copy [PeopleInSpace: `PeopleInSpaceApi.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/remote/PeopleInSpaceApi.kt)
- Error mapping (C03): no HTTP-status mapping in base; add one mapper in `backend-client` (Ktor `HttpResponseValidator`) and show failures as a sealed `Error` UI state; enums for reasons as in `core-model/.../ConnectionDiagnostics.kt`; coded `ApiError` such as `guest_name_taken` mapped to a message ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt); [PeopleInSpace: `PeopleInSpaceRepository.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/repository/PeopleInSpaceRepository.kt)
- Repository (`SOFTWARE_PATTERNS.md`): `PeopleRepository` hides the guest, address-book and share calls ; copy no sample

## Tests

- Roster test: the list always shows the owner first; accepted shares show "Collaborator", pending "Invited", guests "Guest" with a remove button; with no shares and no guests only the owner row shows.
- Suggestion test: with address book `[João, Maria]` and Maria already on the trip, typing "joao" suggests João only; picking it posts `{guest_id}` to the trip endpoint and does not call `POST /api/guests`.
- Create test: typing a new name and pressing Add posts `/api/guests {name}` then `/api/trips/{id}/guests {guest_id}` with the returned id.
- Duplicate test: a name equal (ignoring case and accents) to a guest already on the trip disables Add and shows "NAME is already on this trip."
- Address book failure test: when `GET /api/guests` fails the roster still renders.
- Remove test: declining the confirm sends nothing; accepting sends `DELETE` and reloads; a failing delete shows the fixed "is named by an expense" message, not the server text.
- Share test (owner): sharing posts `{username}`, shows "Invitation sent to NAME" and the share appears with its status; revoking sends `DELETE .../shares/{userId}` without a confirm. A non-owner sees Leave, not Share, and never calls `GET .../shares`.
- Leave test: confirm, then `DELETE .../leave`, then the trip list is shown.
- Picker test: Backspace in an empty field removes the last token; chosen people are not in the suggestions; "joao" finds "João"; the current user is rendered with the "(you)" display text.
- Share panel empty test: with no shares the panel heading is `trip.collaborators` ("Collaborators") and the list shows the hard-coded English text "No collaborators yet."; an accepted share has a green status pill, any other status an amber one (`TripDetailPage.svelte:782-816`).
- Revoke failure test: a failing `DELETE .../shares/{userId}` leaves the row and shows no message.
- Invite UI test: success shows "✓ Invitation sent to NAME" in the success colour; the button reads "…" while sending; Enter in the field sends nothing.
- Leave disabled test: the Leave button is disabled while the request runs.
- Guest keyboard test: Escape then ArrowDown re-opens the guest suggestions; ArrowUp with no highlight goes to the last row; typing clears the highlight.
- No role gate test: a collaborator sees the add field and the remove (x) buttons in People.
- Picker order test: pick B then A from a list ordered A, B: tokens read A, B and Backspace removes B.
- Picker focus test: focusing the field opens the list without resetting the highlight; the typed text "you" matches nothing even though the user row reads "NAME (you)".
- Picker Enter test: Enter with two matches and no highlight does nothing; with one exact match it picks and the form is not submitted.
- People loading test: while the two calls run only the loading text shows; a failing roster call shows only the error text.
- Picker rest test: with six people and none chosen, before the field is focused no suggestion list is drawn; with two chosen the tokens read in `people` order, with the plain names (web tests: "shows no candidate list until you interact with it", "shows what is already selected as tokens").
- Picker search test: focusing the field lists everyone not chosen (six); typing "car" narrows to carlos; "joao" finds "joão"; "BARB" finds barbara (web tests: "opens the full list on focus, so it stays browsable", "narrows the suggestions as you type", "matches accented names typed without accents", "is case insensitive").
- Picker pick test: tapping the second suggestion calls the toggle with barbara; after a pick the typed text is cleared; chosen people are absent from the suggestions (five left when one is chosen); tapping a token's x calls the toggle with that person; the `selected` set passed in is not modified (web tests: "adds someone when their suggestion is clicked", "clears the query after a pick, so the next name starts fresh", "leaves people who are already chosen out of the suggestions", "removes someone through their token", "never mutates the selection it is given").
- Picker empty-message test: with the only person already chosen and the list open the message reads "Everyone on this trip is already added."; typing "zzzz" shows "No one matches that name." (web tests: "says so when everyone has already been added", "says so when nothing matches what was typed").
- Picker keyboard test: Down, Down, Enter picks the second row; typing "ana" (one match) and Enter picks ana without arrowing; typing "a" (several matches) and Enter picks nobody; Escape closes the list; Backspace in an empty field with two tokens takes back the last token shown (barbara); Backspace with "car" typed calls nothing (web tests: "walks the list with the arrow keys and picks with Enter", "picks the only match on Enter without arrowing to it first", "picks nobody on Enter when the query is ambiguous", "closes the list on Escape", "takes back the last token on Backspace in an empty box", "leaves the tokens alone when Backspace is editing actual text").
- People roster test, address book: guests on the trip are the rows with tag "Guest"; a person only in the address book is not a row and appears only as a suggestion once the field is focused; the owner row shows the current user's name when the trip has no `owner_username`; when `GET /api/guests` fails the trip guests still render (web tests: "always lists the owner, so a solo trip is not an empty card", "shows the trip's guests, not the whole address book", "renders the trip even when the address book fails to load").
- People suggestion test: with address book `[João, Lucas]`, typing "joa" offers João only; tapping Lucas posts `POST /api/trips/{id}/guests {guest_id: 2}` and never calls `POST /api/guests` (web tests: "suggests someone you have travelled with as you type, accent-blind", "adds the picked suggestion rather than creating a second guest").
- People create test: typing "Vivian" and tapping "Add" calls `POST /api/guests {name: "Vivian"}`, then `POST /api/trips/{id}/guests {guest_id: 7}` with the returned id (web test: "creates a brand-new guest and puts them on the trip in one go").
- People duplicate test: with guest Jimmy on the trip, typing "JIMMY" shows "Jimmy is already on this trip." (stored spelling) and Add sends nothing (web test: "refuses to add a name already on the trip, whatever its case").
- People remove test: the removal fails with HTTP 409 and the fixed "named by an expense" text shows, not "HTTP 409"; the x asks for confirmation first and sends nothing on no, then `DELETE /api/trips/{id}/guests/{guestId}` on yes (web tests: "explains a refused removal instead of showing the raw error", "asks before taking someone off the trip, and does nothing if you say no").
- People upward test: after loading two guests, the roster callback has been called with a list of two guests (web test: "reports the roster upward so the header count stays live").
- People shares test: accepted share "barbara" shows with tag "Collaborator" and pending share "ana" with tag "Invited" (web test: "shows collaborators and outstanding invitations apart from guests").
- Collaborators load test: opening the trip as an owner requests `GET /api/trips/trip-1/shares` right away, and an accepted collaborator "barbara" is listed in the People section without the Share panel being opened (web test: "loads collaborators with the trip, not when the share panel is opened").
Web tests mirrored: frontend/src/components/PeoplePicker.test.ts, frontend/src/components/TripPeople.test.ts, frontend/src/pages/TripDetailPage.test.ts

## Depends on

- T-010
- T-034
