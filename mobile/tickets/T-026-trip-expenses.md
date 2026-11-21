# T-026 Trip expenses and balances

## Web source

- `frontend/src/components/TripExpenses.svelte` (script 1-321, markup 338-548)
- `frontend/src/api/client.ts` lines 385-404 (`expensesApi`, `ExpenseWriteData`); types in `frontend/src/api/types.ts` 297-332
- Mounted in `frontend/src/pages/TripDetailPage.svelte` lines 1067-1095 under the "Expenses" heading, below the budget panel (T-027); `defaultCurrency` comes from `settingsApi.get().default_currency` (fallback `EUR`) at lines 66-72
- Guest-removal block: `frontend/src/components/TripPeople.svelte` lines 167-186

## What it does

- No owner, collaborator or demo gate in this component: everyone who sees the section can add, edit and delete any expense. The server decides access.
- On mount three calls run in parallel: `GET /api/trips/{id}/expenses`, `GET .../expenses/participants` and `GET .../expenses/balances`. Each failure is swallowed individually (logged, previous state kept). Loading shows an ellipsis. After every successful mutation all three are re-fetched (`refresh`). The web also has an error-text branch and a refresh-failure alert, but since each call catches its own error they never fire (dead paths).
- Empty state: "No expenses yet. Add your first one below." (only while the add form is closed).
- Row (display): description, then "Paid by NAME · split N ways" plus " · added by USER" when `created_by_username` is set, then the currency code, the amount (integers without decimals, otherwise exactly 2 decimals, locale formatted), an Edit button and a Delete button. The "(you)" marker is NOT in the row; it appears only in the payer select and the people picker (own user row shown as "NAME (you)").
- Totals line "Total: EUR 120 BRL 50" shown when there is at least one expense: one pill per currency, sorted by currency code, summed per currency, never converted. After load and after every change the totals are reported to the trip page (used for the trip header total).
- Add form opens with "+ Add expense". On open: currency = account default, payer = the caller's own participant row, split between = every participant selected, shown as one token per person in participant order (two participants show two tokens). When the participant list did not load, or the caller's own row is not in it, the payer is empty and `paid_by` is omitted from the request (the server then uses the creator). Fields:
  - Payer select (`#new-paid-by`, `TripExpenses.svelte:506-516`): one option per participant, in participant order, value `type:id` (for example `user:1`, `user:2`); no extra "Me" option when the list is loaded, because the caller is already in it (two participants give exactly two options). The caller's own row reads `expenses.you` "NAME (you)" and the others the plain name. Only when the participant list is empty or failed is there a single option `expenses.paid_by_me` "Me" with an empty value. With the caller in the list the select starts on the caller's row and Save sends that row explicitly as `paid_by: {type: "user", id: <own id>}`.
  - Fields: description, amount (number, min 0.01), currency select, payer select, people picker "Split between".
  - Save button is disabled while saving, when the description is blank, the amount is empty/0, or no participant is selected (removing every token disables it). The function also refuses amount <= 0 or NaN silently. Pressing Enter in the description or amount field runs the same checks (`addExpense`) without the button: with every participant removed Enter sends nothing and shows no error (`TripExpenses.svelte:211-215, 312-315`). Removing a token (x on a person in "Split between") excludes that person from the sent `participants`; the sent order is the selection order (initial participant order for the untouched ones).
  - `POST /api/trips/{id}/expenses` with `{ description (trimmed), amount (number), currency, paid_by?: {type, id}, participants: [{type, id}] }` where `type` is `user` or `guest`. On success the form closes, the fields reset and everything is re-fetched; on error the message is shown under the form and the form stays open. Enter submits, Escape closes.
