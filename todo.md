# Supersmash Saturdays — Todo

## 1. Player Stats Page (public index.html)

A dedicated stats tab or section on the public page showing per-player and group-level statistics.

### Per-player stats (aggregated across their pair)
- Points scored / points conceded / point differential
- Win rate (%)
- Biggest win (largest margin)
- Closest match (smallest margin)
- Head-to-head record against each opponent pair

### Group-level stats (one set per Sun/Moon/Stars group)
- Highest scoring match of the night
- Most dominant pair (highest average point differential)
- Closest contest (lowest average margin across all matches)
- Most points scored by a single pair

### Implementation notes
- Add a "Stats" tab alongside the existing section tabs on index.html
- All stats derived from raw scores in tournament.json — no new data stored
- Only show stats for matches that have been played (skip TBD)
- Stats update on every Publish


## 2. Cross-Skill Team Ranking System

A full team leaderboard on the public page, ranked by combined performance across all three groups.

### Ranking formula
- **Primary:** Total wins across all three pairs (Sun pair + Moon pair + Stars pair)
- **Tiebreaker:** Combined point differential across all three pairs

### Display
- Dedicated leaderboard section above or below the Cross-Skill Teams grid
- Show rank, team name, total wins, combined point diff
- 🥇🥈🥉 medals for top 3 (already implemented on team cards and in group standings)
- Clicking/tapping a team could expand to show each pair's individual record

### Implementation notes
- `calc_team_standings()` already exists in generate_index.py — leaderboard just needs a rendered HTML section
- Update on every Publish
- Only rank teams once at least one match has been played (avoid misleading 0-0 ties at start)


## 3. Player Skill Dictionary

A persistent skill registry that carries ratings forward across multiple sessions. After each tournament, ratings are automatically adjusted based on final standings within each group.

### Rating adjustment rules
Adjustments apply per player based on their **pair's final rank** within their skill group:

| Finish | Adjustment | Example |
|---|---|---|
| 1st place | +2 levels | `B-` → `B+` |
| 2nd place | +1 level | `A` → `A+` |
| 2nd to last | −1 level | `B` → `B-` |
| Last place | −2 levels | `C` → `C+` (floored at `C-`) |
| All others | No change | — |

Ratings are capped at `A+` (ceiling) and `C-` (floor) — no movement beyond the scale.

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
- Consider showing rating changes on the public page after finalisation (e.g. "↑ Tharindu A+ → A+")


## 4. Project Structure Cleanup

Move Python files into a dedicated folder to clean up the root directory.

### Proposed structure
```
supersmash-saturdays/
├── core/
│   ├── setup.py
│   ├── app.py
│   ├── validate.py
│   └── generate_index.py
├── templates/
│   └── admin.html
├── players.txt
├── index.html
├── tournament.json    (gitignored)
├── skills.md          (future)
├── CLAUDE.md
├── todo.md
├── README.md
└── .gitignore
```

### Implementation notes
- Update all relative imports and file path references (`DATA_FILE`, `OUTPUT_FILE`, `PLAYERS_FILE`) to account for the new location — paths should resolve relative to the repo root, not the script location
- `app.py` template folder path will need updating (`template_folder='../templates'`)
- `README.md` run commands will need updating (`python core/setup.py`, `python core/app.py`)
- Test the full flow (setup → validate → serve → publish) after moving
