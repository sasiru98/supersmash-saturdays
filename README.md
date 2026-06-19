# 🏸 Supersmash Saturdays

Round-robin tournament manager for Supersmash Saturdays badminton events. Players are split into three equal skill groups and paired within their group. Cross-skill teams link one pair from each group for social and mentorship purposes.

**Repo:** https://github.com/sasiru98/supersmash-saturdays
**Live standings:** https://sasiru98.github.io/supersmash-saturdays

> QR code for players → `https://sasiru98.github.io/supersmash-saturdays`
> *(Generate a QR code at qr.io or similar and print it for the venue)*

---

## How it works

- Players are sorted by skill rating and split evenly into three equal groups
- Public-facing group names are **Group A / Group B / Group C**
- Admin panel uses **Advanced / Intermediate / Beginner** internally
- Pairs are formed within each group with mixed-gender pairs prioritised; falls back to top-to-bottom (1st with last) when gender isn't specified or the split is uneven
- Each group runs its own full round-robin (every pair plays every other pair once)
- Cross-skill teams assign one pair from each group together — for social mixing and mentorship
- Standings recalculated from raw scores every time you publish (wins → point diff → points scored)

---

## Setup

### 1. Install dependencies

```bash
pip install flask
```

### 2. Edit players.txt

Each line: `Name : Skill Rating` or `Name : Skill Rating : Gender`

Ratings: `A+`, `A`, `A-`, `B+`, `B`, `B-`, `C+`, `C`, `C-`

Gender: `M` or `F` (optional — omit if unknown or unspecified)

Order and grouping don't matter — setup sorts and splits automatically:

```
Marcus Chen : A+ : M
Emma Johansson : B+ : F
Kevin Tran : C+
```

Adding gender lets setup prioritise mixed pairs within each group.

### 3. Run setup

```bash
python core/setup.py
```

The setup pipeline will:
- Load and validate all players
- Sort by skill rating and split into three equal groups
- Show the groups — confirm or move players between groups
- Generate pairs (mixed-gender prioritised where gender is provided)
- Assign cross-skill teams (one pair per group), optionally name them
- Generate the full round-robin schedule
- Write `tournament.json` and `index.html`
- Rewrite `players.txt` with confirmed group sections (for future edits)

### 4. (Optional) Move players between groups

After setup, `players.txt` is organised into sections:

```
# Advanced
Deshawn : A+ : M
Nonce : B- : F
Inson : A-
...

# Intermediate
John : B+
...

# Beginner
Hari : B
...
```

To move a player, cut their line and paste it under a different section header. When you run `python app.py` next, the validator will detect the change, show you the diff, and ask if you want to regenerate pairings.

> ⚠️ Regenerating resets all entered scores.

### 5. Start the admin server

```bash
python core/app.py
```

On startup it validates `players.txt` against `tournament.json` and reports any issues before the server starts. The admin panel runs on your local network (port 5000):

```
http://<your-ip>:5000
```

The server prints the address on startup.

---

## During the Tournament

- **Admin tablet** → `http://<local-ip>:5000`
  Enter scores as matches finish. Scores auto-save on blur or Enter.

- **Player phones** → https://sasiru98.github.io/supersmash-saturdays
  Live standings, results grid, and schedule. Tabbed layout: **Teams / Group A / Group B / Group C**. Sharing a link with `#group-a` / `#group-b` / `#group-c` in the URL opens that tab directly.

- **Publish button** → Recalculates all standings, commits to `dev`, merges to `main`, pushes to GitHub Pages.

- **Team names** → Editable anytime in the Teams tab of the admin panel.

---

## Validation errors

If `players.txt` has issues, `app.py` will refuse to start and show exactly what's wrong:

| Error | Fix |
|---|---|
| No colon separator | Format must be `Name : Rating` or `Name : Rating : M/F` |
| Unknown rating | Use one of: `A+`, `A`, `A-`, `B+`, `B`, `B-`, `C+`, `C`, `C-` |
| Missing section header | Add `# Advanced`, `# Intermediate`, `# Beginner` |
| Duplicate name | Each player must appear exactly once |
| Groups changed | Choose to regenerate (resets scores) or rerun `setup.py` |

---

## Git workflow

- All development and score updates committed to `dev`
- On every publish, `dev` is merged into `main` and both are pushed
- `main` is always the clean public-facing branch (GitHub Pages serves from here)

---

## When does tournament.json update?

| Action | Effect |
|---|---|
| `python setup.py` | Full rebuild — pairings, schedule, teams *(resets scores)* |
| `python app.py` when groups differ | Pairings and schedule regenerated *(resets scores)* |
| Entering a score in admin | That match only |
| Saving a team name in admin | Team name only |
| Publish | Derives `index.html` from scores — does not change `tournament.json` |

---

## Project structure

```
core/
  setup.py           # One-time tournament setup pipeline
  app.py             # Flask admin server (local only)
  validate.py        # Validates players.txt and syncs tournament.json on startup
  generate_index.py  # Generates public index.html from tournament.json
templates/
  admin.html         # Admin score entry panel
players.txt          # Player list with skill ratings (editable after setup)
index.html           # Public standings page (GitHub Pages)
tournament.json      # Raw tournament state — gitignored, local only
```
