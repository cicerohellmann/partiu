# T-027 Trip budget

## Web source

- `frontend/src/components/TripBudget.svelte` (1-300 script and markup): panel, form, save and clear
- `frontend/src/lib/utils.ts:640-655` (`BUDGET_WARN_AT`, `budgetLevel`), `:619-632` (`formatCurrencyTotals`)
- `frontend/src/lib/currencies.ts` (lines 11-17, the currency codes offered)
- `frontend/src/pages/TripDetailPage.svelte:262-282` (header chip `budgetChip`, `budgetIsShared`), `:628-640` (chip in the trip header), `:1073-1096` (panel inside the Expenses section, hint line, reload after expense changes)
- `frontend/src/components/TripCard.svelte:160-178` (alarm on the trip card)

## What it does

Ownership model (from `frontend/src/api/client.ts:521-529` and the `TripBudget` type): a budget belongs to a person, not to a trip. `GET`, `PUT` and `DELETE /api/trips/{id}/budget` read and write the caller's own row; the response also lists `members` (everyone the budget is shared with, owner included, users or guests), `owner_user_id` and `owner_username`. A member of a shared budget sees it and may edit or clear it. `amount` and `currency` are null when there is no budget. `spent` and `uncounted` are computed by the server; the client only displays them.

Panel (inside the trip's Expenses section, above the expense list):
- Load: `GET .../budget` on mount and again after every change to the expense list. There is no loading indicator: until the first `GET .../budget` answers, `budget` is empty, so the panel shows the "No budget set for this trip." row with the "Set a budget" button (tapping it opens the form with no amount) (`TripBudget.svelte:70-80, 298-306`). If it fails, only the server's error text is shown, in red, and nothing else.
- No budget: the text "No budget set for this trip." and a "Set a budget" button that opens the form.
- Budget present: "SPENT of AMOUNT" (for example "EUR 120 of EUR 800"; whole numbers without decimals, otherwise two decimals) and an "Edit" button.
  - If the budget has members other than the current user: a line "Shared with NAME, NAME". If the viewer is not the owner (`owner_user_id` differs from the current user's id) that line also gets "· set by OWNER_NAME". The "set by" text appears only inside this line.
  - Progress bar (bar width capped at 100 percent; the figure itself keeps counting). Level from `budgetLevel`: no level for an amount of zero or none; `over` when spent / amount is 1 or more; `near` from 0.8 (`BUDGET_WARN_AT`) up to below 1; `under` below 0.8. The bar colour follows the level. ratio = spent / amount (0 when amount <= 0). Colour strength (intensity, clamped 0..1): under = ratio / 0.8; near = (ratio - 0.8) / 0.2; over = (ratio - 1) / 0.3 (saturates at 130 percent). The fill mixes the band colour (success, warning, danger) into the track colour at round(35 + intensity * 65) percent, never below 35 so the bar is always visible. Bar width = min(100, round(ratio * 100)) percent. The track is exposed as a progressbar with min 0, max = amount, now = spent. The root carries the level (under, near, over); "under" is used when none can be computed (`TripBudget.svelte:94-127`, `253-283`; `lib/utils.ts:645-655`).
  - Note under the bar (`TripBudget.svelte:285-294`): when spent equals the amount exactly (remaining is 0, whatever the level), "Budget spent in full" instead of "EUR 0 over budget"; when over, "AMOUNT over budget" where AMOUNT is the overshoot in the budget currency (spent 1600 of 800 gives "EUR 800 over budget", while the bar stays at 100 percent); otherwise "AMOUNT left".
  - Text colours (`TripBudget.svelte:383-392`): the note text is muted for under, warning colour for near and danger colour for over; the bold spent figure also turns danger colour when over. The load error is shown in the danger text colour.
  - "Not counted:" followed by one pill per currency (for example "USD 20") for spend in currencies other than the budget's, sorted alphabetically by currency code (`BRL 240` before `SEK 900`) and formatted like every other total (`formatCurrencyTotals`, `lib/utils.ts:619-632`: whole numbers without decimals, otherwise two decimals, with the device locale's thousands grouping); shown only when there is any. No conversion happens anywhere; the amounts are never added to the bar.
- A hint line under the panel says what is counted: "Counts your share of each expense — an expense split four ways counts a quarter of it, whoever paid." for a solo budget, or "Counts everyone it is shared with together — an expense split four ways between four people counts half of it to a budget two of them share, whoever paid." when the budget has more than one member. The server decides what `spent` contains: the combined share of all members, not what anyone paid.
- Trip header chip (`TripDetailPage.svelte:267-276, 635-644`): when the budget answer has both an `amount` and a `currency` (so exactly when a budget exists) the trip header's summary line shows `🎯 {spent} / {amount}`, each side as `formatCurrencyTotals` text, e.g. `🎯 EUR 700 / EUR 800` for 700 of 800 EUR, carrying the same level as the bar (700 of 800 is `near`, 800 of 800 `over`) at EVERY level including `under`; with no budget (amount or currency null) there is no chip. It reads the same `GET .../budget` answer the panel loaded (no second request) and is drawn last in the summary line, after the expense totals (T-010); its tooltip is `budget.hint`, or `budget.hint_shared` for a shared budget. Unlike the card below, it is not limited to `near` and `over`; the trip card in the trips list shows the same text only when the level is `near` or `over` (and a currency exists), never for `under`. The trip card uses `budget_amount`, `budget_currency` and `budget_spent` from the trip list.

(Precedence in the panel, `TripBudget.svelte:198-306`: a load error wins (error text only); otherwise, while the form is open it is shown INSTEAD of the figures, bar and "No budget set" row; otherwise the budget panel if a budget exists, else the empty row. Cancel and a successful Save or Remove return to the panel or empty row.)

Form (opened by "Set a budget" or "Edit"):

- Amount: free text with decimal keyboard (placeholder "800"); a comma is accepted as the decimal separator (`,` replaced by `.`, so "1200,50" is sent as 1200.5). Only the first comma is replaced, so "1.200,50" becomes "1.200.50", is not a number and shows the invalid-amount error (`TripBudget.svelte:162`). Prefilled with the current amount when editing.
- Currency: choice of 41 codes (`CURRENCIES`); prefilled with the budget's currency, or with the user's default currency from settings (T-032) when there is no budget yet.
- "Share this budget with": the people picker (T-012) over `GET /api/trips/{id}/expenses/participants` (users and guests on the trip; the current user displayed as "NAME (you)"), prefilled with the current members. The participant list is fetched the first time the form opens; a failure leaves the list empty. The picker is shown only when there is more than one candidate (so on a trip with only you, or when the participants call failed, the form shows no sharing row at all), with the hint "A shared budget counts everyone's share together, so it makes no difference who paid." At rest the picker shows only the chosen tokens (the current user as "NAME (you)") and no candidate list, however many people are on the trip; the rest are found by focusing or typing (T-012). When the picker is hidden, Save still sends `members` = the prefilled current members.
- Save: the amount must be a finite number greater than zero, otherwise "Enter an amount greater than zero." is shown and nothing is sent. Valid: `PUT /api/trips/{id}/budget` with `{amount, currency, members}` where `members` is a list of `{type: 'user'|'guest', id}` built from the picker (the app always sends it from this form, including when empty), in selection-set order: the prefilled current members first, then people picked in this form in the order they were picked (so adding barbara (user 2) to a budget held by user 1 sends `[{user,1},{user,2}]`). The button reads "Saving…" while running; on success the form closes and the budget is reloaded; on error the server message is shown in the form.
- "Remove budget" is shown in the form only when a budget exists. It sends `DELETE /api/trips/{id}/budget` immediately (no confirmation), closes the form and reloads. A failure shows the message in the form.
- "Cancel" closes the form without saving. Save and Remove budget are both disabled while either request runs; Cancel is never disabled. Because Save and Remove share one flag, the Save button reads "Saving…" while a Remove is running. Remove does not clear an earlier form error before it starts (`TripBudget.svelte:180-191, 238-250`).
- Locale keys: the amount field label is `budget.amount` ("Budget amount", `TripBudget.svelte:203`); the form's save button is `budget.save` ("Save budget", `budget.saving` while sending, line 240); the word between spent and total is `budget.of` ("of", line 257). The hint under the panel is `budget.hint` ("Counts your share of each expense — an expense split four ways counts a quarter of it, whoever paid.") for a solo budget and `budget.hint_shared` when it has more than one member (`TripDetailPage.svelte:640`, `1084`).

## API calls

- `GET /api/trips/{tripId}/budget` (budgetApi.get)
- `PUT /api/trips/{tripId}/budget` body `{amount, currency, members?}` (budgetApi.set; if `members` is omitted the server leaves an existing member list unchanged, which the web form never does)
- `DELETE /api/trips/{tripId}/budget` (budgetApi.clear)
- `GET /api/trips/{tripId}/expenses/participants` (expensesApi.participants; candidates for sharing; owned by T-026)

## Android notes

Same as shared code.

## iOS notes

Same as shared code.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- ViewModel and UI state (C08): one ViewModel exposing a sealed UI state, not booleans (`SOFTWARE_PATTERNS.md`; `FlowState` in `core-data/.../AppFlowSupport.kt`) (no budget, under, near, over) ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt)
- Progress bar (C25): Material 3 `LinearProgressIndicator`, colour from the budget level ; copy no sample (no linear bar in the samples)
- JSON models (C02): `@Serializable` data classes in `core-model` (`TripBudget` with spent and members); `Json { ignoreUnknownKeys = true }` already set in `PlatformHttpClient.android.kt` ; copy [PeopleInSpace: `PeopleInSpaceApi.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/remote/PeopleInSpaceApi.kt)
- Repository (`SOFTWARE_PATTERNS.md`): `BudgetRepository`; the level (`budgetLevel`) is a pure function, not UI code

## Tests

- Level test: 79 percent gives `under`, 80 gives `near`, exactly 100 gives `over` (and note "Budget spent in full"), 101 gives `over` (note "{amount} over budget"); an amount of zero or none gives no level. The trip card shows the alarm for `near` and `over` only.
- Display test: a 500 EUR budget with 20 USD in `uncounted` shows "Not counted:" with a "USD 20" pill and does not change the bar.
- Amount test: "12,5" is sent as `12.5`; "0", "-3" and "abc" show "Enter an amount greater than zero." and send nothing.
- Members test: saving from the form sends `members` as `{type, id}` pairs including a guest; the picker is hidden when only one candidate exists; the picker failing to load still allows saving.
- Shared test: for a budget whose `owner_user_id` differs from the viewer and has other members, the panel shows "Shared with {names}" and "set by OWNER"; for the owner it does not show "set by". A member can save and remove it.
- Empty and error test: no budget shows "No budget set for this trip." and "Set a budget"; a failing `GET` shows only the error text; "Remove budget" appears only when a budget exists and sends `DELETE` without a confirm.
- Bar test: 40 percent gives intensity 0.5 and a fill mix of 68 percent; 90 percent gives 0.5; 130 percent or more gives 1 (mix 100); 150 percent gives a bar width of 100; the track reports min 0, max amount, now spent.
- Colour test: over turns the spent figure and note danger colour; near shows the warning colour; a load error is shown in the danger text colour.
- Loading test: before the first `GET .../budget` answers the panel shows the empty row with "Set a budget".
- Button state test: while Remove runs, Save and Remove are disabled, Save reads "Saving…" and Cancel stays enabled; an earlier form error stays visible until the request ends.
- Precedence test: opening the form hides the figures, bar and empty row; Cancel restores them.
- Level thresholds test (budget 800 EUR): spent 200 and 639 give level `under`; 640 (exactly 80 percent) and 799 give `near`; 800 and 801 give `over` (web tests: "is neutral well under the limit", "warns as the limit approaches", "is neutral just below the warning threshold", "goes red at the limit, not one euro past it").
- Intensity test (budget 800): the fill mix grows with spend (80 < 400 < 630), starts pale again entering the next band (648 is lower than 632), is at least 35 even at 0 spent, and is exactly 100 at 1040 and at 5000 (web tests: "deepens as the bar fills", "starts pale again on entering the next band", "never mixes so far into the track that the bar disappears", "tops out rather than deepening forever past the limit").
- Spent-in-full test: spent exactly equal to the amount shows "Budget spent in full", not "0 over" (web test: "says the budget is spent rather than "0 over" at exactly the limit").
- Over-budget bar test: spent 1600 of 800 draws the bar at 100 percent width and the note reads "EUR 800 over budget" (web test: "stops the bar at the limit while the number keeps going").
- Other-currency test: `uncounted` of `{SEK: 900, BRL: 240}` on a 420 of 800 EUR budget shows pills "BRL 240" and "SEK 900", in that order, without converting (web test: "lists spend in other currencies without converting it").
- No-budget test: a response with `amount: null` shows the "No budget set for this trip." row with "Set a budget" and no bar (web test: "offers to set one when the trip has no budget").
- Save test: "Set a budget", typing 800 and tapping Save sends `PUT /api/trips/trip-1/budget {amount: 800, currency: "EUR", members: [{type: "user", id: 1}]}` and then reads `GET .../budget` again (two reads in total); "1200,50" is sent as 1200.5; "0" sends nothing and shows the invalid-amount error (web tests: "saves a budget and re-reads the spend", "accepts a comma decimal, which is what a pt-BR keyboard gives", "refuses a budget of zero rather than sending it").
- Shared names test: a budget with members me and barbara shows "Shared with barbara"; with only me, no shared line; when the owner is barbara (not the viewer) the shared line also carries "· set by barbara" (web tests: "names who a shared budget is shared with", "says nothing about sharing when the budget is yours alone", "names the owner when the budget is someone else's").
- Share save test: with participants me and barbara, opening the form, typing 800, picking barbara from the suggestions (the only one offered, since you are already chosen) and saving sends `members: [{user,1},{user,2}]` (web test: "sends the chosen members when saving").
- Crowded trip test: with seven participants the form shows exactly one token and no suggestion list at rest; focusing and typing "pedro" offers only pedro (web test: "stays compact on a crowded trip, with everyone still reachable").
- No-sharing-row test: with only you as participant the form shows no sharing row; when the participants call fails the form still opens and Save sends the amount (web tests: "hides the sharing row on a trip with only you on it", "still lets you set an amount when the participant list fails").
- Reload test: when the expense list reports a change, the budget is read again (second `GET .../budget`) (web test: "re-reads on demand when the expense list reports a change").
- Header budget chip test: a budget answer of amount 800 EUR with spent 700 shows a header chip containing "EUR 700" and "EUR 800" at level `near` (web test: "shows the budget in the header summary, with its state"); with no budget (amount and currency null) the header contents line is drawn but has no budget chip (web test: "leaves the header alone when no budget is set").
Web tests mirrored: frontend/src/components/TripBudget.test.ts, frontend/src/pages/TripDetailPage.test.ts

## Depends on

- T-026
- T-012
- T-008
