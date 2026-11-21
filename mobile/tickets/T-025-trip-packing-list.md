# T-025 Packing list

## Web source

- `frontend/src/components/TripPackingList.svelte` (lines 1-210 script and markup)
- `frontend/src/api/client.ts` lines 567-577 (`packingApi`)
- Mounted in `frontend/src/pages/TripDetailPage.svelte` lines 1046-1065 inside a collapsible "Packing list" section (`packingCollapsed`), with no permission check: it renders for everyone who can open the trip.

## What it does

- On mount `GET /api/trips/{id}/packing` loads the items. While loading it shows only an ellipsis ("…"). On a load error it shows the error message in the danger colour and no add row.
- Progress text "N of M packed" (`packing.progress`) shows only when the list is non-empty AND at least one item is checked (N = checked, M = all items). With nothing checked there is no progress line.
- Add: a text input (placeholder "Add an item…") plus an Add button. Enter in the input also adds. Blank (whitespace-only) text is ignored and the button is disabled while blank or while a request is running. The text is trimmed, the input is cleared at once, then `POST /api/trips/{id}/packing` with body `{ "text": "<trimmed>" }`. The response `{id, ok}` is used to append the row locally (unchecked, at the end). On error the text is put back in the input and an alert shows the message.
- Toggle: the shared checkbox updates the row optimistically, then `PATCH /api/trips/{id}/packing/{itemId}` with body `{ "checked": true|false }`. On error the row is reverted and an alert shows the message. Checked rows show struck-through, muted text. The checkbox label is "Mark as packed" / "Mark as unpacked".
- Edit text: tapping the item text switches the row to an inline input (the row keeps its checkbox and replaces the text and the trash button with an autofocused text input, a "✓" primary button and a "✕" secondary button; "✓" is disabled while the save is running or the text is blank; `TripPackingList.svelte:148-161`) (Enter or the tick saves, Escape or the cross cancels). Save is ignored when the text is blank (tick button disabled). Save sends `PATCH .../packing/{itemId}` with `{ "text": "<trimmed>" }`; on error an alert shows the message and the row stays in edit mode.
- Delete: a trash button on each row (only visible on hover or focus where hover exists; always visible on touch) asks `confirm('Delete "NAME"?')`, then `DELETE .../packing/{itemId}`; the row is removed locally on success, alert on error.
- "Remove checked" button: shown only when at least one item is checked. It asks `confirm("Remove checked?")` (the label plus "?"), then `POST .../packing/clear-checked` (no body). On success the checked rows are removed locally. Alert on error.
- Empty state (no items): "Your packing list is empty. Add your first item below." The add row is still shown.
- There is no owner, collaborator or demo gate in this component; every viewer can add, tick, edit and delete. The server decides access.
- Locale keys: the add input placeholder is `packing.add_placeholder` ("Add an item…") and the Add button is `packing.add` ("Add", `TripPackingList.svelte:192-201`). The delete confirm is `packing.delete_confirm` (`Delete "{name}"?`, line 100, `{name}` = the item text).

## API calls

- `GET /api/trips/{tripId}/packing` (packingApi.list) returns `PackingItem[]` (`id, trip_id, text, checked` as 0/1, `sort_order, created_by, created_at`)
- `POST /api/trips/{tripId}/packing` body `{ text }` (packingApi.create) returns `{ id, ok }`
- `PATCH /api/trips/{tripId}/packing/{itemId}` body `{ text? , checked? }`, one field per call in practice (packingApi.update)
- `DELETE /api/trips/{tripId}/packing/{itemId}` (packingApi.delete)
- `POST /api/trips/{tripId}/packing/clear-checked` no body (packingApi.clearChecked)

## Android notes

Same as shared code.

## iOS notes

Same as shared code.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- ViewModel and UI state (C08): one ViewModel exposing a sealed UI state, not booleans (`SOFTWARE_PATTERNS.md`; `FlowState` in `core-data/.../AppFlowSupport.kt`) with optimistic toggle, rolled back on error ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt)
- Optimistic update with rollback (C30): toggle at once, call the server, restore the old state on error ; copy [Confetti: `ConfettiRepository.kt`](https://github.com/joreilly/Confetti/blob/main/shared/src/commonMain/kotlin/dev/johnoreilly/confetti/ConfettiRepository.kt) (`optimisticUpdates`; hand-written rollback: no sample)
- Offline cache (C04): `core-data` KStore repositories (`KStoreRepositories.kt`, `StoreFactory.kt`) fit the packing items of one trip; for many rows or queries add a SQL database ; copy [PeopleInSpace: `PeopleInSpace.sq`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/sqldelight/com/dev/johnoreilly/peopleinspace/PeopleInSpace.sq) (SQLDelight) if SQL is chosen
- Repository (`SOFTWARE_PATTERNS.md`): `PackingRepository` hides the API and the optimistic update

## Tests

- Toggle test: ticking an item sends `PATCH` with `{checked: true}`, the row updates at once and the "N of M packed" line appears; a failing PATCH reverts the row and shows the error.
- Progress test: with no item checked there is no progress line; with 2 of 5 checked it reads "2 of 5 packed".
- Add test: whitespace-only text sends nothing; "Socks " sends `POST {text: "Socks"}`, clears the input and appends the row; a failing POST restores the text.
- Edit test: tapping the text and saving "Shoes" sends `PATCH {text: "Shoes"}`; a blank text cannot be saved.
- Delete test: after confirming, `DELETE` is sent and the row disappears; cancelling the confirm sends nothing.
- Clear test: "Remove checked" is hidden with nothing ticked; with 2 of 5 ticked and confirmed it sends `POST clear-checked` and leaves 3 items.
- Empty test: no items shows the empty text and the add row.
- Edit row test: in edit mode the input is focused, "✓" is disabled while the text is blank or a save is running, and the trash button is not shown.

## Depends on

- T-010
- T-007
