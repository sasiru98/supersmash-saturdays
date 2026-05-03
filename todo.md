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


## 2. Player Skill Dictionary

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


## 5. Tabs on Public index.html

Replace the single scrolling page with a tabbed layout matching the admin panel.

### Proposed tabs
- **Teams** — cross-skill teams grid with medals and rankings (current default view)
- **☀️ Sun** — standings, results grid, schedule for Advanced group
- **🌙 Moon** — standings, results grid, schedule for Intermediate group
- **⭐ Stars** — standings, results grid, schedule for Beginner group
- **Stats** — player and group stats (once task 1 is built)

### Implementation notes
- Tabs implemented in vanilla JS — no frameworks, keeps index.html fully static
- Active tab persisted in URL hash (e.g. `#moon`) so sharing a link lands on the right tab
- Default tab on load: Teams
- Tab bar should be sticky so it's always accessible while scrolling


## 7. Gender-Aware Pairing

When generating pairs within each skill group, prioritise mixed-gender pairs (one male + one female) over same-gender pairs.

### Pairing rules
- **Priority 1:** Maximise the number of mixed pairs in each group
- **Priority 2:** Where mixed pairing isn't possible (e.g. uneven gender split), fall back to same-gender pairs — best skill match within the same gender
- Same skill-balancing logic still applies within the constraint (top with bottom, etc.)
- Admin can still manually swap players between pairs after generation

### players.txt format change
- Add gender marker to each player line: `Name : Rating : M` or `Name : Rating : F`
- `setup.py` and `validate.py` updated to parse and validate the gender field
- Unknown/missing gender treated as unspecified — falls back to current pairing logic for that player

### Implementation notes
- Gender field is optional for backwards compatibility — if absent, treat as unspecified
- `make_pairs()` in `setup.py` updated with gender-aware matching algorithm
- `validate.py` accepts `M`, `F`, or absent gender — rejects any other value
- Show gender indicator in the pairs review step during setup (e.g. `Tharindu (A+, M) & Nancy (B-, F)`)
