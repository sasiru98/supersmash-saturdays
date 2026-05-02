# 🏸 Supersmash Saturdays

Round-robin tournament manager for Supersmash Saturdays badminton events.
Players are grouped by skill (Advanced / Intermediate / Beginner) and paired within their group.
Cross-skill teams link one pair from each group for social and mentorship purposes.

**Repo:** https://github.com/sasiru98/supersmash-saturdays  
**Live standings:** https://sasiru98.github.io/supersmash-saturdays

> QR code for players → `https://sasiru98.github.io/supersmash-saturdays`
> _(Generate a QR code at qr.io or similar and print it for the venue)_

---

## Setup

### 1. Install dependencies

```bash
pip install flask
```

### 2. Edit players.txt

Each line: `Name : Skill Rating`

Ratings: `A+`, `A`, `A-`, `B+`, `B`, `B-`, `C+`, `C`, `C-`

```
Marcus Chen : A+
Emma Johansson : B+
Kevin Tran : C+
```

### 3. Run setup

```bash
python setup.py
```

The setup script will:
- Sort players into skill groups (Advanced/Intermediate/Beginner)
- Prompt you to review and adjust groupings
- Generate pairs using top-to-bottom pairing (1st with last, etc.)
- Assign cross-skill teams (one pair per skill group)
- Let you name the teams
- Generate the full round-robin schedule
- Create `tournament.json` and the initial `index.html`
- Optionally push to GitHub Pages

### 4. Start the admin server

```bash
python app.py
```

The admin panel runs on your local network (port 5000). Open it on your tablet:

```
http://<your-ip>:5000
```

The server will print the address on startup.

---

## During the Tournament

- **Admin tablet** → `http://<local-ip>:5000`  
  Enter scores as matches finish. All scores are auto-saved on blur/Enter.

- **Player phones** → https://sasiru98.github.io/supersmash-saturdays  
  Live standings, results grid, and schedule.

- **Publish button** → Recalculates all standings, commits to `dev`, merges to `main`, pushes to GitHub Pages.

- **Team names** → Editable at any time in the Teams tab of the admin panel.

---

## Git Workflow

- Development and score updates are committed to `dev`
- On every publish, `dev` is merged into `main` and both are pushed
- `main` is always the clean public-facing branch (GitHub Pages)

---

## Project Structure

```
players.txt          # Player list with skill ratings
setup.py             # One-time tournament setup pipeline
generate_index.py    # Generates public index.html from tournament.json
app.py               # Flask admin server
templates/
  admin.html         # Admin score entry panel
index.html           # Public standings page (GitHub Pages)
tournament.json      # All raw tournament state (gitignored)
```
