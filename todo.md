# Supersmash Saturdays — Todo

## 1. Player Stats Page (public index.html)

A dedicated stats tab or section on the public page showing per-player and group-level statistics.

### Per-player stats (aggregated across their pair)
- Points scored / points conceded / point differential
- Win rate (%)
- Biggest win (largest margin)
- Closest match (smallest margin)
- Head-to-head record against each opponent pair

### Group-level stats (one set per Advanced/Intermediate/Beginner group)
- Highest scoring match of the night
- Most dominant pair (highest average point differential)
- Closest contest (lowest average margin across all matches)
- Most points scored by a single pair

### Implementation notes
- Add a "Stats" tab alongside the existing section tabs on index.html
- All stats derived from raw scores in tournament.json — no new data stored
- Only show stats for matches that have been played (skip TBD)
- Stats update on every Publish


## 2. Player Skill Dictionary

A persistent skill registry that carries ratings forward across multiple sessions. After each tournament, ratings are automatically adjusted based on final standings within each group.

### Rating adjustment rules
Adjustments apply per player based on their **pair's final rank** within their skill group:

| Finish | Adjustment | Example |
|---|---|---|
| 1st place | +2 levels | `6` → `4` |
| 2nd place | +1 level | `3` → `2` |
| 2nd to last | −1 level | `5` → `6` |
| Last place | −2 levels | `7` → `9` (floored at `9`) |
| All others | No change | — |

Ratings are capped at `1` (ceiling) and `9` (floor) — no movement beyond the scale.

Both players in a pair receive the same adjustment (they finished together).

### Storage
- Saved to `skills.md` in the repo root — human-readable, manually editable if needed
- Format: one player per line, `Name | Current Rating | Last Updated`
- On each new session, `setup.py` checks `skills.md` first and pre-fills ratings for known players
- Unknown players (new to the group) fall back to manual rating entry as normal

### Workflow
1. Tournament finishes, admin hits a new **"Finalise"** button (separate from Publish)
2. Standings are calculated, adjustments applied, `skills.md` is updated
3. Next session: `setup.py` reads `skills.md`, suggests ratings for returning players
4. Admin can override any suggestion before confirming groups

### Implementation notes
- Adjustments based on pair rank, not individual standings (pairs finish together)
- If a pair ties for a position (equal wins and diff), neither gets adjusted for that position
- `skills.md` should be committed to the repo so it persists across machines
- Remove `skills.md` from `.gitignore` if added there
- Consider showing rating changes on the public page after finalisation (e.g. "↑ Tharindu 1 → 1")


## 3. Floating Court Queue

Replace the fixed round-based schedule with a shared court queue across all groups. 8 courts (odd-numbered: 1, 3, 5, 7, 9, 11, 13, 15) are shared across Advanced, Intermediate, and Beginner matches.

### Match lifecycle
```
Pending (in queue) → In Progress (on court) → Score Entered (editable) → Finalised (locked)
```

- Matches start as **Pending** in a priority-sorted queue
- Admin assigns a match to a court → **In Progress**
- Admin enters score → **Score Entered** (still editable)
- Admin taps a confirm/tick button → **Finalised** (locked, counts toward standings)

### Queue priority
Matches are sorted by:
1. **Longest waiting pair** — whichever pair in the match has been idle longest gets priority
2. **Fewest matches played** — pairs who've played fewer matches get priority
3. A pair that is currently In Progress on a court is excluded from the queue (no double-booking)

### Court management
- Courts are configurable at setup (default: odd numbers 1-15, 8 courts)
- Admin can manually assign any pending match to any free court (override auto-suggestion)
- System can auto-suggest the next best match when a court frees up

### Matchup generation
- Full round-robin matchup list pre-generated at setup (same as current `make_schedule`)
- No round structure — just a flat list of all matchups per group
- If a player leaves early, remaining matches can be marked as forfeited/skipped

### Admin UI changes
- Replace round-based schedule view with:
  - **Courts** — 8 court cards showing current match or "Free"
  - **Queue** — priority-sorted list of pending matches
  - **Completed** — list of finalised matches with scores
- Score entry on the court card itself (same UX — two inputs, blur/Enter to save)
- Confirm/tick button per match to lock the score

### Public page changes
- Replace "Round 1 / Round 2" schedule with:
  - **Now Playing** — which matches are on which courts
  - **Up Next** — top of the queue
- Standings and results grid remain the same (derived from finalised scores)

### tournament.json changes
- Rounds array replaced with flat `matches` array per group
- Each match: `{ "pair1": id, "pair2": id, "score1": null, "score2": null, "status": "pending", "court": null }`
- Status values: `pending`, `in_progress`, `scored`, `finalised`, `skipped`

### Implementation notes
- `make_schedule` still generates all matchups, just stores them flat instead of grouped into rounds
- Queue sorting logic lives in a new `sort_queue()` function
- Court config stored in `tournament.json` top-level: `"courts": [1, 3, 5, 7, 9, 11, 13, 15]`
- Backward-incompatible with current round-based `tournament.json` — requires fresh setup
