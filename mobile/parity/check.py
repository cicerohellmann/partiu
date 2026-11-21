#!/usr/bin/env python3
"""Parity check for the native front end.

Run from the repository root:

    python3 mobile/parity/check.py          # verify, exit 1 on any problem
    python3 mobile/parity/check.py --list   # print every scanned "kind,source"
    python3 mobile/parity/check.py --report # extra coverage classes, report only

It also checks that every string in frontend/src/locales/en.json is named
in a ticket (by key or by its text) or listed in unused-strings.txt.

It rescans the web app and the backend, then compares the result with
mobile/parity/coverage.csv and the ticket files in mobile/tickets/.
Standard library only, Python 3.9 or newer.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "frontend" / "src"
CLIENT = SRC / "api" / "client.ts"
BACKEND = ROOT / "backend"
COVERAGE = ROOT / "mobile" / "parity" / "coverage.csv"
TICKETS = ROOT / "mobile" / "tickets"
LOCALE_EN = SRC / "locales" / "en.json"
UNUSED_STRINGS = ROOT / "mobile" / "parity" / "unused-strings.txt"

KINDS = ["page", "component", "lib", "api", "route"]
COLUMNS = ["kind", "source", "ticket", "notes"]
# Set to True once every ticket has a "## Build with" section (see BUILD-WITH.md).
ENFORCE_BUILD_WITH = True
REQUIRED_HEADINGS = [
    "## Web source",
    "## What it does",
    "## API calls",
    "## Android notes",
    "## iOS notes",
    "## Tests",
    "## Depends on",
]
if ENFORCE_BUILD_WITH:
    REQUIRED_HEADINGS.insert(REQUIRED_HEADINGS.index("## iOS notes") + 1, "## Build with")
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


# --------------------------------------------------------------------------
# Path normalisation
# --------------------------------------------------------------------------

def _last_identifier(expr: str) -> str:
    names = re.findall(r"[A-Za-z_]\w*", expr)
    return names[-1] if names else "param"


def normalise_client_path(raw: str) -> str:
    """Turn the text that follows an opening quote into `/api/x/{name}/y`.

    Path parameters (`${id}` in a template string, `{id}` in a Svelte
    attribute) become `{name}`. The path ends at a query string, a closing
    quote, or a `${...}` that does not directly follow a slash (that is how
    the client appends optional query strings).
    """
    out = ""
    i = 0
    while i < len(raw):
        two = raw[i:i + 2]
        ch = raw[i]
        if two == "${" or ch == "{":
            start = i + 2 if two == "${" else i + 1
            depth, j = 1, start
            while j < len(raw) and depth:
                if raw[j] == "{":
                    depth += 1
                elif raw[j] == "}":
                    depth -= 1
                j += 1
            expr = raw[start:j - 1]
            if not out.endswith("/"):
                break
            out += "{" + _last_identifier(expr) + "}"
            i = j
            continue
        if ch in "?#\"'`\\ \t\r\n<>,)":
            break
        out += ch
        i += 1
    return out


def shape(path: str) -> str:
    """Parameter-name-free form, used to match client paths to backend paths."""
    return re.sub(r"\{[^}]*\}", "{}", path)


# --------------------------------------------------------------------------
# Scanners
# --------------------------------------------------------------------------

def scan_files() -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {"page": [], "component": [], "lib": []}
    for p in sorted((SRC / "pages").glob("*.svelte")):
        result["page"].append("frontend/src/pages/" + p.name)
    for p in sorted((SRC / "components").glob("*.svelte")):
        result["component"].append("frontend/src/components/" + p.name)
    for p in sorted((SRC / "lib").glob("*.ts")):
        if p.name.endswith(".test.ts") or p.name.endswith(".d.ts"):
            continue
        result["lib"].append("frontend/src/lib/" + p.name)
    return result


_CALL_PATTERNS = [
    # get<T>('/api/...'), post<{...}>(`/api/...`) and the other verb helpers.
    (re.compile(r"\b(get|post|put|patch|del)\s*<[^()]*?>\s*\(\s*['\"`](/api[^\n]{0,200})"), "helper"),
    # _request<T>('PATCH', `/api/...`)
    (re.compile(r"\b_request\s*<[^()]*?>\s*\(\s*'(GET|POST|PUT|PATCH|DELETE)'\s*,\s*['\"`](/api[^\n]{0,200})"), "request"),
    # fetch('/api/...', { method: 'POST' ... }) (multipart uploads)
    (re.compile(r"\bfetch\s*\(\s*['\"`](/api[^\n]{0,200})"), "fetch"),
    # imageUrl: (id) => `/api/...`  (URL builders the web app puts in <img src>)
    (re.compile(r"=>\s*['\"`](/api[^\n]{0,200})"), "url"),
]


def client_calls_detailed() -> List[Tuple[str, str]]:
    """Return [(`METHOD /path`, client function label)] in file order."""
    text = CLIENT.read_text(encoding="utf-8")
    found: List[Tuple[int, str, str]] = []
    for pattern, how in _CALL_PATTERNS:
        for m in pattern.finditer(text):
            if how == "helper":
                verb = {"del": "DELETE"}.get(m.group(1), m.group(1).upper())
                raw = m.group(2)
            elif how == "request":
                verb, raw = m.group(1), m.group(2)
            elif how == "fetch":
                raw = m.group(1)
                mm = re.search(r"method\s*:\s*'(\w+)'", text[m.start():m.start() + 400])
                verb = mm.group(1).upper() if mm else "GET"
            else:
                verb, raw = "GET", m.group(1)
            path = normalise_client_path(raw)
            label = _label_for(text, m.start())
            found.append((m.start(), f"{verb} {path}", label))
    found.sort()
    seen: Set[str] = set()
    result: List[Tuple[str, str]] = []
    for _, source, label in found:
        if source in seen:
            continue
        seen.add(source)
        result.append((source, label))
    return result


def _label_for(text: str, pos: int) -> str:
    """Best-effort `xxxApi.name` label for the call at `pos`."""
    head = text[:pos]
    names = re.findall(r"^\s{2}(\w+)\s*:", head, flags=re.M)
    groups = re.findall(r"^export const (\w+Api)\b", head, flags=re.M)
    if names and groups:
        return f"{groups[-1]}.{names[-1]}"
    return groups[-1] if groups else ""


def client_calls() -> List[str]:
    return [s for s, _ in client_calls_detailed()]


def direct_api_literals() -> Set[str]:
    """Shapes of `/api/...` paths used outside client.ts (links, image tags)."""
    shapes: Set[str] = set()
    files = [SRC / "App.svelte", SRC / "main.ts"]
    for sub in ("pages", "components", "lib"):
        files += sorted((SRC / sub).glob("*.svelte")) + sorted((SRC / sub).glob("*.ts"))
    for p in files:
        if not p.exists() or p.name.endswith(".test.ts"):
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith(("*", "//", "/*", "<!--")):
                continue
            for m in re.finditer(r"['\"`](/api/[^\n]*)", line):
                path = normalise_client_path(m.group(1))
                if path:
                    shapes.add(shape(path))
    return shapes


def _frontend_text() -> str:
    """All non-test web source outside client.ts, joined (for usage lookups)."""
    files = [SRC / "App.svelte", SRC / "main.ts"]
    for sub in ("pages", "components", "lib"):
        files += sorted((SRC / sub).glob("*.svelte")) + sorted((SRC / sub).glob("*.ts"))
    parts = []
    for p in files:
        if p.exists() and not p.name.endswith(".test.ts"):
            parts.append(p.read_text(encoding="utf-8"))
    return "\n".join(parts)


def called_by_a_screen(source: str, label: str, text: str) -> bool:
    """True if some page, component or lib file uses this client function.

    client.ts defines a few helpers that nothing calls (for example
    `tripsApi.addFlight`). Those routes do not need native screens.
    Calls with no `xxxApi.name` label are assumed to be used.
    """
    if not label:
        return True
    group, _, name = label.partition(".")
    pattern = r"\b" + re.escape(group) + r"\s*\.\s*" + re.escape(name) + r"\b"
    return re.search(pattern, text) is not None


def used_shapes() -> Set[str]:
    """Shapes of every endpoint the web app really reaches."""
    text = _frontend_text()
    shapes = {shape(s) for s, label in client_calls_detailed() if called_by_a_screen(s, label, text)}
    shapes |= {"GET " + d for d in direct_api_literals()}
    return shapes


def backend_routes() -> List[str]:
    """Every `METHOD /full/path` that backend/main.py mounts via include_router."""
    main = (BACKEND / "main.py").read_text(encoding="utf-8")
    alias_to_file: Dict[str, Path] = {}
    for m in re.finditer(r"^from \.([\w.]+) import (\w+)(?: as (\w+))?\s*$", main, flags=re.M):
        pkg, name, alias = m.group(1), m.group(2), m.group(3) or m.group(2)
        candidate = BACKEND / Path(*pkg.split(".")) / (name + ".py")
        if candidate.exists():
            alias_to_file[alias] = candidate
    mounted: Dict[Path, Set[str]] = {}
    for m in re.finditer(r"\.include_router\(\s*(\w+)\.(\w+)\s*\)", main):
        alias, var = m.group(1), m.group(2)
        if alias in alias_to_file:
            mounted.setdefault(alias_to_file[alias], set()).add(var)
    routes: List[str] = []
    for path in sorted(mounted):
        text = path.read_text(encoding="utf-8")
        prefixes: Dict[str, str] = {}
        for m in re.finditer(r"^(\w+)\s*=\s*APIRouter\(([^)]*)\)", text, flags=re.M):
            pm = re.search(r"prefix\s*=\s*['\"]([^'\"]*)['\"]", m.group(2))
            prefixes[m.group(1)] = pm.group(1) if pm else ""
        for m in re.finditer(r"^@(\w+)\.(get|post|put|patch|delete)\(\s*['\"]([^'\"]*)['\"]", text, flags=re.M):
            var, verb, sub = m.groups()
            if var not in mounted[path] or var not in prefixes:
                continue
            full = re.sub(r":\w+\}", "}", prefixes[var] + sub)
            routes.append(f"{verb.upper()} {full}")
    return routes


def scan_all() -> Dict[str, List[str]]:
    files = scan_files()
    return {
        "page": files["page"],
        "component": files["component"],
        "lib": files["lib"],
        "api": client_calls(),
        "route": backend_routes(),
    }


# --------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------

def read_coverage(problems: List[str]) -> List[Dict[str, str]]:
    if not COVERAGE.exists():
        problems.append(f"missing {COVERAGE.relative_to(ROOT)}")
        return []
    with COVERAGE.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != COLUMNS:
            problems.append(f"coverage.csv header must be {','.join(COLUMNS)}")
            return []
        return [dict(r) for r in reader]


def ticket_files(problems: List[str]) -> Dict[str, Path]:
    files: Dict[str, Path] = {}
    for p in sorted(TICKETS.glob("*.md")):
        m = re.match(r"^(T-\d{3})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$", p.name)
        if not m:
            problems.append(f"ticket file name must look like T-001-some-slug.md: {p.name}")
            continue
        if m.group(1) in files:
            problems.append(f"two ticket files share the id {m.group(1)}")
            continue
        files[m.group(1)] = p
    return files


def check_ticket_file(tid: str, path: Path, problems: List[str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    first = lines[0] if lines else ""
    if not re.match(r"^# " + re.escape(tid) + r" \S", first):
        problems.append(f"{path.name}: first line must be '# {tid} Title'")
    for heading in REQUIRED_HEADINGS:
        if heading not in lines:
            problems.append(f"{path.name}: missing section '{heading}'")
    if "## Tests" in lines:
        start = lines.index("## Tests") + 1
        bullets = 0
        for line in lines[start:]:
            if line.startswith("## "):
                break
            if re.match(r"^\s*[-*] \S", line):
                bullets += 1
        if bullets < 1:
            problems.append(f"{path.name}: '## Tests' needs at least one bullet")


def _string_core(text: str) -> str:
    """Locale text without {placeholders}, lower-cased, first 40 chars."""
    return re.sub(r"\{[^}]*\}", "", text).strip().lower()[:40]


def check_strings(problems: List[str]) -> Tuple[int, int]:
    """Every web locale string must be named in a ticket (by key or text),
    or be listed in unused-strings.txt as `key<TAB>reason`.

    The native app reuses the web's en.json / pt-BR.json, so a string no
    ticket mentions is a screen state, message or label nobody will build.
    """
    import json

    strings = json.loads(LOCALE_EN.read_text(encoding="utf-8"))
    tickets = "\n".join(p.read_text(encoding="utf-8") for p in sorted(TICKETS.glob("T-*.md")))
    lowered = tickets.lower()
    unused: Dict[str, str] = {}
    if UNUSED_STRINGS.exists():
        for line in UNUSED_STRINGS.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            key, _, reason = line.partition("\t")
            if not reason.strip():
                problems.append(f"unused-strings.txt: {key} needs a reason after a tab")
            unused[key.strip()] = reason
    web = _frontend_text()
    for key in unused:
        if key not in strings:
            problems.append(f"unused-strings.txt: {key} is not in en.json any more")
        elif re.search(r"['\"`]" + re.escape(key) + r"['\"`]", web):
            problems.append(f"unused-strings.txt: {key} is used by the web app")
    for key, text in strings.items():
        if key in unused or key in tickets:
            continue
        core = _string_core(text)
        if len(core) >= 4 and core in lowered:
            continue
        problems.append(f"string {key} (\"{text[:50]}\") is in no ticket and not in unused-strings.txt")
    return len(strings), len(unused)


# --------------------------------------------------------------------------
# Extra coverage classes (round 3): web tests, storage, dialogs, timers, keys,
# and the citation map. REPORT mode only until ENFORCE_NEW_CLASSES is True.
#
#     python3 -I mobile/parity/check.py --report
#
# prints every class with its total and its uncovered items and writes
# mobile/parity/report-r3.txt and mobile/parity/uncited-lines.txt. Without
# --report these scanners are never called, so a bug in them cannot break the
# normal check.
#
# TODO(round 4): flip ENFORCE_NEW_CLASSES to True once the tickets are fixed.
# Then classes 1-5 (not the citation map) add one problem per uncovered item.
# --------------------------------------------------------------------------

ENFORCE_NEW_CLASSES = True

REPORT_FILE = ROOT / "mobile" / "parity" / "report-r3.txt"
UNCITED_FILE = ROOT / "mobile" / "parity" / "uncited-lines.txt"
UNMAPPED_TESTS = ROOT / "mobile" / "parity" / "unmapped-web-tests.txt"
LOCALE_DIR_REL = "frontend/src"
MIN_UNCITED_RUN = 15
# Svelte <style> blocks are design, not behaviour; they are counted apart and
# are not part of the "uncited lines" ranking unless this is True.
COUNT_STYLE_LINES = False
EXPECTED_WEB_TESTS = None  # set to (describes, its) to assert the scanner's counts


def _rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def source_files() -> List[Path]:
    """Every non-test .svelte/.ts file under frontend/src (App, main, api, lib, ...)."""
    out = []
    for p in sorted(SRC.rglob("*")):
        if p.suffix not in (".svelte", ".ts"):
            continue
        n = p.name
        if n.endswith((".test.ts", ".d.ts")) or n == "test-setup.ts":
            continue
        out.append(p)
    return out


def test_files() -> List[Path]:
    return sorted(SRC.rglob("*.test.ts"))


def _ticket_texts() -> Dict[str, str]:
    return {p.name.split("-", 2)[0] + "-" + p.name.split("-", 2)[1]: p.read_text(encoding="utf-8")
            for p in sorted(TICKETS.glob("T-*.md"))}


def _section(text: str, heading: str) -> str:
    out: List[str] = []
    on = False
    for line in text.splitlines():
        if line.startswith("## "):
            on = line.strip() == heading
            continue
        if on:
            out.append(line)
    return "\n".join(out)


_PATH_IN_TICKET = re.compile(r"`((?:frontend|backend)/[\w./-]+\.(?:svelte|ts|js|py|json))")


def source_owners(tickets: Dict[str, str]) -> Dict[str, List[str]]:
    """file path (repo relative) -> tickets whose '## Web source' names it.

    A file may have several owners (TripDetailPage, SettingsPage). An item in
    that file is covered when ANY owner covers it. A file nobody names has no
    owner and its items are uncovered with `owner: none`.
    """
    owners: Dict[str, List[str]] = {}
    for tid, text in tickets.items():
        for m in _PATH_IN_TICKET.finditer(_section(text, "## Web source")):
            lst = owners.setdefault(m.group(1), [])
            if tid not in lst:
                lst.append(tid)
    return owners


def _owner_text(owners: Dict[str, List[str]], tickets: Dict[str, str], rel: str) -> Tuple[List[str], str]:
    ids = owners.get(rel, [])
    return ids, "\n".join(tickets[i] for i in ids)


def _code_lines(path: Path) -> List[Tuple[int, str]]:
    """(1-based line number, text) for lines that are not full-line comments."""
    out = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip().startswith(("*", "//", "/*", "<!--")):
            continue
        out.append((n, line))
    return out


def _norm(s: str) -> str:
    s = s.replace("’", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip().lower()


def _balanced_args(text: str, open_idx: int) -> List[str]:
    """Top-level arguments of the call whose '(' is at text[open_idx]."""
    depth, args, cur, i = 0, [], [], open_idx
    quote = ""
    while i < len(text):
        ch = text[i]
        if quote:
            cur.append(ch)
            if ch == "\\":
                i += 1
                cur.append(text[i:i + 1])
            elif ch == quote:
                quote = ""
        elif ch in "'\"`":
            quote = ch
            cur.append(ch)
        elif ch in "([{":
            depth += 1
            if depth > 1:
                cur.append(ch)
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                args.append("".join(cur).strip())
                return args
            cur.append(ch)
        elif ch == "," and depth == 1:
            args.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
        i += 1
    return args


def _line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def _strip_comment_lines(text: str) -> str:
    """Blank out full-line comments, keeping line numbers."""
    return "\n".join("" if l.strip().startswith(("*", "//", "/*", "<!--")) else l for l in text.splitlines())


def _consts(text: str) -> Dict[str, str]:
    """`const NAME = 'x'` (also indented, also `export const`)."""
    return {m.group(1): m.group(3) for m in re.finditer(
        r"\bconst\s+(\w+)\s*(?::\s*\w+\s*)?=\s*(['\"])(.*?)\2", text)}


# ---- 1. web tests ---------------------------------------------------------

_TEST_CALL = re.compile(r"^(\s*)(describe|it|test)\(\s*(['\"`])((?:\\.|(?!\3).)*)\3", re.M | re.S)


def scan_web_tests() -> List[Dict[str, object]]:
    """Every it()/test() with its file, line and describe path.

    The describe path comes from indentation (the files are prettier-formatted:
    an `it` at column 2 is inside the `describe` at column 0 above it).
    """
    items: List[Dict[str, object]] = []
    describes = 0
    for p in test_files():
        text = p.read_text(encoding="utf-8")
        stack: List[Tuple[int, str]] = []
        for m in _TEST_CALL.finditer(text):
            indent = len(m.group(1).replace("\n", ""))
            kind, title = m.group(2), re.sub(r"\s+", " ", m.group(4))
            stack = [s for s in stack if s[0] < indent]
            if kind == "describe":
                describes += 1
                stack.append((indent, title))
                continue
            items.append({
                "file": _rel(p), "line": _line_of(text, m.start()),
                "describe": " > ".join(s[1] for s in stack), "title": title,
            })
    scan_web_tests.describes = describes  # type: ignore[attr-defined]
    return items


_STOP = {"with", "that", "when", "from", "this", "have", "does", "into", "then", "only", "each",
         "every", "than", "them", "their", "there", "which", "while", "will", "were", "also",
         "should", "never", "again", "still", "same", "other", "after", "before"}


def _stems(title: str) -> List[str]:
    words = re.findall(r"[a-z0-9]+", title.lower())
    return sorted({w[:5] for w in words if len(w) >= 4 and w not in _STOP})


def _tests_bullets(text: str) -> List[str]:
    """Logical bullets of '## Tests' (a bullet and its wrapped continuation lines), lower-cased."""
    out: List[str] = []
    for line in _section(text, "## Tests").splitlines():
        if re.match(r"^\s*[-*] ", line) or not out or not line.strip():
            if line.strip():
                out.append(line.strip())
        else:
            out[-1] += " " + line.strip()
    return [re.sub(r"[^a-z0-9]+", " ", b.lower()) for b in out]


def _read_waivers() -> Dict[str, str]:
    waived: Dict[str, str] = {}
    if UNMAPPED_TESTS.exists():
        for line in UNMAPPED_TESTS.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            key, _, reason = line.partition("\t")
            waived[key.strip()] = reason.strip()
    return waived


def check_web_tests(tickets: Dict[str, str], owners: Dict[str, List[str]]) -> Dict[str, object]:
    """Rule (exact):

    A. FILE: every test file must be listed by an OWNER ticket on a line
       `Web tests mirrored: <path-or-basename>[, <more>]`. Owners of a test
       file are the tickets whose '## Web source' names the source file it
       tests (X.test.ts -> X.svelte | X.ts | frontend/X.js) or names the test
       file itself. `unmapped-web-tests.txt` key `<test file>::*` waives A.
    B. TITLE: every it()/test() title must occur WHOLE (lower-cased, letters
       and digits only, other characters as single spaces) inside one bullet
       of the '## Tests' section of some ticket, normally as
       `(web test: "<title>")` at the end of the native test that mirrors it.
       Owner tickets are tried first. Or the
       key `<file>::<describe path> > <title>` is in unmapped-web-tests.txt.
    A test is covered when both hold. Both failures are reported separately.
    """
    items = scan_web_tests()
    waived = _read_waivers()
    bullets = {tid: _tests_bullets(text) for tid, text in tickets.items()}
    mirrored: Dict[str, Set[str]] = {}
    for tid, text in tickets.items():
        for m in re.finditer(r"^[ \t>*-]*Web tests mirrored:\s*(.+)$", text, flags=re.M | re.I):
            for part in re.split(r"[,;]\s*", m.group(1)):
                mirrored.setdefault(tid, set()).add(part.strip().strip("`").strip())
    file_owners: Dict[str, List[str]] = {}
    for p in test_files():
        rel = _rel(p)
        stem = p.name[: -len(".test.ts")]
        cands = [_rel(p.with_name(stem + ext)) for ext in (".svelte", ".ts")]
        if stem == "sw":
            cands.append("frontend/sw.js")
        ids: List[str] = []
        for c in cands + [rel]:
            for tid in owners.get(c, []):
                if tid not in ids:
                    ids.append(tid)
        file_owners[rel] = ids
    file_ok: Dict[str, bool] = {}
    for rel, ids in file_owners.items():
        base = rel.rsplit("/", 1)[1]
        file_ok[rel] = (rel + "::*") in waived or any(
            rel in mirrored.get(t, set()) or base in mirrored.get(t, set()) for t in ids)
    uncovered = []
    for it in items:
        rel = str(it["file"])
        key = f"{rel}::{it['describe']} > {it['title']}" if it["describe"] else f"{rel}::{it['title']}"
        reasons = []
        if not file_ok[rel]:
            reasons.append("file-not-mirrored")
        title_ok = key in waived
        if not title_ok:
            stems = _stems(str(it["title"]))
            plain = re.sub(r"[^a-z0-9]+", " ", str(it["title"]).lower()).strip()
            order = file_owners[rel] + [t for t in bullets if t not in file_owners[rel]]
            for tid in order:
                for b in bullets[tid]:
                    if plain and plain in b:
                        title_ok = True
                        break
                if title_ok:
                    break
        if not title_ok:
            reasons.append("title-not-in-tests")
        if reasons:
            uncovered.append((it, reasons, file_owners[rel], key))
    return {"total": len(items), "describes": scan_web_tests.describes,  # type: ignore[attr-defined]
            "uncovered": uncovered, "files": file_owners, "file_ok": file_ok}


# ---- 2. storage -----------------------------------------------------------

def scan_storage() -> List[Dict[str, object]]:
    items = []
    call = re.compile(r"\b(local|session)Storage\s*\.\s*(getItem|setItem|removeItem)\s*\(")
    for p in source_files():
        raw = p.read_text(encoding="utf-8")
        text = _strip_comment_lines(raw)
        consts = _consts(text)
        for m in call.finditer(text):
            args = _balanced_args(text, m.end() - 1)
            arg = args[0] if args else ""
            lit = re.fullmatch(r"(['\"`])(.*)\1", arg)
            key = lit.group(2) if lit else consts.get(arg, "")
            items.append({"file": _rel(p), "line": _line_of(text, m.start()),
                          "item": f"{m.group(1)}Storage.{m.group(2)} {key!r}" if key else
                                  f"{m.group(1)}Storage.{m.group(2)} <unresolved {arg}>",
                          "key": key})
    return items


def check_storage(tickets, owners) -> Tuple[int, list]:
    items = scan_storage()
    bad = []
    for it in items:
        ids, text = _owner_text(owners, tickets, str(it["file"]))
        key = str(it["key"])
        # Quoted or backticked only: 'locale', 'theme' are also plain words.
        ok = bool(key) and re.search(r"['\"`]" + re.escape(key) + r"['\"`]", text) is not None
        if not ok:
            bad.append((it, ids))
    return len(items), bad


# ---- 3. dialogs -----------------------------------------------------------

def scan_dialogs() -> List[Dict[str, object]]:
    items = []
    call = re.compile(r"(?<![\w.$])(confirm|alert|prompt)\s*\(")
    for p in source_files():
        text = _strip_comment_lines(p.read_text(encoding="utf-8"))
        for m in call.finditer(text):
            args = _balanced_args(text, m.end() - 1)
            items.append({"file": _rel(p), "line": _line_of(text, m.start()),
                          "item": f"{m.group(1)}({args[0] if args else ''})", "expr": args[0] if args else ""})
    return items


def _en_strings() -> Dict[str, str]:
    import json
    return json.loads(LOCALE_EN.read_text(encoding="utf-8"))


def dialog_covered(expr: str, text: str, strings: Dict[str, str]) -> bool:
    """Three kinds of message:
    1. `$t('key', ...)` (possibly `+ '?'`): covered when the locale key, or the
       first 40 chars of its en.json text, appear in an owner ticket.
    2. static or template text: covered when its longest static fragment (the
       `${...}` parts removed, 4+ chars) appears in an owner ticket.
    3. fully dynamic (`(err as Error).message`, `emailError`): covered when an
       owner ticket contains the word `alert` (the exact text is the server's).
    """
    low = _norm(text)
    m = re.search(r"\$t\(\s*['\"]([\w.]+)['\"]", expr)
    if m:
        key = m.group(1)
        if key in text:
            return True
        core = _string_core(strings.get(key, ""))
        return len(core) >= 4 and core in low
    parts = [re.sub(r"\$\{[^}]*\}", "\x00", q[1]) for q in re.findall(r"(['\"`])((?:\\.|(?!\1).)*)\1", expr)]
    frags = [f.strip() for part in parts for f in part.split("\x00") if len(f.strip()) >= 4]
    if frags:
        frag = max(frags, key=len)
        return _norm(frag) in low
    return re.search(r"\balert\b", text, flags=re.I) is not None


def check_dialogs(tickets, owners) -> Tuple[int, list]:
    items = scan_dialogs()
    strings = _en_strings()
    bad = []
    for it in items:
        ids, text = _owner_text(owners, tickets, str(it["file"]))
        if not dialog_covered(str(it["expr"]), text, strings):
            bad.append((it, ids))
    return len(items), bad


# ---- 4. timers ------------------------------------------------------------

def scan_timers() -> List[Dict[str, object]]:
    items = []
    call = re.compile(r"(?<![\w.$])(setTimeout|setInterval)\s*\(")
    for p in source_files():
        text = _strip_comment_lines(p.read_text(encoding="utf-8"))
        for m in call.finditer(text):
            args = _balanced_args(text, m.end() - 1)
            delay = args[-1] if len(args) >= 2 else "<none>"
            value = None
            if re.fullmatch(r"\d[\d_]*", delay):
                value = int(delay.replace("_", ""))
            elif re.fullmatch(r"[A-Za-z_]\w*", delay):  # identifier: its default value in this file
                d = re.search(r"\b" + re.escape(delay) + r"\s*(?::\s*\w+\s*)?=\s*(\d[\d_]*)", text)
                if d:
                    value = int(d.group(1).replace("_", ""))
            items.append({"file": _rel(p), "line": _line_of(text, m.start()),
                          "item": f"{m.group(1)} delay {delay}" + (f" (= {value} ms)" if value is not None and delay != str(value) else ""),
                          "ms": value})
    return items


def delay_forms(ms: int) -> List[str]:
    """Regexes for how a ticket may state a delay. A unit is always required
    (a bare `150` also matches citations like `150-170`)."""
    forms = [rf"(?<![\d.,_-]){ms}\s?(?:ms|milliseconds?)\b",
             rf"(?<![\d.,_-]){ms:,}\s?(?:ms|milliseconds?)\b"]
    if ms % 1000 == 0 or ms % 100 == 0:
        sec = ms / 1000
        s = f"{sec:g}"
        forms.append(rf"(?<![\d.,_-]){re.escape(s)}[\s-]?(?:s|sec|secs|seconds?)\b")
        if ms == 1000:
            forms.append(r"\bevery second\b|\beach second\b|\bper second\b|\bonce a second\b")
        if ms % 60000 == 0:
            n = ms // 60000
            forms.append(rf"(?<![\d.,_-]){n}[\s-]?(?:minutes?|min)\b")
            if n == 1:
                forms.append(r"\bevery minute\b|\bper minute\b|\ba minute\b")
    return forms


_TIMER_WORDS = re.compile(
    r"debounc|delay|timeout|timer|poll|interval|every|after|autosave|auto-save|dismiss|fade|"
    r"disappear|clear|refresh|wait|fallback|tick|countdown|retry|blur|toast|settle|reset|\bsaved\b", re.I)


def _delay_in_context(ms: int, text: str) -> bool:
    """The delay, with a unit, within 200 characters of a timer word
    (debounce, delay, every, after, poll, ...). A shared ticket may mention
    '2 s' for something else; the timer word is what ties it to a timer."""
    for f in delay_forms(ms):
        for m in re.finditer(f, text, flags=re.I):
            if _TIMER_WORDS.search(text[max(0, m.start() - 200): m.end() + 200]):
                return True
    return False


def check_timers(tickets, owners) -> Tuple[int, list]:
    items = scan_timers()
    bad = []
    for it in items:
        ids, text = _owner_text(owners, tickets, str(it["file"]))
        ms = it["ms"]
        ok = ms is not None and _delay_in_context(int(ms), text)
        if not ok:
            bad.append((it, ids))
    return len(items), bad


# ---- 5. keyboard keys -----------------------------------------------------

_KEY_ALIASES = {
    "Enter": r"\bEnter\b|\bReturn\b",
    "Escape": r"\bEscape\b|\bEsc\b",
    "ArrowDown": r"\bArrowDown\b|\bArrow Down\b|\bdown arrow\b",
    "ArrowUp": r"\bArrowUp\b|\bArrow Up\b|\bup arrow\b",
    "ArrowLeft": r"\bArrowLeft\b|\bArrow Left\b|\bleft arrow\b",
    "ArrowRight": r"\bArrowRight\b|\bArrow Right\b|\bright arrow\b",
    "Backspace": r"\bBackspace\b",
    "Tab": r"\bTab\b(?= key)|\bTab\b(?=,)|`Tab`",
    " ": r"\bSpace\b|\bSpacebar\b",
}


def scan_keys() -> List[Dict[str, object]]:
    """Keyboard branches: `x.key === 'Enter'` (either order) and
    `['A','B'].includes(x.key)`. `.key` on data objects (`a.key`) and
    `case 'x'` of other switches are not keyboard checks and are ignored."""
    items = []
    kb = r"(?:\w+\??\.key|(?:e|ev|evt|event)\.code)"  # `x.key`, or `e.code`; not `err.code`
    eq = re.compile(kb + r"\s*[!=]==?\s*(['\"])(.*?)\1|(['\"])(.*?)\3\s*[!=]==?\s*" + kb)
    inc = re.compile(r"\[((?:\s*['\"][^'\"]*['\"]\s*,?)+)\]\s*\.includes\(\s*" + kb + r"\s*\)")
    for p in source_files():
        text = _strip_comment_lines(p.read_text(encoding="utf-8"))
        for m in eq.finditer(text):
            key = m.group(2) if m.group(2) is not None else m.group(4)
            items.append({"file": _rel(p), "line": _line_of(text, m.start()), "item": f"key {key!r}", "key": key})
        for m in inc.finditer(text):
            for k in re.findall(r"['\"]([^'\"]*)['\"]", m.group(1)):
                items.append({"file": _rel(p), "line": _line_of(text, m.start()), "item": f"key {k!r}", "key": k})
        # switch (e.key) { case 'x': ... }
        for sm in re.finditer(r"switch\s*\(\s*" + kb + r"\s*\)\s*\{", text):
            body = text[sm.end(): sm.end() + 1500]
            for cm in re.finditer(r"case\s+(['\"])(.*?)\1\s*:", body):
                items.append({"file": _rel(p), "line": _line_of(text, sm.end() + cm.start()),
                              "item": f"key {cm.group(2)!r}", "key": cm.group(2)})
    return items


def check_keys(tickets, owners) -> Tuple[int, list]:
    items = scan_keys()
    bad = []
    for it in items:
        ids, text = _owner_text(owners, tickets, str(it["file"]))
        key = str(it["key"])
        pat = _KEY_ALIASES.get(key, r"(?<![\w])" + re.escape(key) + r"(?![\w])")
        # Case-sensitive on purpose: "enter" and "escape" are ordinary words.
        if not re.search(pat, text):
            bad.append((it, ids))
    return len(items), bad


# ---- 6. citation map ------------------------------------------------------

_FILE_MENTION = re.compile(
    r"(?P<path>(?:[\w.-]+/)*[\w.-]*\w\.(?:svelte|ts|js|css|json|py))(?![\w])"
    r"|(?<![\w/.])(?P<stem>[A-Z][A-Za-z0-9]+)(?=\s+\d)")
_UNIT_AFTER = r"(?!\w)(?!\.\d)(?!\s*(?:px|ms|rem|em|%|min\b|MB|KB|chars?|days?|h\b|s\b|in each))"
_NUM = r"~?(\d{1,5})(?:\s*[-\u2013]\s*(\d{1,5}))?" + _UNIT_AFTER
_NAME = r"(?:`[A-Za-z_][\w$]*`\s*)?"  # an optional `identifier` between the file and its numbers


def parse_citations(text: str, by_name: Dict[str, str], by_stem: Dict[str, str],
                    lengths: Dict[str, int],
                    owned: Optional[Set[str]] = None) -> Tuple[Dict[str, List[Tuple[int, int]]], List[str]]:
    """Line citations in one ticket: {source path: [(from, to)]}, plus stale notes.

    A file is "named" by `dir/File.ext`, `File.ext` (any extension) or a bare
    component name directly followed by a number (`FlightDetailPage 258-264`).
    Numbers that belong to it:
      * directly after the name: `File.svelte:12`, `file.ts:12-30`, `File.svelte 218`,
        `lines 55-117`, `~1638-1648`, optional `identifier` first (`utils.ts` `cabinLabel` 165-173);
      * a list continues after `,` / `;` / `and`, with an optional (note) first:
        `lines 253-310 (note), 983-1037`, `280, 471`.
    Numbers with no file directly before them are attached to the NEAREST FILE
    NAMED EARLIER IN THE SAME TICKET (any line), preferring files the ticket
    lists in its '## Web source' (`owned`), because a ticket cites its own file
    far more often than a helper it mentions in passing, and only a file long
    enough to hold the cited line (a number past the end of a file is listed as
    stale and cites nothing; `:1-65535` is a port range, not a citation): `:700-830`, `lines 12-30`, `line 9`,
    `~1638-1648`, and parenthesised ranges `(405-422)`, `(293-301, 337-345)`,
    `(1-436 script and markup)`. Units (20px, 2.75rem, 480px, 14:00) and
    prose like `783 in each` are never numbers here.
    """
    cites: Dict[str, List[Tuple[int, int]]] = {}
    stale: List[str] = []

    def add(res: Optional[str], a: int, b: int) -> None:
        if not res:
            return
        lo, hi = min(a, b), max(a, b)
        if hi > lengths.get(res, 10 ** 9):  # past the end of the file: stale, cites nothing
            stale.append(f"{res}:{lo}-{hi}" if lo != hi else f"{res}:{lo}")
            return
        cites.setdefault(res, []).append((lo, hi))

    events: List[Tuple[int, int, Optional[str]]] = []
    for m in _FILE_MENTION.finditer(text):
        path = m.group("path")
        if path:
            if path.startswith("frontend/src/"):
                res = path if path in lengths else None
            elif path.startswith(("frontend/", "backend/")):
                res = None
            else:
                res = by_name.get(path.rsplit("/", 1)[-1])
        else:
            res = by_stem.get(m.group("stem"))
        events.append((m.start(), m.end(), res))
    consumed: List[Tuple[int, int]] = []
    for _, end, res in events:
        tail = text[end:end + 400]
        p, first = 0, True
        while True:
            sep = (r"[\s`:(~]*(?:lines?\s*)?" if first else
                   r"(?:\s*\([^()]*\))?\s*(?:,|;|\band\b)\s*(?:lines?\s*)?") + _NAME
            mm = re.match(sep + _NUM, tail[p:], flags=re.I)
            if not mm:
                break
            add(res, int(mm.group(1)), int(mm.group(2) or mm.group(1)))
            consumed.append((end + p, end + p + mm.end()))
            p += mm.end()
            first = False

    def nearest(pos: int, hi: int) -> Optional[str]:
        earlier = [res for start, end, res in events if end <= pos and res]
        fits = [r for r in reversed(earlier) if lengths.get(r, 0) >= hi]
        owned_fits = [r for r in fits if owned and r in owned]
        return (owned_fits or fits or earlier[::-1] or [None])[0]

    rng = r"~?(\d{1,5})\s*[-\u2013]\s*(\d{2,5})"
    standalone = [
        re.compile(r"(?<![\w.])(?::|lines?\s+)" + _NUM, re.I),
        re.compile(r"(?<![\w.\d])~" + _NUM),
    ]
    for pat in standalone:
        for m in pat.finditer(text):
            if any(s <= m.start() < e for s, e in consumed):
                continue
            hi = int(m.group(2) or m.group(1))
            add(nearest(m.start(), max(hi, int(m.group(1)))), int(m.group(1)), hi)
            consumed.append((m.start(), m.end()))
    for m in re.finditer(r"\(\s*" + rng + r"(?=[\s,;)])((?:\s*,\s*" + rng + r"(?=[\s,;)]))*)", text):
        if any(s <= m.start() < e for s, e in consumed):
            continue
        ctx = nearest(m.start(), int(m.group(2)))
        add(ctx, int(m.group(1)), int(m.group(2)))
        for r2 in re.finditer(rng, m.group(3)):
            add(ctx, int(r2.group(1)), int(r2.group(2)))
    return cites, stale


def _countable_lines(path: Path) -> Tuple[List[int], Set[int], int]:
    """(line numbers that count, style line numbers, total lines).
    Blank lines and import statements (including multi-line ones) do not count."""
    lines = path.read_text(encoding="utf-8").splitlines()
    style: Set[int] = set()
    if path.suffix == ".svelte":
        inside = False
        for n, l in enumerate(lines, 1):
            if re.match(r"\s*<style\b", l):
                inside = True
            if inside:
                style.add(n)
            if "</style>" in l:
                inside = False
    out: List[int] = []
    in_import = False
    for n, l in enumerate(lines, 1):
        s = l.strip()
        if in_import:
            if re.search(r"\bfrom\s+['\"]", s) or s.endswith(";"):
                in_import = False
            continue
        if not s:
            continue
        if re.match(r"import\b", s) and not re.match(r"import\s*\(", s):
            if not (re.search(r"\bfrom\s+['\"]", s) or re.match(r"import\s+['\"]", s)):
                in_import = True
            continue
        out.append(n)
    return out, style, len(lines)


def citation_map(tickets: Dict[str, str], owners: Dict[str, List[str]]) -> Dict[str, object]:
    files = source_files()
    by_name: Dict[str, str] = {}
    dup: Set[str] = set()
    for p in files:
        if p.name in by_name:
            dup.add(p.name)
        by_name[p.name] = _rel(p)
    for d in dup:
        del by_name[d]
    by_stem = {p.stem: _rel(p) for p in files if p.suffix == ".svelte" and p.stem[:1].isupper()}
    lengths = {_rel(p): len(p.read_text(encoding="utf-8").splitlines()) for p in files}
    cited: Dict[str, Set[int]] = {}
    stale: List[str] = []
    n_cites = 0
    for tid, text in sorted(tickets.items()):
        owned = {f for f, ids in owners.items() if tid in ids}
        c, s = parse_citations(text, by_name, by_stem, lengths, owned)
        stale += [f"{tid} {x}" for x in s]
        for f, rs in c.items():
            n_cites += len(rs)
            for a, b in rs:
                cited.setdefault(f, set()).update(range(a, b + 1))
    rows = []
    for p in files:
        rel = _rel(p)
        lines, style, _ = _countable_lines(p)
        use = [n for n in lines if COUNT_STYLE_LINES or n not in style]
        unc = [n for n in use if n not in cited.get(rel, set())]
        runs: List[Tuple[int, int, int]] = []
        run: List[int] = []
        for n in use:
            if n in cited.get(rel, set()):
                if len(run) >= MIN_UNCITED_RUN:
                    runs.append((run[0], run[-1], len(run)))
                run = []
            else:
                run.append(n)
        if len(run) >= MIN_UNCITED_RUN:
            runs.append((run[0], run[-1], len(run)))
        rows.append({"file": rel, "runs": runs, "uncited": len(unc), "counted": len(use),
                     "style": len([n for n in lines if n in style])})
    rows.sort(key=lambda r: (-int(r["uncited"]), str(r["file"])))  # type: ignore[arg-type]
    return {"rows": rows, "citations": n_cites, "stale": sorted(set(stale))}


def format_uncited(cm: Dict[str, object]) -> str:
    out = [
        "# Uncited lines: source lines no ticket cites by a File:line citation.",
        "# Counted: non-blank, non-import lines (blank and import lines do not break a run; they are",
        f"# skipped over). <style> blocks of .svelte files are {'included' if COUNT_STYLE_LINES else 'left out (listed as style lines)'}.",
        f"# A range is listed when it holds {MIN_UNCITED_RUN}+ consecutive uncited counted lines.",
        f"# citations parsed: {cm['citations']}; sorted by uncited lines desc, then path.",
        "# file<TAB>uncited lines<TAB>of counted<TAB>style lines (not counted)<TAB>ranges (from-to:lines)",
    ]
    for r in cm["rows"]:  # type: ignore[union-attr]
        rr = ", ".join(f"{a}-{b}:{n}" for a, b, n in r["runs"])
        out.append(f"{r['file']}\t{r['uncited']}\t{r['counted']}\t{r['style']}\t{rr}")
    out.append("")
    out.append("# citations past the end of their file (stale line numbers):")
    out += ["#   " + s for s in cm["stale"]] or ["#   none"]  # type: ignore[union-attr]
    return "\n".join(out) + "\n"


# ---- report ---------------------------------------------------------------

def new_class_results() -> Dict[str, object]:
    tickets = _ticket_texts()
    owners = source_owners(tickets)
    res: Dict[str, object] = {"tickets": tickets, "owners": owners}
    res["web-tests"] = check_web_tests(tickets, owners)
    res["storage"] = check_storage(tickets, owners)
    res["dialogs"] = check_dialogs(tickets, owners)
    res["timers"] = check_timers(tickets, owners)
    res["keys"] = check_keys(tickets, owners)
    res["citations"] = citation_map(tickets, owners)
    return res


def new_class_problems() -> List[str]:
    """Problems for classes 1-5; used only when ENFORCE_NEW_CLASSES is True."""
    res = new_class_results()
    problems = []
    for it, reasons, _, key in res["web-tests"]["uncovered"]:  # type: ignore[index]
        problems.append(f"web-test {key}: {', '.join(reasons)}")
    for cls in ("storage", "dialogs", "timers", "keys"):
        for it, ids in res[cls][1]:  # type: ignore[index]
            problems.append(f"{cls} {it['file']}:{it['line']} {it['item']} (owner: {', '.join(ids) or 'none'})")
    for x in res["citations"]["stale"]:  # type: ignore[index]
        problems.append(f"citation past the end of its file: {x}")
    return problems


def build_report(res: Dict[str, object]) -> str:
    out: List[str] = ["parity report r3 (REPORT mode; nothing here fails the normal check)",
                      f"enforcing: {ENFORCE_NEW_CLASSES}"]
    wt = res["web-tests"]
    unc = wt["uncovered"]  # type: ignore[index]
    nf = sum(1 for ok in wt["file_ok"].values() if not ok)  # type: ignore[index]
    nb = sum(1 for _, r, _, _ in unc if "title-not-in-tests" in r)
    out.append("")
    out.append(f"== web-tests: {wt['total']} tests in {len(wt['files'])} files ({wt['describes']} describes), "  # type: ignore[index]
               f"{len(unc)} uncovered; {nf} files lack 'Web tests mirrored:', {nb} titles match no Tests bullet")
    out.append("-- files without a 'Web tests mirrored:' line (file  owners)")
    for rel, ids in wt["files"].items():  # type: ignore[union-attr]
        if not wt["file_ok"][rel]:  # type: ignore[index]
            out.append(f"  {rel}  owners: {', '.join(ids) or 'none'}")
    out.append("-- titles matching no Tests bullet (file:line  describe > title  owners)")
    for it, reasons, ids, _ in unc:
        if "title-not-in-tests" in reasons:
            d = f"{it['describe']} > " if it["describe"] else ""
            out.append(f"  {it['file']}:{it['line']}  {d}{it['title']}  owners: {', '.join(ids) or 'none'}")
    for cls in ("storage", "dialogs", "timers", "keys"):
        total, bad = res[cls]  # type: ignore[misc]
        out.append("")
        out.append(f"== {cls}: {total} items, {len(bad)} uncovered")
        for it, ids in bad:
            out.append(f"  {it['file']}:{it['line']}  {it['item']}  owner: {', '.join(ids) or 'none'}")
    cm = res["citations"]
    rows = cm["rows"]  # type: ignore[index]
    out.append("")
    out.append(f"== citations: {cm['citations']} parsed, {sum(int(r['uncited']) for r in rows)} uncited lines in "  # type: ignore[index]
               f"{len(rows)} files, {len(cm['stale'])} past end of file (full list: mobile/parity/uncited-lines.txt)")  # type: ignore[index]
    for r in rows[:10]:
        out.append(f"  {r['file']}  uncited {r['uncited']} of {r['counted']}")
    return "\n".join(out) + "\n"


def run_report() -> int:
    res = new_class_results()
    text = build_report(res)
    REPORT_FILE.write_text(text, encoding="utf-8")
    UNCITED_FILE.write_text(format_uncited(res["citations"]), encoding="utf-8")  # type: ignore[arg-type]
    print(text, end="")
    return 0


def verify() -> Tuple[List[str], Dict[str, List[str]], Set[str]]:
    problems: List[str] = []
    scanned = scan_all()
    rows = read_coverage(problems)
    files = ticket_files(problems)

    # Rows: shape, duplicates, tickets.
    by_key: Dict[Tuple[str, str], Dict[str, str]] = {}
    referenced: Set[str] = set()
    for r in rows:
        kind, source, ticket = r["kind"], r["source"], r["ticket"]
        if kind not in KINDS:
            problems.append(f"unknown kind '{kind}' for {source}")
            continue
        if (kind, source) in by_key:
            problems.append(f"duplicate row: {kind} {source}")
        by_key[(kind, source)] = r
        if ticket == "none":
            if kind != "route":
                problems.append(f"{kind} {source}: only routes may have ticket 'none'")
            continue
        if not re.match(r"^T-\d{3}$", ticket):
            problems.append(f"{kind} {source}: bad ticket '{ticket}' (use T-123 or none)")
            continue
        referenced.add(ticket)
        if ticket not in files:
            problems.append(f"{kind} {source}: ticket {ticket} has no file in mobile/tickets/")

    # Sources vs rows.
    scanned_keys: Set[Tuple[str, str]] = set()
    for kind in KINDS:
        for source in scanned[kind]:
            scanned_keys.add((kind, source))
            if (kind, source) not in by_key:
                problems.append(f"not in coverage.csv: {kind} {source}")
    for key in by_key:
        if key not in scanned_keys:
            problems.append(f"coverage.csv row no longer matches any source: {key[0]} {key[1]}")

    # Ticket files.
    for tid, path in files.items():
        check_ticket_file(tid, path, problems)
        if tid not in referenced:
            problems.append(f"{path.name}: no coverage row points to {tid}")

    # Cross-check the web client against the backend.
    route_shapes = {shape(s) for s in scanned["route"]}
    for s in scanned["api"]:
        if shape(s) not in route_shapes:
            problems.append(f"client call has no matching backend route (scanner bug or stale client): {s}")
    used = used_shapes()
    for route in scanned["route"]:
        row = by_key.get(("route", route))
        if row is None:
            continue
        is_used = shape(route) in used
        if is_used and row["ticket"] == "none":
            problems.append(f"route {route} is used by the web app but has ticket 'none'")
        if not is_used and row["ticket"] != "none":
            problems.append(f"route {route} is not used by the web app, so its ticket must be 'none'")
    check_strings(problems)
    if ENFORCE_NEW_CLASSES:
        problems.extend(new_class_problems())
    return problems, scanned, set(files)


def main(argv: List[str]) -> int:
    if "--report" in argv:
        return run_report()
    if "--list" in argv:
        for kind, sources in scan_all().items():
            for source in sources:
                print(f"{kind},{source}")
        return 0
    problems, scanned, tickets = verify()
    if problems:
        print(f"parity check FAILED: {len(problems)} problem(s)")
        for p in problems:
            print("  - " + p)
        return 1
    rows = read_coverage([])
    unused = sum(1 for r in rows if r["kind"] == "route" and r["ticket"] == "none")
    print("parity check passed")
    for kind in KINDS:
        print(f"  {kind + 's':<11}{len(scanned[kind])}")
    print(f"  routes not used by the web app: {unused}")
    total, unused_n = check_strings([])
    print(f"  strings    {total} ({unused_n} listed unused)")
    print(f"  tickets: {len(tickets)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
