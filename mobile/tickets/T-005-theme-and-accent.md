# T-005 Theme (light, dark, system) and accent colour

## Web source

- `frontend/src/lib/accentStore.ts`
- `frontend/src/lib/themeStore.ts`
- `frontend/src/app.css`
- `frontend/src/pages/SettingsPage.svelte` lines ~1600-1635 (Appearance)

## What it does

- Theme has three choices: system (default), light, dark. It is stored only on the device (`localStorage` key `theme`) and never sent to the server, on purpose: a phone at night and a laptop by day can differ. System means no `data-theme` attribute, so the CSS follows `prefers-color-scheme`; light and dark set `data-theme` on `<html>`. Any stored value other than `dark` or `light` reads as system.
- Accent has five presets, in this order: sky (default), ocean, dusk, orchid, graphite. `setAccent` applies it at once (`data-accent` on `<html>`), caches it locally and calls `PATCH /api/auth/me` `{accent}`, ignoring a failure. The server value is returned by `GET /api/auth/me`, sign-in and 2FA verify.
- `applyUserAccent(value)` (after me, sign-in and 2FA verify) applies the server value; an unknown, null or missing value becomes sky. It writes nothing to the server.
- The local accent copy (`localStorage` key `accent`) exists only to paint the right colour before the server answers. Invalid stored values read as sky. At app start the cached accent is applied before the first screen is drawn (`accentStore.ts:51-53`), so there is no flash of the default; a cache that cannot be read (storage disabled or throwing) reads as sky and does not stop the app (`accentStore.ts:41-47`). Every accent change, whether chosen in Settings or adopted from the server, is also written to this cache (`accentStore.ts:49`). The server value always wins over the cache: after sign-in or `me` a user whose server accent is `ocean` shows ocean even if the cache said orchid.
- Colours, fonts and spacing are CSS variables in `frontend/src/app.css`: base tokens for light (line ~122, 159) and dark (~195), and per-accent overrides `[data-accent=...]` (~251-290) with separate light/dark variants (~293 on).
- Settings > Appearance shows three buttons for the theme (system, light, dark; the active one highlighted) and five round swatches for the accent (`aria-pressed` on the active one, title and label from `settings.accent_<name>`), with the accent's label as a hint line beneath. The labels are `settings.accent_sky` ("Sky"), `settings.accent_ocean` ("Ocean"), `settings.accent_dusk` ("Dusk"), `settings.accent_orchid` ("Orchid") and `settings.accent_graphite` ("Graphite"); the keys are built from the accent list in `accentStore.ts:22-27`. The language select sits in the same section (T-004). See T-032.

- Reduced motion: under `prefers-reduced-motion: reduce` the web shrinks all animation and transition durations to 0.001 ms, runs animations once and turns off smooth scrolling (`app.css:470-476`). Native respects the system reduce-motion setting the same way: no slide, fade or skeleton animations; state changes appear instantly.

## API calls

- `PATCH /api/auth/me` body `{accent}` (authApi.updateMe)

## Android notes

Material 3 dynamic colour must not override the accent presets; map each preset to a colour scheme pair (light and dark). Follow `AppCompatDelegate` night mode for system.

## iOS notes

Define the presets in an asset catalog with light and dark variants; set `overrideUserInterfaceStyle` for the explicit choices.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- Theme and accent colour (C11): `composeApp/.../kmpstartup/Theme.kt` (`KmpStartupTheme`); add the accent presets and light/dark/system choice as a stored setting feeding the colour scheme ; copy [ClimateTraceKMP: `Theme.kt`](https://github.com/joreilly/ClimateTraceKMP/blob/main/composeApp/src/commonMain/kotlin/dev/johnoreilly/climatetrace/ui/theme/Theme.kt); [Confetti: `Theme.kt`](https://github.com/joreilly/Confetti/blob/main/androidApp/src/main/java/dev/johnoreilly/confetti/ui/Theme.kt)
- Small settings (C05): `multiplatformSettings` is declared in `core-data/build.gradle.kts` but unused; wrap it in a `core-data` repository; theme choice and the local accent copy ; copy [FantasyPremierLeague: `AppSettings.kt`](https://github.com/joreilly/FantasyPremierLeague/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/AppSettings.kt); [Confetti: `AppSettings.kt`](https://github.com/joreilly/Confetti/blob/main/shared/src/commonMain/kotlin/dev/johnoreilly/confetti/AppSettings.kt)
- HTTP client (C01): reuse the shared client in `backend-client/.../backend/client/Clients.kt` (`KtorAuthApi` style: one small API class per area); `PATCH /api/auth/me` with `{accent}` ; copy [PeopleInSpace: `Koin.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/di/Koin.kt)
- State machine (`SOFTWARE_PATTERNS.md`): a `ThemeSettings` repository exposes one sealed/enum state that the colour scheme reads ; copy no sample

## Native additions (not in web)

- Derive the native design tokens from `app.css` so both front ends stay visually aligned.
- Material 3 dynamic colour must not override the accent presets (see Android notes).

## Tests

- Each of the five accents has a distinct primary colour in light and dark; an unknown, null or missing accent renders sky.
- Choosing an accent applies it immediately and sends one `PATCH /api/auth/me` `{accent}`; a failing PATCH is ignored and the accent stays applied.
- Signing in (or launch with `me`) as a user whose server accent differs replaces the local value and sends no PATCH.
- Theme: system, light and dark can be chosen; the choice persists across restarts and no request is sent; an unknown stored value reads as system.
- Reduce-motion: with the system setting on, no transition or animation runs and state changes appear at once.
- Default accent test: with nothing cached, the accent is sky (web test: "defaults to sky when nothing is cached").
- Cold start test: with `ocean` cached, the first drawn screen already uses ocean, before any server answer (web test: "paints the cached value at import time, before anything renders").
- Bad cache test: a cached value `chartreuse` (not a preset) gives sky (web test: "ignores a cached value that is not a known preset").
- Unreadable cache test: when reading the local cache throws, the accent is sky and the app starts (web test: "survives storage being unavailable").
- Preset list test: the presets are exactly sky, ocean, dusk, orchid, graphite, in that order (web test: "lists every preset the stylesheet defines, sky first").
- Persist test: choosing `dusk` sends `PATCH /api/auth/me` `{accent: "dusk"}`, so the choice belongs to the account and not only to the device (web test: "persists the choice to the user account, not just the browser").
- Immediate test: choosing `orchid` shows orchid at once even while the PATCH never answers (web test: "applies immediately rather than waiting for the server").
- Save failure test: choosing `ocean` with a failing PATCH leaves ocean applied (web test: "keeps the chosen colour when the save fails").
- Server wins test: cache `orchid`, server accent `ocean` for the signed-in user: the screen shows ocean (web test: "adopts the signed-in user's accent over whatever the browser cached").
- No write-back test: adopting the server's accent (`dusk`) sends no PATCH (web test: "does not write back to the server").
- Missing accent test: a user row with no accent, with `dusk` cached, shows sky (web test: "falls back to the default for a user row with no accent").
Web tests mirrored: frontend/src/lib/accentStore.test.ts

## Depends on

- T-002
