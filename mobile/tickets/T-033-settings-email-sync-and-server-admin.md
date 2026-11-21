# T-033 Settings: email sync, forwarding, Immich, airports and server admin

## Web source

Owned part of `frontend/src/pages/SettingsPage.svelte` (the other parts belong to T-032, T-034 and T-035; see the split listed in T-032):

- Page loading and error state `:801-808`, load function `:178-217` (parallel `GET /api/settings`, `GET /api/sync/status`, `GET /api/settings/airports/count`)
- Sync status panel and "Full Sync" button `:810-824`, script `:219-256`; status bar `frontend/src/components/SyncStatusBar.svelte`
- Email account (IMAP) form `:826-976`, script `:258-306` (`saveSettings`, `testImapConnection`), presets `:38-43`
- Inbound SMTP server (admin) `:978-1059`
- Email forwarding (per user) `:1061-1126`
- Immich `:1218-1266`, script `:419-462`
- Airport data `:1268-1304`, script `:310-328`
- "Manage users" link (admin) `:1306-1318` (the screen itself is T-036)
- Integrations status and blocked sender domains (admin) `:1345-1419`, script `:125-146` and `:616-650`

## What it does

Gates: admin = `$currentUser.is_admin`. The demo flag is NOT used anywhere in these sections: the web does not hide secrets or disable saving here.

The screen has a top bar titled "⚙ Settings" (`settings.title`; the glyph is part of the string, `SettingsPage.svelte:798`). Below it the page shows the loading screen, the error screen or the sections.

Page load: shows a loading screen with the gear icon and `settings.loading` ("Loading settings…") then the sections. If `GET /api/settings` fails the page shows only an error screen titled `settings.load_error` ("Failed to load settings") with the server message (no retry button). `GET /api/sync/status` and `GET /api/settings/airports/count` failures are ignored (treated as no status / zero airports). If the status is `running` at load, polling starts.

Sync status (all users):
- Status bar shows: "Syncing…" (with "— N / M emails" when a total is known); or "Sync error: MESSAGE" when status is `error`; or "Last sync: TIME" plus "(in Xh Ym at HH:MM)" or "(any moment)" computed from `last_synced_at + sync_interval_minutes`; or "Never synced".
- Button `settings.full_sync` ("↓ Full Sync from Email (keep existing)"): shows a `confirm` (`settings.full_sync_confirm`: "Run a full sync?" + blank line + "This will re-fetch all emails from the beginning of your sync window. It may take several minutes depending on how many emails you have. Existing flights won't be deleted."). On yes: `POST /api/sync/full-sync`, status is set to running locally and `GET /api/sync/status` is polled every 2 seconds until the status is no longer `running` (a failing poll stops polling). Failure shows "Error: MESSAGE" in the shared settings message line. The button is disabled while the request is in flight. Polling is also cancelled when the screen is left; it restarts on the next visit only if the status read at load is `running` (`SettingsPage.svelte:256`).

