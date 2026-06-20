# Supersmash Saturdays — Code Review

Senior-engineer / architect pass over the full codebase as it stands on `dev`.
Findings are ordered by severity. Each one is written to be **actioned directly by an
LLM**: it names the exact file and lines, explains the problem, and gives a concrete fix
(usually with code). Check items off as they are completed.

Schema reminder (current, post-refactor): each `data["groups"][g]` holds a **flat
`"matches"` list**; every match has `id`, `pair1`, `pair2`, `score1`, `score2`,
`status`, `court`, `seq`. Match lifecycle: `pending → in_progress → scored → finalised`.

---

## Critical — Correctness & Data Integrity

### [ ] C1. `tournament.json` is read/written without `encoding="utf-8"`
**Files:** `core/app.py:49` (read), `core/app.py:54` (write), `core/generate_index.py:24` (read), `core/validate.py:222` (read), `core/setup.py:410` (write)

On Windows, `open(path)` and `open(path, "w")` default to the locale code page
(cp1252), **not** UTF-8. Any player or team name with a non-ASCII character (e.g.
`Begoña`, `José`, an emoji) will either raise `UnicodeEncodeError` on save or round-trip
incorrectly. This is the single source of truth, so corruption here is unrecoverable
except via backup. The HTML writers already pass `encoding="utf-8"` — the JSON I/O must too.

**Fix:** add `encoding="utf-8"` to every `tournament.json` open. For writes, also pass
`ensure_ascii=False` so the file stays human-readable:

```python
# app.py / setup.py
def load_data():
    if not os.path.exists(DATA_FILE):
        return None
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    # ... see C2 for the atomic version ...
    json.dump(data, f, indent=2, ensure_ascii=False)
```

Apply the same `encoding="utf-8"` to `generate_index.load_data` and `validate.validate_and_sync`.

---

### [ ] C2. `save_data()` is not atomic — a crash or concurrent read corrupts the live tournament
**Files:** `core/app.py:53-55`, `core/setup.py:409-411`

`json.dump(data, f)` writes in place. If the process is killed mid-write (laptop sleeps,
battery dies, Ctrl-C), `tournament.json` is left truncated and invalid — fatal during a
live event. Compounding this, the read paths (`/api/queue` at `app.py:276`, `/api/data`,
the `/` handler, `generate_index`) call `load_data()` **without** `_data_lock`, so a read
that races a write can see a half-written file and throw.

**Fix:** write to a temp file and `os.replace()` (atomic on the same filesystem), and take
the lock for reads that can run concurrently with a write.

```python
def save_data(data):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, DATA_FILE)   # atomic
```

Then wrap `api_queue`'s `load_data()` in `with _data_lock:` (it currently reads bare).

---

### [ ] C3. Concurrent git operations corrupt the working tree / branch state
**Files:** `core/app.py:58-100` (`git_publish`), `core/app.py:382-434` (`git_finalise`)

Flask's dev server is threaded by default. Both `git_publish` and `git_finalise` perform
`checkout dev → commit → push → checkout main → merge → push → checkout dev`. The current
branch is **global process state**. If Publish and Finalise (or two Publishes) run at
once, their `checkout`/`merge` steps interleave and can commit to the wrong branch, leave
the repo on `main`, or abort a merge half-done. There is no lock around the sequence.

Secondarily: `players.txt` is currently modified in the working tree (`git status` shows
`M players.txt`). If a tracked file differs between `dev` and `main` and is uncommitted,
`git checkout main` aborts and the publish fails mid-way.

**Fix:**
1. Add a module-level `_git_lock = threading.Lock()` and wrap the *entire* body of both
   `git_publish` and `git_finalise` in `with _git_lock:`.
