# T-006 Navigation shell, inbox badge and announcement banner

## Web source

- `frontend/src/components/AnnouncementBanner.svelte`
- `frontend/src/components/SideRail.svelte`
- `frontend/src/components/TabBar.svelte`
- `frontend/src/components/ToastContainer.svelte`
- `frontend/src/components/TopNav.svelte`
- `frontend/src/lib/invitationStore.ts`
- `frontend/src/lib/nav.ts`
- `frontend/src/lib/toastStore.ts`
- `frontend/src/App.svelte` (routes 25-43, boot 60-117, shell 119-150)

## What it does

- Five top-level destinations, defined once in `lib/nav.ts` (`NAV_ITEMS`): Trips (`#/trips`), History (`#/history`), Stats (`#/stats`), Inbox (`#/notifications`, carries the badge), Settings (`#/settings`). The web shows them as a left rail (`SideRail`) from 900px wide and a floating bottom dock (`TabBar`) below that; both read the same list. The rail also has a "P" mark linking to the project's GitHub page `https://github.com/thiagodsti/partiu` (opens a new tab; the link carries `rel="noopener noreferrer"` so the third-party site gets no opener handle and no referrer, `SideRail.svelte:20-26`; the "P" is only a letter, so the accessibility label is required); its tooltip and accessibility label are `nav.project` ("Partiu on GitHub", `SideRail.svelte:27-28`).
- Active item: it matches when the current route starts with one of its prefixes; Trips has `['/', '/trips']` where `/` matches only exactly. So `/history/...` lights History, and `/stats/map` lights Stats. Prefixes (`lib/nav.ts:19-29`): Trips `['/', '/trips']` (`/` only matches exactly), History `['/history']`, Stats `['/stats']`, Inbox `['/notifications']`, Settings `['/settings']`; matching is a raw `startsWith`. Examples (`lib/nav.test.ts:23-49`): `/` and `/trips/abc/flights/xyz` light Trips; `/history` and `/settings` do not light Trips; `/history/abc` lights History but `/trips/abc` does not; `/login` lights no item. Each entry has a unique target and exactly one entry (Inbox, `#/notifications`) carries the badge (`lib/nav.ts:21-27`). The rail shows one entry per item, with the current one marked active; the dock shows the same entries in the same order. Consequently `/invitations` (which shows the Inbox screen) lights NO item, and `/admin/users` lights NO item. Native decision needed: parity (no item lit) or light Inbox on `/invitations` and Settings on `/admin/users`.
- Wide layout (`app.css:493-509, 620, 671, 788, 2487`): from 900 px wide the rail is fixed at the left, the app shell gets `padding-left: var(--rail-width)` and no bottom padding (the dock is hidden), top nav and main content get larger side padding, and toasts move to bottom left beside the rail instead of centred. This is app-wide; individual screens add their own wide rules (trip detail two columns from 1000 px, T-010). Tablets use the rail, phones the dock.
- Sign-in and setup (`/login`, `/setup`) show neither rail nor dock.
- Inbox badge = pending invitations + unread notifications, shown as the plain sum (no cap) only when above 0. `refreshInvitationCount()` does nothing when no user is signed in; otherwise it loads `GET /api/trips/invitations` and `GET /api/notifications/inbox/count` together. It runs on every route change, every 30 seconds while the app is open, after sign-in, and after actions on the Inbox screen. On an `UnauthorizedError` from either call it clears the user, zeroes both counts and goes to `/login` (T-002; `invitationStore.ts`, catch block); because the user is now cleared, the next poll tick does nothing (no further requests). The two calls are awaited together: if either fails, neither count is updated. Any other failure (offline, HTTP 502, 5xx) keeps the signed-in user, the last counts and the current route. The badge number is drawn as plain text of the sum (for example `3`) and the badge element does not exist at 0 (`SideRail.svelte`, `TabBar.svelte`).
- Badge clearing: on app start (after `me` succeeds) and whenever the page becomes visible with a user signed in, the web calls `navigator.clearAppBadge()` if present and `POST /api/notifications/badge/clear` (failures ignored).
- Routes (`App.svelte`): `/`, `/trips` (list), `/trips/new`, `/trips/:id`, `/trips/:id/edit`, `/trips/:tripId/flights/:flightId`, `.../edit`, `/trips/:tripId/add-transport`, `/stats`, `/stats/map` (the map reads an optional `?year=` from the hash), `/history`, `/history/:id` (same trip screen), `/history/:tripId/flights/:flightId` and `.../edit`, `/settings`, `/admin/users`, `/notifications` and `/invitations` (same Inbox screen), `/login`, `/setup`. The router has no catch-all route; the `routeNotFound` handler (go to `/trips`) is bound to the router's `routeEvent`, which an unknown path does not emit, so unknown-route behaviour is not defined by the web code.
- Top bar (`TopNav`, included by each screen with its own title, not by the shell): title, optional back arrow (accessibility label `trip.back`, "Back to Trips", `TopNav.svelte:44`), optional action buttons, and when signed in the username plus a sign-out button (calls logout, then goes to `/login`; see T-002). The username text is hidden at widths up to 560px (`max-width: 560px`, `TopNav.svelte:78-86`); only the sign-out button remains.
- Shell order: offline banner (T-003), then announcement banner, then the screen, then rail/dock, then toasts. While the first `me` check runs the shell shows a plain "Loading..." text.
- Toasts (`toastStore.show(message, type = 'info', duration = 3000)`): a message with a type (info by default), removed after 3 seconds; several can stack in order of arrival, newest last. The container is not drawn at all while there are no toasts (`ToastContainer.svelte`). Styles (`app.css:2496-2517`): all have a card with a left accent bar; info uses the muted colour, `success` a green bar, `error` a red bar and red text. The message is the exact text passed.
- Announcement banner: shows `announcement` from the user object, or on a demo server (`demo: true`) a fixed translated demo message `demo.banner` ("This is the Partiu demo — everyone signs in to the shared account…", see en.json for the full text; `AnnouncementBanner.svelte:15`) when there is no announcement (an announcement wins over the demo text). Dismiss (an X glyph `✕`, accessibility label "Dismiss", English only, `AnnouncementBanner.svelte:27`) hides it. The dismissal is stored in the browser's session storage (`sessionStorage`, so it lasts until the tab or app session ends, not forever; not `localStorage`) under the key `announcement_dismissed` (`AnnouncementBanner.svelte:5,7,18`); the stored value is the announcement text at the time (`''` when there was none). On start the banner is hidden only when the stored value equals the current announcement text exactly (no stored value counts as not dismissed), so a changed announcement shows again; this is read once when the banner is created. Native: keep it per app session, not persisted across launches. On a demo server the banner cannot be dismissed. A user with no announcement and `demo` false sees nothing.
- Render failure: a boundary replaces a crashed screen with "This page didn't load." and a Reload button (reloads the page). Both strings are English only.