Email account (all users; one form):
- All fields start with the values from `GET /api/settings`; for example the address field shows the saved `gmail_address` ("test@gmail.com"; `SettingsPage.svelte:193, 837-839`).
- Fields: email address (`gmail_address`, placeholder `settings.email_placeholder` "you@gmail.com"), app password (`gmail_app_password`, label `settings.password` "Password / App Password", password field, placeholder `settings.password_set` "(already set — paste to change)" when `gmail_app_password_set` is true, else `settings.password_placeholder` "xxxx-xxxx-xxxx-xxxx"; hint `settings.password_hint` "For Gmail, generate an App Password at: Google Account → Security → 2-Step Verification → App passwords."; the server never returns the password), the section label `settings.imap_server` ("IMAP Server"), a provider select (Gmail `imap.gmail.com:993`, Outlook `outlook.office365.com:993`, Zoho `imap.zoho.com:993`, Yahoo `imap.mail.yahoo.com:993`, or "Custom…", chosen automatically when host and port match no preset) which fills the host and port fields, host (placeholder `settings.imap_host_placeholder` "imap.example.com") and port (ports 1 to 65535). Defaults: `imap.gmail.com`, 993.
- Admin only, in the same form: `settings.sync_interval` ("Sync Interval (minutes)"; 1-1440, default 10; hint `settings.sync_interval_hint` "How often the server polls email for new messages. Takes effect after restart.") and `settings.first_sync_days` ("Initial Sync Window (days)"; 1-3650, default 90; hint `settings.first_sync_days_hint` "How far back to look when syncing for the first time.").
- Button `settings.test_connection` ("⇄ Test Connection"): `POST /api/settings/test-imap` with `{imap_host, imap_port, gmail_address?, gmail_app_password?}` (address and password only when non-empty); the server's `message` is shown below the button, green on success and red on failure (the error text).
- Save (`POST /api/settings`): the body contains only the keys listed here. `gmail_address` only if non-empty after trim; `gmail_app_password` only if typed (so leaving it empty keeps the stored one); `imap_host` (trimmed) and `imap_port` always; for admins also `sync_interval_minutes` and `first_sync_days` when they are numbers greater than zero, `smtp_server_enabled`, `smtp_server_port`, `smtp_domain` (trimmed); for everyone `smtp_recipient_address` and `smtp_allowed_senders` (trimmed, possibly empty strings). Success shows "Settings saved!" and clears the password field; failure shows "Error: MESSAGE". The save button reads `settings.save` ("Save Settings"; the same label on all three forms) and "Saving…" while running. While running, each action button is disabled and swaps its label (`SettingsPage.svelte:219-232, 900-920, 1293-1302, 1411-1415`): Full Sync shows "Syncing…", Test connection shows "Testing…" (the old result line is cleared when a test starts), Reload airports shows "Reloading…", add blocked domain shows "Adding…". There is no username, folder or polling on/off field.
- All the forms on this page that call save (email account, inbound SMTP, forwarding) share the same handler, state and message line, so any of their save buttons sends the same body. This message line has no timer: it is not cleared at the start of a save and keeps showing until another action replaces it, and the same text is rendered in all three forms (only the default-currency message in T-032 disappears after 2.5 s). Success is green, error red, otherwise grey. It reserves one line (24 px) of height even when empty so the layout does not jump (`SettingsPage.svelte:279-285, 953-966`).

Inbound SMTP server (admin only):
- Title `settings.inbound_smtp` ("Inbound Email Server"), description `settings.smtp_desc` ("Run a simple SMTP server so users can forward flight confirmation emails directly to this app."), a checkbox "Enable SMTP server", a domain field (`smtp_domain`, placeholder `settings.smtp_domain_placeholder` "teda.work", hint `settings.smtp_domain_hint` "Users without a custom forwarding address will default to username@domain."), and the port field (`smtp_server_port`, ports 1 to 65535, placeholder 2525, hint `settings.smtp_port_hint` "Use 2525 (or any port above 1024) to avoid needing root. Map port 25 → 2525 in Docker or your firewall.") which is shown only while the checkbox is on. Save as above. Loaded values: `smtp_server_enabled` (default false), `smtp_server_port` (default 2525), `smtp_domain`.

Email forwarding (all users, shown only while the local SMTP-enabled flag is true; it starts from the saved `smtp_server_enabled`, and for an admin it follows the "Enable SMTP server" checkbox live, before saving, `SettingsPage.svelte:1062`; the SMTP port field behaves the same way):
- Intro text `settings.forwarding_desc` ("Forward flight confirmation emails to your personal address below. Each user has their own forwarding address."). "Your address" (`settings.your_address` "Your forwarding address"; `smtp_recipient_address`, email field, placeholder `settings.your_address_placeholder` "trips@your-domain.com", hint `settings.your_address_hint` "Emails sent to this address will be processed and assigned to your account."). When the saved value is empty and an SMTP domain is set, the field is prefilled with `USERNAME@DOMAIN`.
- "Allowed senders" (`smtp_allowed_senders`, free text, placeholder `settings.allowed_senders_placeholder` "you@gmail.com, partner@gmail.com", hint `settings.allowed_senders_hint` "Comma-separated list of email addresses allowed to forward to you. Leave blank to accept from anyone."). Save as above.

