# T-032 Settings: appearance, default currency, password, two-factor, version

## Web source

`frontend/src/pages/SettingsPage.svelte` is one page, split over four tickets so that every section has exactly one owner:

- T-032 (this one): Appearance block (theme, accent, language, default currency) `:1602-1669` with `saveCurrency` `:84-103`; Change password `:1671-1740` with script `:482-514`; Two-factor authentication `:1421-1600` with script `:516-614`; Version (admin) `:1320-1343` with script `:149-152`.
- T-033: loading and error state of the page `:801-808`, sync status panel `:810-824`, email account `:826-976`, inbound SMTP `:978-1059`, email forwarding `:1061-1126`, Immich `:1218-1266`, airports `:1268-1304`, "Manage users" link `:1306-1318`, integrations and blocked domains `:1345-1419`.
- T-034: trusted users `:1742-1777`, trash `:1782` (`TrashPanel.svelte`), activity `:1783` (`ActivityPanel.svelte`), guest address book `:1786-1900`.
- T-035: admin push status `:1128-1141`, notification preferences and enable/disable push `:1143-1216` (and `frontend/src/lib/notifications.ts`).

Order of sections on the page, top to bottom: Sync status, Email account, Inbound SMTP (admin), Email forwarding (SMTP flag on), Push status (admin), Notifications, Immich, Airport data, Administration (admin), Version (admin), Integrations (admin), Blocked sender domains (admin), Two-factor authentication, Appearance (with language and default currency), Change password, Trusted users, Trash, Activity, Guests (`SettingsPage.svelte:810-1900`). A native app may regroup into sub-screens but must keep every block.

Also used here: `frontend/src/lib/themeStore.ts`, `accentStore.ts` and `i18n.ts` (stores themselves belong to T-004 and T-005), `frontend/src/lib/currencies.ts`.

## What it does

Gates used on this page: `$currentUser.is_admin` (admin), `$currentUser.demo === true` (demo server), `$currentUser.totp_enabled`.

Appearance block (all users), headed `settings.appearance` ("Appearance", `SettingsPage.svelte:1604`):
- Theme: three buttons "System", "Light", "Dark"; the active one is highlighted; choosing sets the theme store (T-005).
- Accent: one round swatch per accent in `ACCENTS`; the chosen one is marked pressed; its name is printed under the swatches. Choosing calls `setAccent` (T-005).
- Language: a select with the supported locales; choosing calls `setLocale` (T-004).
- Default currency: a hint "Pre-filled when adding expenses to a trip" and a select of the 41 codes in `CURRENCIES` (`SettingsPage.svelte:77-85`, `lib/currencies.ts:11-17`), in this order: AED ARS AUD BRL CAD CHF CLP CNY COP CZK DKK EGP EUR GBP HKD HUF IDR ILS INR ISK JPY KRW MAD MXN MYR NOK NZD PEN PHP PLN QAR RON SAR SEK SGD THB TRY TWD UAH USD ZAR. Shown as the plain codes. The server (`backend/expenses/domain.py:61` `SUPPORTED_CURRENCIES`, checked in `backend/settings/service.py:92`) upper-cases the value and rejects anything else with a validation error. Changing it immediately sends `POST /api/settings` with `{default_currency: value}`. On success the inline green message is `settings.saved` ("Settings saved!") for 2.5 s; on failure the select reverts to the last saved value and the server message shows in red for 2.5 s; the timer restarts on each change (`SettingsPage.svelte:91-102`; `locales/en.json:351`). If the user changes it again before the earlier request finishes, the older answer is ignored. The initial value comes from `GET /api/settings` (`default_currency`, fallback "EUR"), which the page loads as a whole (T-033 owns that load and its loading and error screens).

