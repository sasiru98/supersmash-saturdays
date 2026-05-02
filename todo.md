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