Immich (all users):
- Text with a link to immich.app, fields "Immich URL" (url input) and "API Key" (password input; placeholder says a key is set when `immich_api_key_set` is true; the key is never returned).
- Exact hard-coded strings (not in `locales/en.json`, so T-004 does not carry them; `SettingsPage.svelte:1219-1265`): section title "Immich"; intro "Connect your self-hosted Immich instance to create photo albums from completed trips." with "Immich" a link to https://immich.app (new tab); labels "Immich URL" and "API Key"; URL placeholder "https://immich.example.com"; key placeholder "••••••••  (set — enter new key to change)" when `immich_api_key_set`, else "Paste your Immich API key"; no autofill on either field; buttons "Save Immich Settings" ("Saving…" while saving) and "Test" ("…" while testing); success message "Immich settings saved".
- Save and Test share one message line, cleared at the start of each. After a successful Save or the silent save inside Test, the key field is emptied. Web quirk: `immich_api_key_set` is recomputed after the field is emptied, so a key entered for the first time does not flip the placeholder until the next load (`SettingsPage.svelte:420-462`); native may set it to true right away (trip pages read `immich_api_key_set`, T-010).
- "Save Immich Settings": `POST /api/settings` with `{immich_url}` (trimmed) plus `immich_api_key` only if typed; success shows "Immich settings saved" and clears the key field; failure shows the server message.
- "Test": if the URL or key field has content it first saves them the same way (a save failure is ignored), then calls `POST /api/settings/test-immich` (no body); the server `message` is shown green on success, red on failure. The trip pages treat Immich as configured when both `immich_url` and `immich_api_key_set` are present (T-010).

Airport data (visible to all users):
- If the count is above 0 the text shows the number of loaded airports, formatted with the device locale's thousands grouping (`toLocaleString()`, e.g. `78,462 airports loaded.`; the same grouping applies to the unranked difference `count - ranked` in the warning and to the number in the "N airports loaded" line shown after Reload; `SettingsPage.svelte:318-320, 1275-1290`); e.g. a count of 5000 reads "5,000 airports loaded."; else "No airports loaded." plus the hard-coded sentence "Download airports.csv from ourairports.com and place it in the data/ directory." where "ourairports.com" links to https://ourairports.com/data/airports.csv (new tab; `SettingsPage.svelte:1275-1283`). A missing `ranked` counts as 0 on the web (so the warning would then cover every airport; the real server always sends `ranked`, `backend/settings/dto.py:60`). If the count is above 0 and `ranked` is lower than `count`, a warning (`settings.airports_unranked`, with `{n}` = count minus ranked) shows how many airports lack their size ranking: "N airports are missing their size ranking, so airport names in emails may resolve to the wrong airport (a flight from “London” can become London, Ontario). Put an up-to-date airports.csv in data/ and reload."
- A `settings.reload_airports` ("↺ Reload Airports") button appears whenever the count is above 0 (not admin-gated on the web). It sends `POST /api/settings/airports/reload`, updates count and ranked from the answer and shows "N airports loaded" in the shared message line; failure shows "Error: MESSAGE" there.

