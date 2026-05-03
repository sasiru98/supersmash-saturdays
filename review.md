# Supersmash Saturdays — Code Review

Senior engineer pass across all source files. Issues are ranked roughly by priority within each section.

---

## Bugs & Correctness Issues

### 1. ~~XSS / HTML injection via player names~~ ✅ Fixed
`from html import escape as esc` added to `generate_index.py`; all player/team name interpolations wrapped. JS `esc()` helper added to `admin.html`; `pairName()`, team card names, and team member spans all escaped.

---

### 2. ~~Race condition on concurrent score saves~~ ✅ Fixed
`_data_lock = threading.Lock()` added at module level. Both `api_score` and `api_team_name` now hold the lock for their entire load/modify/save cycle.

---

### 3. `git_publish()` continues after git errors — `app.py:34–54`
`run()` collects errors but never short-circuits. If `git checkout dev` fails (e.g. uncommitted changes, wrong branch), the next `git add` runs on whatever branch is currently checked out, potentially committing to the wrong branch.

**Fix:** Return early from `git_publish()` on the first failure, especially for `checkout` and `merge` steps.

```python
if not run(["git", "checkout", "dev"]):
    return errors
```

---

### 4. ~~"Last updated" is load time, not publish time~~ ✅ Fixed
`datetime.now().strftime("%H:%M · %a %d %b")` embedded as a static string at generate time. JS `new Date()` line removed. Timestamp now reflects when Publish was actually hit.

---

### 5. ~~Last round stuck on "Live" after tournament ends~~ ✅ Fixed
`find_current_round` returns `None` when all rounds complete. `rounds_section` guards the Live badge with `current_round_idx is not None`. When all groups are done: hero label switches to "Final Results", a 🏆 Tournament Complete banner appears between header and nav, and rank-1 rows in each standings table get a gold background with `text-white` name.

---

### 6. ~~Odd-sized groups silently drop a player~~ ✅ Fixed
`validate.py` now errors on odd group sizes and unequal group sizes (blocks `app.py` startup with clear messages). `setup.py`'s `edit_groups` shows the same warnings and blocks `[c]ontinue` until all groups are even and equal.

---

### 7. ~~Score save fires on every blur even if unchanged~~ ✅ Fixed
`data-original` stored on `focus`; `blur`/Enter handler skips the fetch if neither input changed. After a successful save, `data-original` is updated so repeat blur is still suppressed.

### 8. ~~No server-side score range validation~~ ✅ Fixed
`parse_score()` helper in `api_score` enforces `0–99`; out-of-range values raise `ValueError` and return a 400.

---

## Duplicated Code / Maintainability

### 9. ~~Duplicate constants across `setup.py` / `validate.py`~~ ✅ Fixed
`core/constants.py` created with `SKILL_ORDER`, `GROUP_NAMES`, `VALID_GENDERS`. Both files now import from it; local definitions removed.

---

### 10. ~~Team standings matched by player name set instead of pair ID~~ ✅ Fixed
`calc_team_standings` now builds a `(group, pair_id) → team_index` lookup from `pair["team"]` before touching any match data. Inner loop uses `dict.get()` by pair ID — no set construction or name comparison per match.

---

## Security Notes

### 11. Admin panel has no authentication
`app.py` binds to `0.0.0.0:5000` with no auth. Anyone on the same WiFi network can POST to `/api/score` or `/api/publish`. For a social tournament this is probably fine, but worth knowing — especially the publish endpoint which runs `git push`.

**Low-risk mitigation:** A single shared password via HTTP Basic Auth or an env-var token check on write endpoints would prevent accidental access.

---

### 12. No CSRF protection on state-changing endpoints
`/api/score`, `/api/team_name`, `/api/publish` accept POST from any origin. Since Flask doesn't set CORS headers, browser-based cross-origin requests are blocked — but `curl` or any non-browser client can call them freely. Same note as above: acceptable for local use, just be aware.

---

## Feature Suggestions

### 13. Tournament complete state
Once all matches in all groups are scored, there's no "finished" indicator on the public page. The last round stays "Live". Consider a banner like "🏆 Tournament Complete" that appears when every score is filled in, and a "Final Standings" emphasis style (e.g. gold border on 1st-place rows).