- Edit: Edit button turns the row into an inline form (description, amount, currency, payer, people picker), pre-filled with the expense's description, amount (as the stored number), currency, the payer select set to the expense's own `paid_by` (key `type:id`) and the split picker set to the expense's own participants (`TripExpenses.svelte:241-249`). The payer and participants of the expense stay selectable even if they have since left the trip. Save is disabled only while saving, or when the description or amount is blank; an empty participant set is refused silently inside `saveEdit`. Save sends `PATCH /api/trips/{id}/expenses/{expenseId}` with the FULL set `{ description, amount, currency, paid_by, participants }` (not just changed fields). Enter in the edit description or amount input saves (same silent validation as the Save button; `TripExpenses.svelte:317-320`, `351-364`). On error an alert; Escape or Cancel closes. Opening edit closes the add form and vice versa.
- Add form (`TripExpenses.svelte:294-302`, `312-315`, `535-548`): Cancel and Escape close the add form and clear its error but keep the typed description and amount; opening the form again resets only the currency, payer and split selection (description and amount are cleared only after a successful add). Order on the card: expense list, totals strip, balances section, then the add form or the "+ Add expense" button (hidden while the form is open).
- Delete: confirm text is exactly `Delete expense "DESCRIPTION – AMOUNT CUR"?` with an en dash (U+2013), the amount formatted by the same integer/2-decimal rule as the row, hard-coded English in every language (the locale key `expenses.delete_confirm` is unused and lacks the description and amount; native copies the web text exactly, in English, for parity; localising it is a web bug to report upstream, not a native change; `TripExpenses.svelte:283-285`), then `DELETE .../expenses/{expenseId}`; alert on error.
- Balances: the "Show balances" / "Hide balances" button is rendered only when the balances response has at least one currency. Shown, balances are grouped by currency (heading per currency code); each row is a person with signed net (`+` for >= 0), green when net > 0.005 and red when < -0.005. The web shows per-person net amounts, not "X owes Y" transfers. Tapping rows ticks them (selection is per currency: ticking "me" under EUR does not tick "me" under BRL, and a BRL group with nothing ticked shows no "Combined" line; each row is exposed as a toggle button with a pressed state, true when ticked); a "Combined: +N CUR" line appears for a currency when at least one of its rows is ticked, summing the ticked nets.
- Balances details (`TripExpenses.svelte:323-337`, `442-476`): balances are collapsed by default and the toggle state is not persisted; the ticked-rows selection is per session only (not cleared by a refresh). Currency groups and the person rows inside them keep the order the API returned (only the totals strip is sorted). Each row shows a small checkbox glyph (filled accent square with an accent-on tick when ticked, outlined empty square when not), the plain participant name (no "(you)" marker here) and the signed net amount.
- Guests: the participant list holds the trip owner, accepted collaborators and the trip's guest roster. Guests are added and removed in the People section (`TripPeople`), not here. The add and edit forms offer only that list (the payer select and the "Split between" picker); there is no "add guest" field and no suggestion strip from the user's address book in the expense form, and this section never calls `GET /api/guests`; a person who is in the address book but not on the trip is never mentioned (`TripExpenses.svelte:83-92`). Removing a guest that an expense still names fails with 409 and the People section shows a "blocked" message (T-012). After a guest is added there the page calls `reloadParticipants` (re-fetch of the participants endpoint only, `TripExpenses.svelte:146-152`): the expense list and balances are not fetched again; the new person shows up in the payer select and the picker the next time the add form is opened (an already open form keeps its selection and offers the new person as an unselected suggestion); if that call fails the error is only logged and the previous participant list stays in use (opening the form still shows the old tokens).
- Refresh after a change (`TripExpenses.svelte:125-137`): after a successful add, edit or delete the three reads run again, each failure kept apart. If only the balances call fails (network error), the new expense still appears in the list and the form still closes; the old balances stay.
- The trip card total (T-009) comes from the trip payload (`expenses_total`); the trip page replaces it with the live totals once this section loaded. The budget panel (T-027) is reloaded after every change.
- Locale keys: the description placeholder in the add and edit forms is `expenses.add_placeholder_desc` ("Description (e.g. Hotel, Car…)", `TripExpenses.svelte:356`, `487`); the add form's submit button is `expenses.save` ("Add", shown as `expenses.saving` while sending, line 533); the empty-participant payer option is `expenses.paid_by_me` ("Me", line 511); the row text "split N ways" is `expenses.split_count` ("split {n} ways", `{n}` = number of participants, line 409).

## API calls

- `GET /api/trips/{tripId}/expenses` (expensesApi.list) returns `TripExpense[]` (`id, description, amount, currency, created_by_username, paid_by {type,id,name}, participants [{type,id,name}]`)
- `POST /api/trips/{tripId}/expenses` body `ExpenseWriteData` (expensesApi.create) returns `{ id, ok }`
- `PATCH /api/trips/{tripId}/expenses/{expenseId}` body `Partial<ExpenseWriteData>`; the web always sends all five fields (expensesApi.update)
- `DELETE /api/trips/{tripId}/expenses/{expenseId}` (expensesApi.delete)
- `GET /api/trips/{tripId}/expenses/participants` (expensesApi.participants) returns `[{type, id, name}]`
- `GET /api/trips/{tripId}/expenses/balances` (expensesApi.balances) returns `{ balances: { CUR: [{type, id, name, net}] } }`

## Android notes

Same as shared code.

## iOS notes