Admin only:
- "Manage users" button linking to the users screen (T-036).
- Integrations: section title `settings.integrations` ("Optional integrations") and intro `settings.integrations_desc` ("These are all optional — Partiu works without them. Each one adds a feature, and this shows what is missing without it. Set them in the server's .env file and restart."). List: `GET /api/settings/admin/integrations` returns rows `{key, configured, state, env_var}`. Each row shows a dot: amber when `state` is `public_instance` (checked first, so Photon on the public instance is amber even though its `configured` is true), else green when `configured` is true, else grey (a neutral grey, never red: an unset optional integration is a choice, not a fault; `SettingsPage.svelte:144-147`). Each row shows a name for the key, a state label (`integrations.state_<state>`, e.g. `integrations.state_public_instance` "public instance"), an effect sentence for that key and state, and the environment variable name only when the row has an `env_var` AND `configured` is false (so a configured key, and Photon on the public instance, show no variable name; an unset CARTO key shows `CARTO_API_KEY`; `SettingsPage.svelte:1365-1367`). The keys and texts are looked up as `integrations.<key>` and `integrations.<key>_<state>`: `integrations.carto` "CARTO basemap" (`carto_set` "Trip maps use the CARTO Voyager basemap, with Latin-script labels worldwide."; `carto_unset` "Trip maps fall back to plain OpenStreetMap tiles, whose labels are in the local script."); `integrations.aviationstack` "AviationStack" (`aviationstack_set` "Aircraft types and live flight status are looked up automatically."; `aviationstack_unset` "No aircraft types and no live flight status. Everything else about a flight still works."); `integrations.photon` "Photon geocoder" (`photon_public_instance` "Using komoot's public instance. Station and accommodation search work, but every place you type is sent to a shared, rate-limited service. Self-host Photon to avoid that."; `photon_self_hosted` "Using your own Photon instance for station and accommodation search."; `photon_disabled` "No station or accommodation search. Places save as plain text — no map pin, no timezone conversion, and they will not count toward visited countries."); `integrations.ollama` "Ollama LLM fallback" (`ollama_set` "Emails from unrecognised airlines are passed to the LLM as a last resort."; `ollama_unset` "Emails from unrecognised airlines are not parsed. All built-in airline rules still apply."); `integrations.push` "Web push notifications" (`push_set` "Push notifications are ready to send."; `push_unset` "No push notifications. Generate a key pair in the Push notifications section above."). The server's possible states are `set`, `unset`, `public_instance`, `self_hosted`, `disabled` (`backend/settings/integrations.py:43`). While loading it shows "Loading…"; a failed call leaves the list empty (the loading flag is cleared by `finally`).
- Blocked sender domains: description `settings.blocked_domains_desc` ("Emails from these domains are silently ignored during sync. Useful for accommodation, car rental, or other non-flight senders."). `GET /api/settings/admin/non-flight-domains` rows `{domain, note, created_at}`. Shows "Loading…", "No blocked domains." when empty, or each domain with a "Remove" button which calls `DELETE /api/settings/admin/non-flight-domains/{domain}` (URL-encoded) at once with no confirmation and removes the row locally. Add: a text field (label `settings.blocked_domains_add` "Block domain", placeholder `settings.blocked_domains_add_placeholder` "e.g. bookatable.com"; Enter also submits; on the web Enter ignores the in-flight state, only the button is disabled, so a fast double Enter can post twice; native should also ignore Enter while an add is running (accepted deviation) and still ignore a blank field; `SettingsPage.svelte:633-645, 1405-1412`) and an add button, disabled while empty or in flight; the domain is trimmed and lower-cased and sent as `POST /api/settings/admin/non-flight-domains` `{domain, note: ""}`, then the list is reloaded. Errors from add and delete are not shown.

## API calls

- `GET /api/settings` (settingsApi.get)
- `POST /api/settings` (settingsApi.update; body keys as described above)
- `POST /api/settings/test-imap` (settingsApi.testImap)
- `POST /api/settings/test-immich` (settingsApi.testImmich)
- `GET /api/sync/status` (syncApi.status)
- `POST /api/sync/full-sync` (syncApi.fullSync)
- `GET /api/settings/airports/count` (settingsApi.airportCount; `{count, ranked?}`)
- `POST /api/settings/airports/reload` (settingsApi.reloadAirports)
- `GET /api/settings/admin/integrations` (integrationsApi.list; admin)
- `GET /api/settings/admin/non-flight-domains` (nonFlightDomainsApi.list; admin)
- `POST /api/settings/admin/non-flight-domains` (nonFlightDomainsApi.add; admin)
- `DELETE /api/settings/admin/non-flight-domains/{domain}` (nonFlightDomainsApi.delete; admin)

## Android notes

Same as shared code.

## iOS notes

Same as shared code.

## Build with

Base = the KMPstarter base in `mobile/`; see `mobile/BUILD-WITH.md`.

