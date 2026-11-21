# T-007 Shared UI building blocks

## Web source

- `frontend/src/components/Checkbox.svelte`
- `frontend/src/components/ConfirmModal.svelte`
- `frontend/src/components/EmptyState.svelte`
- `frontend/src/components/FormSection.svelte`
- `frontend/src/components/Icon.svelte`
- `frontend/src/components/LoadingScreen.svelte`
- `frontend/src/app.css`

## What it does

- Loading screen (`LoadingScreen`): an icon (default the text glyph `✈`, U+2708, shown with a floating/rotating animation; a caller may pass any other glyph, for example `🔄`) and a message (default "Loading...", exactly three dots, `LoadingScreen.svelte:6`). Each screen passes its own text. The icon and message are two separate pieces of text.
- Empty state (`EmptyState`): icon (default the text glyph `✈`, U+2708; a caller may pass another, for example `⚠️`, `EmptyState.svelte:10`), title, optional description, and optional child content such as buttons (for example Retry on a failed load). The description line is drawn only when a non-empty description is passed; otherwise no line and no gap is left (`EmptyState.svelte:16`).
- Confirm dialog (`ConfirmModal`): a message, a cancel button (default label "Cancel") and a confirm button (default "Confirm"), shown over a backdrop. Tapping the backdrop calls cancel; tapping inside the dialog does not. `danger` styles the confirm button as destructive instead of primary. Callers pass the labels; the defaults are English. It is used by the trip and flight detail screens; other places use the browser's `confirm()` (15 call sites).
- Form section (`FormSection`): a grouped block holding its fields (the children). The title line is drawn only when a non-empty title is passed; with no title there is no title row at all (`FormSection.svelte:12`).
- Checkbox (`Checkbox`): a button with `role="checkbox"`, `aria-checked` and an `aria-label` (the label prop; the box has no visible text). Checked state draws a filled box in the accent colour (`--accent`) with a tick in the on-accent colour (`--accent-on`, never fixed white: on the graphite preset in dark mode the accent is near-white and a white tick would vanish; `Checkbox.svelte:34-37`). Unchecked draws an empty outlined box (border `--border-strong`) with no tick and no fill (`Checkbox.svelte:45`). `aria-checked` is `false` when unchecked and `true` when checked (`Checkbox.svelte:28`). A tap calls `onToggle` and does not bubble to the parent row. Used by the packing list and the day planner.
- Icons (`Icon`): five inline icons used by the navigation: plane, clock, chart, inbox, sliders. Other screens use text or emoji glyphs.

- Reduced motion (`app.css:470-476`, applies to the loading animation, the confirm dialog and toasts, `ToastContainer.svelte`): under the system reduce-motion setting they appear and disappear without animation.

## API calls

- None of its own.

## Android notes

Same as shared code. Use the platform's accessibility semantics (TalkBack role and state for the checkbox).

## iOS notes

Same as shared code. Use VoiceOver traits (`.isButton`, selected state) for the checkbox.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- ViewModel and UI state (C08): `SOFTWARE_PATTERNS.md` state machine (sealed interfaces, not booleans), `FlowState` in `core-data/.../AppFlowSupport.kt`, `composeApp/.../kmpstartup/FlowStateCard.kt`, androidx `ViewModel`; stateless loading, empty and confirm components next to `FlowStateCard.kt` ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt); [FantasyPremierLeague: `PlayerListViewModel.kt`](https://github.com/joreilly/FantasyPremierLeague/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PlayerListViewModel.kt)
- Theme and accent colour (C11): `composeApp/.../kmpstartup/Theme.kt` (`KmpStartupTheme`); add the accent presets and light/dark/system choice as a stored setting feeding the colour scheme; tokens from the theme ; copy [ClimateTraceKMP: `Theme.kt`](https://github.com/joreilly/ClimateTraceKMP/blob/main/composeApp/src/commonMain/kotlin/dev/johnoreilly/climatetrace/ui/theme/Theme.kt); [Confetti: `Theme.kt`](https://github.com/joreilly/Confetti/blob/main/androidApp/src/main/java/dev/johnoreilly/confetti/ui/Theme.kt)
- i18n strings (C10): not in base: add `composeApp/src/commonMain/composeResources/values/` and `values-pt-rBR/` (`compose.components.resources` is already a dependency); default labels like "Cancel" as resources ; copy [Confetti: `strings.xml`](https://github.com/joreilly/Confetti/blob/main/shared/src/commonMain/composeResources/values-fr/strings.xml); [Confetti: `SettingsUI.kt`](https://github.com/joreilly/Confetti/blob/main/shared/src/commonMain/kotlin/dev/johnoreilly/confetti/ui/settings/SettingsUI.kt)
- UI tests (C21): none in base; add compose ui-test; accessibility roles and states ; copy [PeopleInSpace: `ISSPositionUiTests.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonTest/kotlin/com/surrus/peopleinspace/ui/ISSPositionUiTests.kt)
- Adapter (`SOFTWARE_PATTERNS.md`): one dialog component, no platform code; keep it free of ViewModels ; copy no sample

## Native additions (not in web)

- Native should use one dialog component for both `ConfirmModal` uses and the browser `confirm()` prompts.
- The confirm dialog also handles the system back gesture as cancel (the web only handles backdrop tap).

## Tests

- Each component renders in light and dark and with each accent.
- Checkbox: a tap calls `onToggle` once and does not trigger the parent row's tap; it exposes the checkbox role, checked state and label.
- Confirm dialog: confirm calls confirm, cancel calls cancel, a backdrop tap calls cancel, a tap inside the dialog calls neither; `danger` uses the destructive style; default labels are "Confirm" and "Cancel".
- Empty state shows the description and children only when given; loading screen shows the default message "Loading..." when none is given.
- Native addition: the system back gesture on the confirm dialog calls cancel.
- Checkbox states: unchecked exposes role checkbox, state false and the given label (for example "Mark item"), and shows an empty outlined box with no tick (web test: "exposes its state to assistive tech", web test: "draws an empty box when unchecked"); checked exposes state true (web test: "reports itself as checked when it is"); checked draws the tick in the on-accent colour on an accent-filled box, so it is readable on every accent preset in light and dark (web test: "paints the tick in the accent-on token so it reads on every preset"); one tap calls `onToggle` exactly once (web test: "calls onToggle when clicked"); the tap does not reach a parent row's tap handler, so ticking an item inside a collapsible card does not collapse the card (web test: "does not let the click reach an enclosing handler").
- Empty state: with only a title it shows the title and the default `✈` icon, and no description line (web test: "renders the title", web test: "renders the default icon when none provided", web test: "does not render description element when omitted"); with `icon: ⚠️` it shows that glyph (web test: "renders a custom icon"); with a description "No flights found" it shows that text (web test: "renders description when provided").
- Loading screen: no arguments shows `✈` and "Loading..." (web test: "renders the default message", web test: "renders the default icon"); with message "Fetching trips…" it shows that text (web test: "renders a custom message"); with icon `🔄` it shows that glyph (web test: "renders a custom icon").
- Form section: the fields passed in are shown (web test: "renders children"); with title "My Section" the title text is shown above them (web test: "renders title when provided"); with no title no title row is shown (web test: "does not render title element when omitted").
- Reduce-motion: with the system setting on, a toast, the confirm dialog and the loading icon show and hide with no animation.
- Web tests mirrored: frontend/src/components/Checkbox.test.ts, frontend/src/components/EmptyState.test.ts, frontend/src/components/LoadingScreen.test.ts, frontend/src/components/FormSection.test.ts

## Depends on

- T-005