Same as shared code.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- ViewModel and UI state (C08): one ViewModel exposing a sealed UI state, not booleans (`SOFTWARE_PATTERNS.md`; `FlowState` in `core-data/.../AppFlowSupport.kt`) with a sealed add/edit state ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt)
- JSON models (C02): `@Serializable` data classes in `core-model` (`Expense`, participants, balances); `Json { ignoreUnknownKeys = true }` already set in `PlatformHttpClient.android.kt` ; copy [PeopleInSpace: `PeopleInSpaceApi.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/remote/PeopleInSpaceApi.kt)
- Repository (`SOFTWARE_PATTERNS.md`): `ExpenseRepository` loads expenses, participants and balances in parallel; totals per currency are a pure function
- Small settings (C05): `multiplatformSettings` is declared in `core-data/build.gradle.kts` but unused: wrap it in a `core-data` repository (default currency pre-fills the add form) ; copy [Confetti: `AppSettings.kt`](https://github.com/joreilly/Confetti/blob/main/shared/src/commonMain/kotlin/dev/johnoreilly/confetti/AppSettings.kt)

## Tests

- Add test: with 3 participants all selected, 90.00 in EUR sends one `POST` with `amount: 90`, 3 participants and the own user as `paid_by`; the list is re-fetched and the row reads "split 3 ways".
- Validation test: Save stays disabled with blank description, empty amount, or no participant selected.
- Totals test: two expenses in EUR and BRL show two pills sorted by code, no combined number; two EUR expenses are summed.
- Edit test: changing the payer sends `PATCH` with description, amount, currency, paid_by and participants (all five); the payer of an expense stays selectable when no longer in the participant list.
- Delete test: confirming sends `DELETE` and refreshes; cancelling sends nothing.
- Balances test: the button is absent when the response has no currencies; with data it lists nets per currency with the sign and colour rule, and ticking two EUR rows shows "Combined" only for EUR.
- Empty test: no expenses and the form closed shows the empty text.
- Edit prefill test: opening edit shows the stored description, amount, currency, payer and participants.
- Edit keyboard test: Enter in the edit description or amount saves; Escape cancels.
- Add form test: Cancel keeps the typed description and amount; reopening resets currency, payer and split only; a successful add clears the text.
- Delete text test: the confirm reads `Delete expense "Dinner – 40 EUR"?` with an en dash, in every app language.
- Balances default test: balances start collapsed; rows keep API order; a ticked row shows the filled glyph and no "(you)" marker.
- Expenses empty test: no expenses and the form closed shows "No expenses yet. Add your first one below." (web test: "shows empty state when there are no expenses").
- Expense row test: an expense "Lunch", EUR 100, paid by "me", two participants shows "Paid by me", "split 2 ways" and the description (web test: "renders expense with paid-by and split info").
- Add defaults test: opening "+ Add expense" with two participants shows two tokens in "Split between"; typing "Taxi" and 40 and saving sends `POST` with description "Taxi", amount 40 and both participants `[{user,1},{user,2}]`; with no signed-in own row in the list `paid_by` is not sent (web test: "defaults the add form to paying for self and splitting between everyone").
- Payer select test (signed in as user 1, participants me and spouse): the payer select has exactly two options with values `user:1` and `user:2`, no extra "Me"; the first reads "me (you)" and the second "spouse"; it starts on `user:1` and Save sends `paid_by: {type: "user", id: 1}`; with an empty participant list the select has one option "Me" with an empty value (web tests: "has one option per person and no extra "Me"", "marks your own row rather than renaming it", "preselects you, and sends you explicitly", "falls back to the "Me" option when the list is unavailable").
- Balances refresh failure test: after a successful add, when the second balances call fails, the new expense "Lunch" still shows in the list (web test: "still shows a newly added expense even if the balances refresh fails").
- Split edit test: tapping the x on the second token sends only the first participant `[{user,1}]`; removing both tokens disables Save and pressing Enter in the amount field sends no request (web tests: "unchecking a participant excludes them from the split", "does not submit when every participant is unchecked, even via Enter").
- Own people only test: with an address-book guest "Alex" who is not on the trip, the add form shows no add-guest field, no suggestion chips and never mentions Alex (web test: "offers only the trip's own people, never the whole address book").
- Delete confirm test: confirming the delete dialog sends `DELETE /api/trips/t1/expenses/e1` (web test: "deletes an expense after confirmation").
- Balances toggle test: with `EUR: me +75, spouse -25`, "Show balances" reveals the rows "+75" and "-25" (web test: "shows per-currency balances when toggled").
- Balances per-currency selection test: with EUR and BRL groups each holding "me", ticking the EUR row makes only that row pressed, shows one "Combined" line (EUR only) and leaves the BRL row unpressed (web test: "selecting a person to combine in one currency does not select them in another").
- Reload participants test: after the guest "Jimmy" is added in People, the section's reload entry point re-reads `GET .../expenses/participants` once more (two calls in total) and opening the add form then shows Jimmy; it does not read the expense list or balances again (one call each in total); when that re-read fails the add form still shows the two previous tokens (web tests: "refetches the trip roster and offers the new guest", "leaves the expenses and balances alone", "keeps the existing list when the refetch fails").
- Header expense total test: a trip with one flight and `expenses_total` {EUR: 420, SEK: 900} shows "EUR 420" and "SEK 900" in the header contents line (web test: "shows the expense total alongside what the trip holds").
Web tests mirrored: frontend/src/components/TripExpenses.test.ts, frontend/src/pages/TripDetailPage.test.ts

## Depends on

- T-010
- T-012
- T-008