Change password:
- On a demo server (`demo === true`) the whole block is replaced by the text "The password is fixed on the demo — it is printed on the sign-in page for everyone to use." (`demo.locked_password`).
- Otherwise: "current password" and "new password" fields, and, only when the user has 2FA on (`totp_enabled`), a 6-character code field. The submit button is disabled while a request runs. If either password is empty the submit silently does nothing. There is no length check on the web side. Field details (`SettingsPage.svelte:1677-1718`): current password has autocomplete off and placeholder `settings.current_pw_placeholder`; new password has autocomplete `new-password` and placeholder `settings.new_pw_placeholder` ("New password (min 8 chars)") although no length is checked; the 2FA code field (only when 2FA is on) is numeric, max 6, one-time-code, placeholder `settings.pw_totp_placeholder` ("000000").
- Request: `POST /api/auth/change-password` with `{current_password, new_password}` plus `totp_code` (the field's content) when 2FA is on. Success shows "Password changed successfully" and clears the three fields. Any failure shows the server's message.

Two-factor authentication:
- On a demo server the block is replaced by "Two-factor authentication is disabled on the demo — everyone shares this account, so one person's authenticator app would lock everybody else out." (`demo.locked_2fa`); no calls are made.
- State is derived from `totp_enabled` (enabled), otherwise idle or setup.
- Idle: hint text `settings.2fa_idle_hint` ("Add an extra layer of security to your account with an authenticator app.") and a button "Enable 2FA". It calls `GET /api/auth/2fa/setup`, which returns `{secret, uri}`. The web builds the QR code itself (SVG from `uri`, via the `qrcode` library) and enters setup state; a failure shows the server message.
- Setup: instruction `settings.2fa_setup_hint` ("Scan this QR code with your authenticator app (e.g. Google Authenticator, Authy), then enter the 6-digit code to confirm."), the QR image, "Manual entry key:" with the `secret` text, a code field labelled `settings.2fa_code_label` ("6-digit code from your app"; numeric, max 6 characters, placeholder "000000", one-time-code autofill, takes focus when the setup view opens) and buttons "Cancel" and "Enable 2FA"; while the enable request runs the Enable button reads `settings.2fa_enabling` ("Enabling…"). The QR uses error-correction level M, a 2-module quiet zone, black on white, drawn 260 x 260 on a white card even in the dark theme so it still scans (`SettingsPage.svelte:533-553, 1522-1580`). Cancel is disabled while Enable is running. Setup is not persisted: the secret, QR and typed code are local state, leaving the screen abandons it, and a new visit starts idle and calls `GET /api/auth/2fa/setup` again. Enable is disabled until exactly 6 characters are typed. It sends `POST /api/auth/2fa/enable` with `{code}`. Success sets `totp_enabled: true` in the current user, leaves setup and shows "2FA enabled successfully". Failure shows the server message and stays in setup. Cancel leaves setup and clears the code and message.
- Enabled: shows one line: the 2FA-enabled sentence `settings.2fa_enabled_msg` ("Two-factor authentication is enabled on your account.") with the word "enabled" as a bold green badge (`SettingsPage.svelte:1439-1448`; the web builds it as message-minus-"enabled" + badge + " on your account." and so repeats "on your account"; native shows a single clean sentence "Two-factor authentication is [enabled] on your account." and localises it as a whole), and a "Disable 2FA" button. The button reveals a form: "Enter your TOTP code or current password to disable 2FA:", an authenticator code field (max 6 characters), the divider `settings.2fa_or` ("— or —"), and a current password field, with buttons "Cancel" and "Disable 2FA"; while the disable request runs the Disable button reads `settings.2fa_disabling` ("Disabling…"). Disable is enabled only when at least one of the two fields is filled. It sends `POST /api/auth/2fa/disable` with `{code?, password?}`, including only the non-empty fields. Success sets `totp_enabled: false`, closes the form and shows "2FA disabled". Failure shows the server message. Cancel (`cancelDisable`, `SettingsPage.svelte:602-606, 1490-1496`) closes the disable form and clears both fields but does NOT clear the 2FA message line; Cancel is disabled while the disable request runs. The disable form's password field uses placeholder `settings.2fa_current_pw_placeholder` ("Current password").
- 2FA messages (success or error) show above the current state; opening the disable form clears them.

Version (admin only):
- Shown only when the user is an admin and `GET /api/version` succeeded (a failure is ignored and the block stays hidden). Text `settings.running_version` ("Running version:") with `current_version` in monospace. If `update_available`, a button "↑ Update available — LATEST" (`settings.update_available` = "Update available —", followed by `latest_version`) an anchor to exactly `https://github.com/thiagodsti/partiu/releases/latest`, opened in a new tab / the external browser (`target=_blank`, `rel=noopener noreferrer`; `SettingsPage.svelte:1329-1340`); else if `latest_version` is known, a check mark with "Up to date"; else nothing more.

## API calls

- `POST /api/settings` `{default_currency}` (settingsApi.update; the rest of `/api/settings` belongs to T-033)
- `POST /api/auth/change-password` `{current_password, new_password, totp_code?}` (authApi.changePassword)
- `GET /api/auth/2fa/setup` (authApi.setup2fa; returns `{secret, uri}`)
- `POST /api/auth/2fa/enable` `{code}` (authApi.enable2fa)
- `POST /api/auth/2fa/disable` `{code?, password?}` (authApi.disable2fa)
- `GET /api/version` (versionApi.get; admin only; returns `{current_version, latest_version, update_available}`)

## Android notes

Same as shared code.

## iOS notes

Same as shared code.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- ViewModel and UI state (C08): one ViewModel exposing a sealed UI state, not booleans (`SOFTWARE_PATTERNS.md`; `FlowState` in `core-data/.../AppFlowSupport.kt`) per block (appearance, password, 2FA) ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt)
- Small settings (C05): `multiplatformSettings` is declared in `core-data/build.gradle.kts` but unused: wrap it in a `core-data` repository (theme, accent, language and default currency are stored here) ; copy [Confetti: `AppSettings.kt`](https://github.com/joreilly/Confetti/blob/main/shared/src/commonMain/kotlin/dev/johnoreilly/confetti/AppSettings.kt)
- Theme and accent colour (C11): `Theme.kt` (`KmpStartupTheme`); add a stored light/dark/system choice and accent presets feeding the colour scheme (C05) ; copy [ClimateTraceKMP: `Theme.kt`](https://github.com/joreilly/ClimateTraceKMP/blob/main/composeApp/src/commonMain/kotlin/dev/johnoreilly/climatetrace/ui/theme/Theme.kt); user-chosen accent: no sample
- Language switch (C10): not in base: add `composeApp/src/commonMain/composeResources/values/` and `values-pt-rBR/` ; copy [Confetti: `strings.xml`](https://github.com/joreilly/Confetti/blob/main/shared/src/commonMain/composeResources/values-fr/strings.xml); plural rule: no sample; runtime language switch: no sample

## Tests

- Currency test: choosing "BRL" posts `{default_currency: "BRL"}` and shows "Settings saved!"; a failing request reverts the select to the previous value and shows the server message; two quick changes ignore the stale first answer.
- Password test: with 2FA off the request body has exactly `current_password` and `new_password`; with 2FA on it also has `totp_code`; empty fields send nothing; a server error is shown verbatim; success clears the fields.
- Demo test: with `demo: true` neither the password form nor the 2FA controls are shown, only the two locked messages, and no setup call is made.
- 2FA enable test: setup shows a QR built from `uri` and the `secret`; Enable stays disabled until 6 characters; a correct code posts `{code}` and flips `totp_enabled` to true; a wrong code shows the server message and stays in setup.
- 2FA disable test: the button is disabled with both fields empty; a code only posts `{code}`, a password only posts `{password}`, both posts both; success flips `totp_enabled` to false.
- Version test: an admin sees the running version and "Update available" when `update_available`; a non-admin never calls `GET /api/version` and sees no block.
- Appearance heading test: the Settings screen shows a block headed "Appearance" (web test: "renders appearance section").
Web tests mirrored: frontend/src/pages/SettingsPage.test.ts

## Native additions (not in web)

- Server address (T-001) shown and changeable in this screen.
- Show the otpauth `uri` as a button that opens the installed authenticator app (Android `ACTION_VIEW`, iOS `UIApplication.open`) besides the QR and secret text; use `FLAG_SECURE` on Android on the 2FA setup screen; make sure Password AutoFill works on the password fields on iOS.
- Currency list test: the select offers exactly the 41 codes in the order listed above; a lower-case value sent to the server is upper-cased, and an unsupported code is rejected.
- Section order test: the Settings screen shows its blocks in the order listed above (admin-only blocks absent for non-admins).
- 2FA enabled text test: the enabled state shows one sentence with a green "enabled" badge and "on your account" once.
- 2FA setup detail test: the QR is drawn at 260 x 260 on white in dark theme; the code field is numeric with placeholder 000000; Cancel is disabled while Enable runs; leaving and re-entering the screen starts at idle.
- Cancel test: Cancel in the 2FA disable form clears both fields, leaves the previous 2FA message line unchanged and is disabled while the disable request runs.
- Field hints test: new password uses the new-password autofill hint and placeholder "New password (min 8 chars)"; the change-password 2FA code field is numeric with placeholder 000000.
- Version link test: with `update_available` the link opens exactly `https://github.com/thiagodsti/partiu/releases/latest` outside the app.

## Depends on

- T-002
- T-004
- T-005