- ViewModel and UI state (C08): one ViewModel exposing a sealed UI state, not booleans (`SOFTWARE_PATTERNS.md`; `FlowState` in `core-data/.../AppFlowSupport.kt`) per section (sync status, email form, admin) ; copy [PeopleInSpace: `PersonListViewModel.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/viewmodel/PersonListViewModel.kt)
- HTTP client (C01): `KtorAuthApi` in `backend-client/.../backend/client/Clients.kt` (settings, test-imap, full sync and admin calls through one `SettingsRepository`); the session cookie needs the `HttpCookies` plugin (not in base) ; copy [PeopleInSpace: `Koin.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/di/Koin.kt) (`createHttpClient`, no cookies)
- Error mapping (C03): not in base: add one HTTP-status mapper in `backend-client` (`ConnectionFailureReason` in `core-model` is the enum style) ; copy [PeopleInSpace: `PeopleInSpaceRepository.kt`](https://github.com/joreilly/PeopleInSpace/blob/main/common/src/commonMain/kotlin/dev/johnoreilly/common/repository/PeopleInSpaceRepository.kt) (`catch`); status mapping: no sample

## Tests

- Load test: a failing `GET /api/settings` shows only the error; failing status and airport calls do not block the page.
- Save body test: a non-admin saving with an empty password field sends `imap_host`, `imap_port`, `smtp_recipient_address`, `smtp_allowed_senders` and no `gmail_app_password`, no `sync_interval_minutes`, no `smtp_server_*`; an admin also sends `sync_interval_minutes`, `first_sync_days`, `smtp_server_enabled`, `smtp_server_port`, `smtp_domain`. An empty address field sends no `gmail_address`.
- Preset test: picking Outlook sets host `outlook.office365.com` port 993; typing a different host switches the select to Custom.
- IMAP test-connection test: the request carries host and port, and the address and password only when filled; the server message is shown green or red.
- Visibility test: a non-admin does not see the interval and first-sync fields, inbound SMTP, integrations, blocked domains, "Manage users"; the forwarding block shows only while the SMTP-enabled flag is on: ticking the admin "Enable SMTP server" checkbox shows it at once, unticking hides it; the airports and sync sections show for everyone.
- Full sync test: declining the confirm sends nothing; accepting posts `full-sync` and polls `/api/sync/status` every 2 s until the status is not `running`.
- Immich test: key left empty sends only `immich_url`; "Test" first saves then calls `test-immich`; `immich_api_key_set` only changes the placeholder.
- Airports test: with count 0 the reload button is hidden; with `ranked < count` the warning shows the difference; reload updates the numbers.
- Domains test: adding " Example.COM " sends `{domain: "example.com", note: ""}` and reloads; removing deletes without a confirm.
- Title test: the Settings top bar reads "⚙ Settings".
- Busy label test: during Full Sync, Test connection, Reload airports and add-domain the button is disabled and reads "Syncing…", "Testing…", "Reloading…", "Adding…"; starting a test clears the old result line.
- Poll cancel test: leaving the screen while a sync poll runs stops the polling.
- Message line test: a "Settings saved!" message stays until another action replaces it (no timer) and appears in all three forms.
- Immich strings test: the Immich section shows the exact intro, labels and placeholders listed above; the airports zero state shows the download sentence with its link.
- Immich key test: after Save the key field is empty; Save and Test share one message line.
- Integrations test: for each of the five keys and each state the server can send, the row shows its name, the state label, the matching effect sentence and (when not configured) the environment variable; a `public_instance` photon row has an amber dot and the self-host warning.
- Airport number test: 78462 is displayed grouped (`78,462` in en), in the loaded line, the Reload message and the unranked warning.
- Blocked-domain Enter test: Enter on a blank field sends nothing; a second Enter while an add is running is ignored.
- Settings loading test: while `GET /api/settings` has not answered the loading screen "Loading settings…" is shown (web test: "shows loading screen initially").
- Settings failure test: `GET /api/settings` fails with "Forbidden": that text is shown on the error screen "Failed to load settings" (web test: "shows error state when load fails").
- Email account prefill test: settings with `gmail_address` "test@gmail.com" show that address in the email address field (web test: "renders email account section with current address").
- Airport count test: `GET /api/settings/airports/count` returns `{count: 5000}`: the airport section shows the "airports loaded" sentence with 5,000 (web test: "renders airport count").
- Save request test: submitting the email account form without any change sends `POST /api/settings` once (web test: "calls settingsApi.update when form is submitted").
- Integrations list test: as an admin, with rows carto (`unset`), photon (`public_instance`) and push (`set`), the section "Optional integrations" shows the CARTO name and the label "not configured" (web test: "lists each integration with its state for an admin").
- Integration env var test: the unset CARTO row shows `CARTO_API_KEY`; the configured Photon row (`env_var` "PHOTON_URL") does not show its variable (web test: "names the env var only for something that is not configured").
- Photon tone test: the Photon row in state `public_instance` shows the label "public instance" and an amber dot, not green (web test: "distinguishes Photon on the public instance from a configured key").
- Neutral dot test: three rows give three dots; only the configured push row is green, the unset CARTO row is neither green nor amber (web test: "marks an unconfigured integration neutrally, not as an error").
Web tests mirrored: frontend/src/pages/SettingsPage.test.ts

## Depends on

- T-002
- T-032