2. Stash or commit tracked changes before switching branches, or operate without switching
   branches (e.g. push `dev` and fast-forward `main` via `git push origin dev:main` when
   it's a strict ancestor — no checkout needed). Prefer eliminating the `checkout main`
   dance entirely:
   ```python
   # after committing + pushing dev, update main without leaving dev:
   run(["git", "push", "origin", "dev:main"], "Pushed main → GitHub Pages")
   ```
   This removes the branch-switch race and the dirty-working-tree failure in one go.

---

### [ ] C4. Removing an in-use court orphans its live match
**File:** `core/app.py:166-179` (`api_courts`)

`api_courts` overwrites `data["courts"]` with whatever list is posted, without checking
whether a removed court currently has an `in_progress`/`scored` match on it. The admin UI
(`renderCourts`, `admin.html:332`) only iterates configured courts, so that match
disappears from the Courts tab while its `status` stays `in_progress` — its two pairs are
permanently "busy", never re-enter the queue, and the match can't be scored or cancelled.

**Fix:** reject removal of a court that has an active match, or auto-unassign it.

```python
active = {m["court"] for gd in data["groups"].values()
          for m in gd["matches"] if m["status"] in ("in_progress", "scored")}
removed = active - set(courts)
if removed:
    return jsonify({"error": f"Courts {sorted(removed)} have live matches; "
                             f"finish or cancel them first"}), 400
```

---

## Bugs & Dead Code

### [ ] B1. `is_tournament_complete()` has inverted logic and is never called
**File:** `core/generate_index.py:65-70`

```python
def is_tournament_complete(data):
    for gd in data["groups"].values():
        for m in gd["matches"]:
            if m.get("status") not in ("finalised", "skipped"):
                return True   # ← returns True when the tournament is NOT complete
    return False
```

The function returns `True` as soon as it finds an *unfinished* match — the opposite of
its name. It is also dead: `generate_index` computes `all_complete` inline (line 439) and
never calls this. A future caller trusting the name will get backwards behaviour.

**Fix:** delete it, or correct and use it:
```python
def is_tournament_complete(data):
    return all(m.get("status") in ("finalised", "skipped")
               for gd in data["groups"].values() for m in gd["matches"])
```

---

### [ ] B2. `"skipped"` status is read in five places but never written anywhere
**Files:** `core/generate_index.py:68,246,350,437`, `templates/admin.html:647`

Every "done" check treats `"skipped"` as terminal, but no endpoint ever sets a match to
`"skipped"` (`app.py` only ever writes `pending`/`in_progress`/`scored`/`finalised`). So
either a planned "skip this match" feature was never finished, or it's cargo-culted noise.
A tournament with a genuinely unplayable match (player left early) can therefore **never
reach "complete"**, so the Finalise button never enables.

**Fix:** decide one:
- Implement it: add `POST /api/skip_match` that sets `status="skipped"` (mirroring
  `api_finalise_match`), and surface a "Skip" action in the Done/Queue UI; **or**
- Remove `"skipped"` from all five checks to avoid implying support that doesn't exist.

---

### [ ] B3. Badminton score rules are enforced only client-side, and non-blockingly
**Files:** `core/app.py:129-135` (`_parse_score`), `templates/admin.html:247-256` (`scoreWarning`)

`scoreWarning` flags ties, scores >30, and "must win by 2" — but it only renders an amber
note; the save still goes through. Server-side `_parse_score` accepts any integer 0–99,
including **equal scores**. A match can be `finalised` with `21–21`, in which case
`calc_standings` awards the win to neither pair (line 45-50) while still counting points —
silently skewing standings. Garbage scores become permanent tournament data.

**Fix:** mirror the rules server-side in `api_finalise_match` (the point of no return),
returning 400 on violation. At minimum reject ties:
```python
if match["score1"] == match["score2"]:
    return jsonify({"error": "Scores cannot be tied"}), 400
```
Consider also enforcing max 30 and win-by-2 there, leaving `api_score` permissive so
in-progress edits aren't blocked mid-typing.

---

## Maintainability & Architecture

### [ ] M1. ~150 lines of HTML shell are duplicated across the two generators
**Files:** `core/generate_index.py:494-600` vs `core/generate_results.py:67-168` (and the archive page at `171-249`)

The `<head>` (fonts, Tailwind CDN, inline styles), hero header, sticky tab bar, progress
bar, footer, and the `showTab` script are copy-pasted between `generate_index` and
`generate_results`. Any visual change (and the CDN-bundling fix in S2) must be made in
two or three places and will drift. This is the biggest maintainability liability.

**Fix:** extract a shared `core/page_shell.py` with a single function, e.g.
`render_page(*, title, hero_label, banner, tab_buttons, body, progress, scripts="", footer_links="")`,
and have both generators call it. Keep the page-specific bits (live vs final accent
colours, auto-refresh script, "Played on" vs "Last updated") as parameters.

---

### [ ] M2. `git_publish` and `git_finalise` are ~95% identical
**Files:** `core/app.py:58-100` and `core/app.py:382-434`

The checkout/commit/push/merge/push/return-to-dev sequence and the nested `run()` helper
are duplicated verbatim. The only differences are the staged files and the commit message.

**Fix:** extract one helper and have both call it (combine with the C3 lock):
```python
def _git_sync(files, commit_msg, extra_steps=None):
    with _git_lock:
        errors, steps = [], list(extra_steps or [])
        def run(cmd, label): ...   # unchanged
        ...  # single copy of the workflow
        return errors, steps
```
`git_publish` → `_git_sync(["index.html"], "Update scores and standings")`;
`git_finalise` → `_git_sync([...results files...], f"Finalise {date_str} ...")`.

---

### [ ] M3. `strip_invisible` duplicates and diverges from `validate.INVISIBLE`
**Files:** `core/setup.py:19-22` vs `core/validate.py:14-35`

`setup.py` defines its invisible-character set as **literal pasted glyphs** — exactly the
"copy-paste ambiguous" pattern the review previously praised `validate.py` for avoiding —
and it's missing the soft hyphen (`­`) that `validate.py` includes. Two sources of
truth that already disagree.

**Fix:** move the `INVISIBLE` set (with `\uXXXX` code-point literals + comments) and the
`clean()`/`strip_invisible()` helper into `core/constants.py`, and import it in both
`setup.py` and `validate.py`.

---

### [ ] M4. `validate.py`'s UTF-8 fallback is misleading and inconsistent with `setup.py`
**File:** `core/validate.py:49-54`

```python
try:
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
except UnicodeDecodeError:
    with open(filepath, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()
```

A UTF-8 BOM does **not** raise `UnicodeDecodeError` under `encoding="utf-8"` — it decodes
to a leading `﻿` char — so the `utf-8-sig` fallback never triggers for the BOM case
it appears to guard. `setup.py:30` was already simplified to a single
`encoding="utf-8-sig"` (review item #24). Make `validate.py` consistent.

**Fix:**
```python
with open(filepath, "r", encoding="utf-8-sig") as f:
    lines = f.readlines()
```
`utf-8-sig` transparently handles both BOM and BOM-less files.

---

### [ ] M5. No automated tests for the scoring / standings / pairing / queue logic
**Files:** (new) `tests/`

The math that decides who wins — `calc_standings`, `calc_team_standings` (tie-breakers),
`make_pairs` (gender-balanced pairing), `assign_groups`, and the `/api/queue` fairness
ordering — has zero test coverage. For a results-critical app this is the highest-value
addition. A regression here is invisible until someone disputes a trophy.

**Fix:** add `pytest` and a `tests/` package with table-driven cases:
- `calc_standings`: W/L counting, point-diff and points-for tie-breakers, ties counted as no-win.
- `calc_team_standings`: combined wins then diff; pairs mapped by `(group, pair_id)`.
- `make_pairs`: N mixed pairs = `min(#M, #F)`; remainder paired top-to-bottom; odd group drops last.
- `api_queue`: pairs with fewer played matches surface first; busy pairs excluded.
Run them in a one-line CI workflow (`pytest -q`).

---

## Security & Operations

### [ ] S1. No auth on write endpoints; server binds `0.0.0.0`; Publish/Finalise run `git push`
**File:** `core/app.py:495` (bind), all `/api/*` POST routes

Anyone on the venue WiFi can `curl` `/api/score`, `/api/assign`, `/api/restore`,
`/api/courts`, and — most importantly — `/api/publish` and `/api/finalise`, which run
`git push`. For a social event the blast radius is small, but a single shared token is
cheap insurance and protects the irreversible publish path.

**Fix:** require a shared secret (env var) on all state-changing routes via a
`before_request` hook checking a header, or Flask-HTTPAuth. Keep GET routes open so the
admin page still renders. Document the token in the run command.

---

### [ ] S2. Match-time pages depend on three CDNs and an unstyled-fallback risk
**Files:** `core/generate_index.py:500-502`, `core/generate_results.py:73-76`, `templates/admin.html:10-11`

The public page and results pages load Google Fonts + Tailwind from CDN; admin also loads
QRCode.js from cdnjs. `https://cdn.tailwindcss.com` is the **play CDN, explicitly "not for
production"** (it compiles in the browser, logs a console warning, and is slow). If venue
WiFi is captive/firewalled/flaky, players see an unstyled page during the event.

**Fix:** bundle CSS at generate time. Run the Tailwind CLI once before publish to emit a
static `styles.css` with only the classes used, commit it, and reference it locally.
Self-host the one font weight set you use. This also removes a privacy/availability
dependency on Google for the public page. (Tie this into the M1 shared shell so it's done once.)

---

### [ ] S3. `assign_groups` silently drops paying players to balance groups
**File:** `core/setup.py:73-95`

When player count isn't divisible by 3 (or groups end up odd/unequal), the bottom
remainder players are **dropped** so groups stay equal and even. The event is moving to
**pay-upfront** — dropping someone who paid is a real-world failure, not just a balance nit.

**Fix:** prefer byes over exclusion. Allow unequal/odd groups and have the round-robin and
queue treat a missing opponent as a bye (no points, counts as "played" for fairness), or
flag the imbalance loudly in setup and force an explicit operator decision rather than a
silent drop. At minimum, surface dropped names as a blocking confirmation, not a print.

---

## Minor / Polish

### [ ] P1. Tab keyboard navigation not wired on admin panel
**File:** `templates/admin.html:233-240` — group tabs don't respond to arrow keys. Low
priority for a tablet-only tool, but it's the standard tab-widget a11y expectation.

### [ ] P2. Pin dependencies
**File:** `requirements.txt` — only `flask>=3.0.0`. Pin an exact version (and add `pytest`
once M5 lands) for reproducible setups across machines.

### [ ] P3. Document the match state machine
**Files:** `core/app.py`, `CLAUDE.md` — the `pending → in_progress → scored → finalised`
lifecycle (and where `seq`/`next_seq` come in) is implicit across endpoints. A short
docstring/diagram at the top of `app.py` would save the next reader (human or LLM) a full
re-derivation — and would have surfaced the `"skipped"` dead state in B2.

---

## Already Well Done
- **No derived data in `tournament.json`** — recompute-on-publish keeps the file
  human-readable and corruption-resistant.
- **`_find_match` + match-status guards** in the new queue endpoints are clean and
  defensive (reject scoring a non-active match, double-assign, etc.).
- **`calc_team_standings` keyed by `(group, pair_id)`** rather than name sets — correct and fast.
- **`/api/queue` fairness ordering** (fewest matches played, then least-recent) is a
  thoughtful way to keep everyone rotating.
- **Branch discipline** — always returning to `dev` after publish is the right instinct
  (just needs the C3 lock to be safe under concurrency).
- **HTML escaping** via `esc()` on both server and client closes the original XSS vector.

---

*Review date: 2026-06-20*
