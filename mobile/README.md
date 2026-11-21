# Partiu mobile (planning only)

This folder holds the plan for a native Android and iOS app, built with Kotlin Multiplatform (KMP). It will be a second front end for the same backend API, doing exactly what the Svelte web app in `frontend/` does. **No app code exists yet**: only the inventory, one ticket per piece of work, and a script that keeps the two in sync.

## How the parity list works

`parity/coverage.csv` has one row for everything the web app is made of, plus every backend route:

| kind | what a row is |
| --- | --- |
| `page` | a file in `frontend/src/pages/` |
| `component` | a file in `frontend/src/components/` |
| `lib` | a non-test file in `frontend/src/lib/` |
| `api` | a call in `frontend/src/api/client.ts`, as `METHOD /path` with `{name}` path parameters |
| `route` | a backend route, as `METHOD /full/path`, from every router mounted with `include_router` in `backend/main.py` |

Columns: `kind,source,ticket,notes`. Each row names the ticket (`T-012`) that must cover it. Several rows can share a ticket. Backend routes that the web app never uses get the ticket `none` and the note `not used by web app` (five at the time of writing; some are defined in the web client but never called by a screen). The handlers `main.py` declares itself (the web manifest, the service worker and the single-page-app fallback) are not counted.

## Check

From the repository root (Python 3.9 or newer, standard library only):

```
python3 mobile/parity/check.py
```

It exits with 1 and lists the problems when a page, component, lib file, API call or backend route is missing from the CSV (or the CSV lists one that no longer exists), a row points at a missing ticket file, a ticket file has no `## Tests` bullet, or a ticket file is referenced by no row. Run it after any change to the web app or the backend routes. `python3 mobile/parity/check.py --list` prints every `kind,source` pair it found, which helps when adding rows.

## Tickets

`tickets/T-NNN-slug.md`, one per ticket, with exactly these sections:

1. `# T-NNN Title`
2. `## Web source`: the web files the ticket replaces.
3. `## What it does`: behaviour, read from the Svelte code.
4. `## API calls`: endpoints used.
5. `## Android notes` and `## iOS notes`: where the platforms differ (map, calendar, file import, wallet, links, secure storage, push), or "Same as shared code."
6. `## Build with` (to be added; not enforced yet, see `ENFORCE_BUILD_WITH` in `parity/check.py`): which starter module, pattern and sample app to copy, by concern id from [`BUILD-WITH.md`](BUILD-WITH.md).
7. `## Tests`: at least one bullet; each ticket lists what must be shown to work.
8. `## Depends on`: other tickets that come first.

T-001 to T-008 are foundations (server address and API client, sign-in and two-factor, offline cache, languages, theme, navigation shell, UI kit, shared logic). T-035 (native push) needs a backend change, because the server only sends Web Push today.