---

### 14. ~~No auto-refresh on public page~~ ✅ Fixed
`location.reload()` on a 60s timer injected at generate time. Pauses via `visibilitychange` when the tab is backgrounded (saves phone battery). Timer is omitted entirely when `all_complete` is true — no point refreshing a finished tournament.

---

### 15. ~~No QR code on admin panel~~ ✅ Fixed
`get_pages_url()` in `app.py` derives the GitHub Pages URL from `git remote get-url origin` (handles both HTTPS and SSH remotes). A `📱 QR` button in the header toggles a collapsible panel with a 200×200 QR code (QRCode.js via CDN), the URL as text, and a Copy link button. Panel and button are omitted entirely if the remote URL can't be parsed.

---

### 16. ~~No backup before regeneration~~ ✅ Fixed
Two backup files, both gitignored:
- **`tournament.json.bak`** — written by `setup.py` after initial creation, and by `app.py` on every startup after validation passes. Always holds the state from when the server last started.
- **`tournament.json.pre-regen.bak`** — written by `validate.py` immediately before any regeneration. Specific safety net for the one destructive operation.

---

### 18. ~~No round progress indicator~~ ✅ Fixed
Slim progress bar + "X / Y matches" counter injected below the sticky tab bar in `generate_index.py`. Bar is green during the tournament, turns amber and shows "Final" label when all matches are complete.

---

### 20. ~~No badminton score validation~~ ✅ Fixed
`scoreWarning(s1, s2)` checks three rules: equal scores, either score > 30, both ≥ 20 with win margin < 2. Warning text appears in amber on the match card — non-blocking, save still goes through. Warning is populated on initial render for already-saved suspicious scores, and re-evaluated after every save.

---

### 21. ~~Export/print results~~ ✅ Fixed
`core/generate_results.py` added — `finalise()` generates a frozen `past_results/YYYY-MM-DD.html` results page, updates `past_results/index.json`, and regenerates `archive.html`. A `🏆 Finalise` button in the admin header (enabled only when all scores are complete) calls `POST /api/finalise`, which commits all new files to dev, merges to main, and pushes — publishing them to GitHub Pages. The finalise toast shows step progress and clickable links to the results page and the archive. `index.html` footer gains a "Past tournaments →" link to `archive.html` once it exists.

---

## Minor UX / Polish

### 22. Tab keyboard navigation not wired on admin panel
The group tabs in `admin.html` don't respond to arrow keys. This is a standard accessibility expectation for tab widgets but low priority for a tablet-only internal tool.

---

### 23. External resource dependency at match time
`index.html` loads Google Fonts and Tailwind from CDN. If the venue WiFi has a firewall or poor internet, the page renders unstyled. Consider inlining critical CSS or bundling Tailwind at generate time (the CLI version of Tailwind can be run as a one-off before publish).

---

### 24. ~~`setup.py:32–37` — unusual file open pattern~~ ✅ Fixed
```python
try:
    f = open(filepath, "r", encoding="utf-8")
except UnicodeDecodeError:
    f = open(filepath, "r", encoding="utf-8-sig")
with f:
    ...
```
If the second `open()` raises, `f` from the first attempt would already be open and leaked. Use `try/except` around the entire block or use a helper.

---

## Already Well Done

- **No derived data in `tournament.json`** — the "recalculate everything on publish" pattern is clean and makes the data file human-readable and corruption-resistant.
- **`find_current_round`** — the "first round with any unscored match" heuristic is exactly right for this format.
- **`make_pairs` gender-aware pairing** — the top-male / bottom-female balancing logic is thoughtful.
- **`git_publish` branch discipline** — always returning to `dev` at the end of publish is correct.
- **`strip_invisible` / `INVISIBLE` set** — handling zero-width spaces in `players.txt` is the kind of defensive detail that prevents hard-to-debug issues.
- **Separation between admin labels (Advanced/Intermediate/Beginner) and public labels (Sun/Moon/Stars)** — great design for player-facing privacy.

---

*Review date: 2026-05-03*
