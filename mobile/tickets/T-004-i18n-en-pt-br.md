# T-004 Languages: English and Brazilian Portuguese

## Web source

- `frontend/src/lib/i18n.ts`
- `frontend/src/locales/en.json`, `frontend/src/locales/pt-BR.json` (flat dotted keys, 783 in each, identical key sets)
- `frontend/src/pages/SettingsPage.svelte` lines ~1638-1648 (language select), ~755-790 (`ApiError` code handling)
- `frontend/src/lib/utils.ts` lines 9-68 (date formatting)
- `frontend/src/components/TripCard.svelte` line ~67 (plural choice)

## What it does

- Two languages: English (`en`, the fallback) and Brazilian Portuguese (`pt-BR`), built on `svelte-i18n`. Both files hold the same 783 keys, as flat dotted strings such as `nav.*`, `trips.*`, `trip.*`, `flight.*`, `settings.*`, `stays.*`, `expenses.*`.
- Strings use `{name}`-style placeholders (the names differ per string: `{n}`, `{count}`, `{name}`, `{s}`). Plurals are NOT ICU: a counted string has a hand-written twin key with a `_plural` suffix (for example `trips.flight_count` = "{n} flight" and `trips.flight_count_plural`). Call sites choose the key themselves with `count === 1 ? key : key + '_plural'`, in English and pt-BR alike (so 0 uses the plural form).
- Initial language: the value stored locally under `locale` if it is `en` or `pt-BR`, else `en`, so the right language shows before the server answers.
- The language belongs to the user account. `applyUserLocale(l)` (called after `GET /api/auth/me`, sign-in and 2FA verify) stores and applies `l` if valid, else `en`; it makes no API call.
- Settings > Appearance has a language select built from `LOCALES` (`i18n.ts:26-29`): the labels are the fixed strings "English" and "Português (BR)" with values `en` and `pt-BR`, shown identically in every UI language (they are not translated). `setLocale` stores and applies the choice at once, then calls `PATCH /api/auth/me` `{locale}` and ignores a failure. It does not validate the value (the select only offers the two).
- Dates and times: `formatDate`-style helpers in `lib/utils.ts` pass the locally stored locale to `toLocaleDateString` (short month, day, year); times are formatted 24-hour with the `en-GB` locale regardless of language; the day card builds weekday and month names from the app locale; some places (month chart labels, expense amounts, sync time) pass `undefined`, i.e. the device's own locale. The web does not use one single `Intl` setting.
- Errors that arrive as `ApiError` with a code and params (the Settings guest screen handles `guest_name_taken`, `guest_in_use`, `guest_on_trips`) are shown through a translated key with the params as values; every other error shows the server's string as received (English).

## API calls

- `PATCH /api/auth/me` (authApi.updateMe)

## Android notes

Generate Android string resources from the JSON at build time, or load the JSON in shared code. Android 13 per-app language settings should map to the same two values. Android's built-in plural rules for pt-BR treat 0 and 1 as singular, but the web picks the plural key for everything except exactly 1; keep the web rule for parity.

## iOS notes

Generate a String Catalog or load the JSON in shared code. Respect the system per-app language setting, mapped to the same two values.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- i18n strings (C10): not in base: add `composeApp/src/commonMain/composeResources/values/` and `values-pt-rBR/` (`compose.components.resources` is already a dependency); generate resources from the two locale JSON files at build time; plural rule and runtime language switch have no sample ; copy [Confetti: `strings.xml`](https://github.com/joreilly/Confetti/blob/main/shared/src/commonMain/composeResources/values-fr/strings.xml); [Confetti: `SettingsUI.kt`](https://github.com/joreilly/Confetti/blob/main/shared/src/commonMain/kotlin/dev/johnoreilly/confetti/ui/settings/SettingsUI.kt)
- Small settings (C05): `multiplatformSettings` is declared in `core-data/build.gradle.kts` but unused; wrap it in a `core-data` repository; the chosen language ; copy [FantasyPremierLeague: `AppSettings.kt`](https://github.com/joreilly/FantasyPremierLeague/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/AppSettings.kt); [Confetti: `AppSettings.kt`](https://github.com/joreilly/Confetti/blob/main/shared/src/commonMain/kotlin/dev/johnoreilly/confetti/AppSettings.kt)
- Platform adapters (C22): `expect`/`actual` like `PlatformHttpClient.*.kt` and `PlatformStoreFactory.*.kt`, small inputs and outputs (`SOFTWARE_PATTERNS.md` Adapter); OS per-app language mapped to `en` / `pt-BR` ; copy no sample
- State machine (`SOFTWARE_PATTERNS.md`): one `LocaleState` exposed as a flow; `PATCH /api/auth/me` through the API class ; copy no sample

## Native additions (not in web)

- Reuse the two JSON files as the single source of truth (convert at build time) so a contributor adds a string in one place.
- Respect the OS per-app language setting, mapped to the same two values.
- Use one consistent locale for dates and numbers instead of the mix above (decide and document; parity with the web mix is not required).

## Tests

- Key parity test: every key in `en.json` exists in `pt-BR.json` and vice versa, and the placeholders of each key match between the two (true in the web files today).
- `applyUserLocale` with `pt-BR` applies it; with an unknown value, null or undefined applies `en`.
- Switching the language in Settings re-renders visible strings without a restart and sends `PATCH /api/auth/me` `{locale}` once; a failing PATCH is ignored and the language stays changed.
- Plural selection: a count of 1 uses the plain key, 0 and 2 use the `_plural` key, in both languages.
- A coded `ApiError` (for example `guest_in_use` with params) shows the translated string with the params; a plain error shows the server text unchanged.
- Language list: the select always shows "English" and "Português (BR)" whatever the current UI language; the stored values are `en` and `pt-BR`.

## Depends on

- T-001
- T-002