## API calls

- `GET /api/trips/invitations` (sharesApi.listInvitations)
- `GET /api/notifications/inbox/count` (notificationsApi.inboxCount)
- `POST /api/notifications/badge/clear` (notificationsApi.clearBadge)

## Android notes

Use Navigation Compose (or the chosen UI toolkit's equivalent) with the same route table. Handle the system back button the same as the top-bar back arrow. App icon badge counts need a launcher-specific API or notification count; treat the badge as best-effort.

## iOS notes

Use a tab bar with the same five destinations. App icon badge uses `UNUserNotificationCenter.setBadgeCount`, which needs notification permission.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- Navigation shell (C07): `composeApp/.../kmpstartup/App.kt` has only an `AppDestination` enum with `rememberSaveable`, no back stack; not in base: add Navigation 3 or Voyager; same five destinations plus the route table; unknown route lands on Trips ; copy [FantasyPremierLeague: `App.kt`](https://github.com/joreilly/FantasyPremierLeague/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/ui/App.kt)
- ViewModel and UI state (C08): `SOFTWARE_PATTERNS.md` state machine (sealed interfaces, not booleans), `FlowState` in `core-data/.../AppFlowSupport.kt`, `composeApp/.../kmpstartup/FlowStateCard.kt`, androidx `ViewModel`; inbox badge and announcement banner as one UI state fed by the 30-second poll ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt); [FantasyPremierLeague: `PlayerListViewModel.kt`](https://github.com/joreilly/FantasyPremierLeague/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PlayerListViewModel.kt)
- Platform adapters (C22): `expect`/`actual` like `PlatformHttpClient.*.kt` and `PlatformStoreFactory.*.kt`, small inputs and outputs (`SOFTWARE_PATTERNS.md` Adapter); back handling ; copy no sample
- App-icon badge (C28): one `expect`/`actual` adapter taking the count (`setBadgeCount` on iOS) ; copy no sample
- Unit tests (C20): `commonTest` in `core-data` (e.g. `SyncMergeTest.kt`) with `kotlin-test` and `kotlinx-coroutines-test`; fake HTTP with Ktor `MockEngine` (add); badge sum and clearing ; copy no sample
- Use case (`SOFTWARE_PATTERNS.md`): a `RefreshBadges` use case does invitations plus unread count in one call ; copy no sample

## Native additions (not in web)

- Bottom bar (Android) and tab bar (iOS), plus a rail on tablets, replace rail/dock.
- Define what an unknown route does (suggested: land on Trips) since the web does not.
- Native back-button handling and a launcher/app-icon badge count are native concerns; the web only calls `clearAppBadge` when available.
- Web-only, not rebuilt natively: the service worker and its versioned caches (`sw.js:25-43`, cache-first and network-first routing, update prompt), the install manifest (`public/manifest.json`: icons, theme colour), the `index.html` meta tags, the pre-JS HTML loader and the service-worker registration in `main.ts`. Native replaces them with its own offline cache (T-003) and the app icon and launch screen.

## Tests

- Route table test: every web route listed above resolves to a native destination with the same parameters, including `/history/...` variants that return to History and `?year=` on `/stats/map`; `/notifications` and `/invitations` open the same screen.
- Active item: `/history/5` lights History, `/stats/map` lights Stats, `/trips/new` lights Trips.
- Badge test: with 2 invitations and 3 unread notifications the Inbox badge shows 5; with 0 it shows nothing. After an Inbox action that changes the counts the badge refreshes.
- Refresh test: a `401` from either badge call clears the user and goes to sign-in; a `500` keeps the previous counts.
- Foreground test: becoming visible while signed in calls `POST /api/notifications/badge/clear`; not signed in, it does not.
- Announcement test: a dismissed announcement stays hidden for the session but a different announcement text shows again; with `demo: true` and no announcement the demo message shows with no dismiss control; with `demo: true` and an announcement the announcement text shows, still not dismissible.
- Toast test: a toast disappears after 3 seconds and two toasts stack.
- Wide layout test: at 900 px wide the rail is shown, the dock is hidden, content is inset by the rail width and toasts appear at the bottom left; below 900 px the dock is shown and content has bottom padding.
- Active item edge test: `/invitations` and `/admin/users` light no tab (web parity), unless the native decision above lights Inbox or Settings.
- Narrow top bar test: at 560px wide or less the username is hidden and the sign-out button stays; above 560px both show.
- Nav list: five entries each with a unique target, and exactly one (Inbox, `#/notifications`) carries the badge (web test: "has a unique href per entry", web test: "marks exactly one entry as carrying the inbox count").
- Active-item rules: `/` lights Trips; `/trips/abc/flights/xyz` lights Trips; `/history` and `/settings` do not light Trips; `/history/abc` lights History and `/trips/abc` does not; `/stats/map` lights Stats; `/login` lights nothing (web test: "lights Trips on the bare root", web test: "lights Trips on a nested trip route", web test: "does not light Trips on another section", web test: "lights History on a trip opened from history", web test: "lights Stats on the world map, which lives under it", web test: "leaves every entry dark on a route the navigation does not own").
- Rail (wide layout): one entry per nav item; on `/trips/abc` the entry with target `#/trips` is the active one (web test: "renders one entry per nav item", web test: "marks the current section active"). Inbox count 0 shows no badge; count 3 shows a badge with the text `3` (web test: "hides the inbox count when there is nothing unread", web test: "shows the inbox count when there is something unread").
- Dock (narrow layout): shows the same entries, in the same order, as the rail (web test: "renders the same entries in the same order as the rail").
- Project mark: opens `https://github.com/thiagodsti/partiu` outside the app (system browser, not inside the app) and carries a non-empty accessibility label ("Partiu on GitHub") (web test: "links to the repository in a new tab, safely", web test: "is labelled, since \"P\" says nothing to a screen reader").
- Toast container: with no toasts nothing is drawn; a toast "Hello world" shows that exact text; two toasts "First" and "Second" both show; an `error` toast "Error!" shows that text in the error style (red bar and text) and a `success` toast "Done" in the success style (green bar) (web test: "renders nothing when there are no toasts", web test: "renders a toast message", web test: "renders multiple toasts", web test: "applies the correct type class", web test: "applies success class correctly").
- Announcement (session storage key `announcement_dismissed`): a user with no announcement and `demo` false sees no banner (web test: "renders nothing without an announcement"); announcement "Maintenance Sunday" shows that text with a dismiss control (web test: "shows the announcement with a dismiss button on an ordinary install"); with `announcement_dismissed` already holding "Maintenance Sunday" the banner is hidden (web test: "respects a dismissal of that same announcement"); with `demo: true` and no announcement the demo message shows (web test: "banners the shared-account notice with no announcement configured"), with no dismiss control (web test: "offers no dismiss button"); with `demo: true`, announcement "Shared demo" and a stored dismissal of "Shared demo" the banner still shows "Shared demo" (web test: "stays up even when this announcement was dismissed before"); with `demo: true` and announcement "Resets nightly" that text shows instead of the demo message (web test: "prefers the deployer's own announcement over the default text").
- Inbox count refresh: signed out, `refreshInvitationCount` makes neither request (web test: "does not call the API when nobody is signed in"); signed in with 2 invitations and `{unread: 3}` the counts become 2 and 3 (web test: "updates both counts for a signed-in user"); invitations answering 401 with the user signed in (previous invitation count 1): user cleared, invitation count 0, route `#/login`, and the next refresh makes no request (web test: "signs the user out and stops polling when the session has expired"); an HTTP 502 on the invitations call (previous count 4): user stays, count stays 4, route stays `#/trips` (web test: "keeps the session and the last counts on other errors").
- Web tests mirrored: frontend/src/lib/nav.test.ts, frontend/src/components/SideRail.test.ts, frontend/src/components/AnnouncementBanner.test.ts, frontend/src/components/ToastContainer.test.ts, frontend/src/lib/invitationStore.test.ts

## Depends on

- T-001
- T-002
- T-007
