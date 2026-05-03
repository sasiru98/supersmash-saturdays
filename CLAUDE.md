# Supersmash Saturdays — LLM Guide

## What this is
A local Flask tournament manager for a weekly badminton social. Admin runs it on a tablet (local network). Players view live standings via GitHub Pages.

## Stack
- Python + Flask — local admin server (`app.py`)
- `tournament.json` — single source of truth, **gitignored**, never stores derived data
- `generate_index.py` — derives all standings/stats from raw scores, writes `index.html`
- `index.html` — GitHub Pages public page (committed)
- `templates/admin.html` — local-only admin UI (Jinja2 + vanilla JS)
- Tailwind CSS via CDN, Inter font via Google Fonts
- Dark theme (`#080d14` bg), green accents (`#22c55e`)

## Key conventions
- **Never store derived data** in `tournament.json` — only raw scores and structure. Recalculate everything in `generate_index.py` on publish.
- **Group keys are always `A`, `B`, `C`** internally (Advanced/Intermediate/Beginner). Public-facing names are `☀️ Sun / 🌙 Moon / ⭐ Stars` — set in `GROUP_PUBLIC` in `generate_index.py`. Admin always shows internal names.
- **Equal-size groups** — players sorted by rating, split evenly into thirds. Rating letters (A/B/C) are for sorting only, not for group assignment.
- **`players.txt` is the group editor** — after setup it has `# Advanced / # Intermediate / # Beginner` section headers. Moving a player between sections and restarting `app.py` triggers a regeneration prompt.
- **Git flow** — work on `dev`, publish merges to `main` and pushes both. `main` is always clean for GitHub Pages.

## Files to know
| File | Purpose |
|---|---|
| `core/setup.py` | One-time interactive pipeline — parses players, assigns groups, generates pairs/schedule, writes `tournament.json` and `players.txt` |
| `core/validate.py` | Called on `app.py` startup — validates `players.txt`, detects group changes, offers to regenerate |
| `core/generate_index.py` | Derives standings, grids, schedules from `tournament.json`, writes `index.html` |
| `core/app.py` | Flask server — 4 API endpoints: `/api/score`, `/api/team_name`, `/api/publish`, `/api/data` |
| `players.txt` | Editable after setup — sectioned by group, rewritten after each confirmed setup |
| `todo.md` | Planned features — check here before adding anything new |

## Ratings scale
`A+  A  A-  B+  B  B-  C+  C  C-` (best to worst, defined in `SKILL_ORDER`)

## Ranking logic
- Standings: wins → point differential → points scored
- Team rankings: combined wins across all 3 pairs → combined point diff
- Medals: 🥇🥈🥉 on team cards and next to team badges in group standings

## What to avoid
- Don't add interactivity to `index.html` — it's a static file served by GitHub Pages
- Don't persist anything extra to `tournament.json` — keep it raw scores only
- Don't change group key names (`A`/`B`/`C`) — they're referenced everywhere
- Don't modify `main` branch directly — always go through `dev`
