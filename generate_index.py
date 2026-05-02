#!/usr/bin/env python3
"""Generate the public index.html from tournament.json."""

import json
import os

DATA_FILE = "tournament.json"
OUTPUT_FILE = "index.html"

GROUP_ORDER = ["A", "B", "C"]
GROUP_LABELS = {"A": "Advanced", "B": "Intermediate", "C": "Beginner"}


def load_data():
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(f"{DATA_FILE} not found. Run setup.py first.")
    with open(DATA_FILE) as f:
        return json.load(f)


def calc_standings(group_data):
    pairs = group_data["pairs"]
    rounds = group_data["rounds"]
    stats = {p["id"]: {"pair": p, "W": 0, "L": 0, "pts_for": 0, "pts_against": 0} for p in pairs}

    for rnd in rounds:
        for match in rnd:
            s1 = match.get("score1")
            s2 = match.get("score2")
            if s1 is None or s2 is None:
                continue
            p1, p2 = match["pair1"], match["pair2"]
            stats[p1]["pts_for"] += s1
            stats[p1]["pts_against"] += s2
            stats[p2]["pts_for"] += s2
            stats[p2]["pts_against"] += s1
            if s1 > s2:
                stats[p1]["W"] += 1
                stats[p2]["L"] += 1
            elif s2 > s1:
                stats[p2]["W"] += 1
                stats[p1]["L"] += 1

    ranked = sorted(
        stats.values(),
        key=lambda x: (
            -x["W"],
            -(x["pts_for"] - x["pts_against"]),
            -x["pts_for"],
        ),
    )
    for i, s in enumerate(ranked):
        s["rank"] = i + 1
    return ranked


def find_current_round(rounds):
    """Return the index of the first round with any unplayed matches."""
    for i, rnd in enumerate(rounds):
        for match in rnd:
            if match.get("score1") is None or match.get("score2") is None:
                return i
    return len(rounds) - 1


def pair_display(pair_obj):
    players = pair_obj["players"]
    team = pair_obj.get("team") or ""
    name = f"{players[0]} & {players[1]}"
    return name, team


def standings_table(standings, group_data):
    pairs = {p["id"]: p for p in group_data["pairs"]}
    rows = ""
    for s in standings:
        pair_obj = s["pair"]
        name, team = pair_display(pair_obj)
        diff = s["pts_for"] - s["pts_against"]
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        team_badge = f'<span class="text-xs text-green-400 ml-1">({team})</span>' if team else ""
        rows += f"""
        <tr class="border-b border-gray-700 hover:bg-gray-700/40 transition-colors">
          <td class="py-2 px-2 text-center font-bold text-green-400">{s['rank']}</td>
          <td class="py-2 px-3">
            <span class="font-medium">{name}</span>{team_badge}
          </td>
          <td class="py-2 px-2 text-center">{s['W']}</td>
          <td class="py-2 px-2 text-center">{s['L']}</td>
          <td class="py-2 px-2 text-center">{s['pts_for']}</td>
          <td class="py-2 px-2 text-center">{s['pts_against']}</td>
          <td class="py-2 px-2 text-center font-semibold {('text-green-400' if diff >= 0 else 'text-red-400')}">{diff_str}</td>
        </tr>"""
    return rows


def match_grid(group_data, standings):
    pairs = group_data["pairs"]
    rounds = group_data["rounds"]
    n = len(pairs)
    if n < 2:
        return ""

    # Build a score lookup: (pair_id_a, pair_id_b) -> (score_a, score_b)
    scores = {}
    for rnd in rounds:
        for match in rnd:
            p1, p2 = match["pair1"], match["pair2"]
            s1, s2 = match.get("score1"), match.get("score2")
            scores[(p1, p2)] = (s1, s2)
            scores[(p2, p1)] = (s2, s1)

    # Order pairs by rank
    ordered = [s["pair"] for s in standings]

    header_cells = '<th class="p-2 text-xs text-gray-400"></th>'
    for p in ordered:
        short = p["players"][0].split()[0]
        header_cells += f'<th class="p-2 text-xs text-gray-400 text-center min-w-[44px]">{short}<br/>&amp;<br/>{p["players"][1].split()[0]}</th>'

    rows = ""
    for row_pair in ordered:
        row_name = f"{row_pair['players'][0].split()[0]} & {row_pair['players'][1].split()[0]}"
        cells = f'<td class="p-2 text-xs font-medium text-gray-300 whitespace-nowrap">{row_name}</td>'
        for col_pair in ordered:
            if row_pair["id"] == col_pair["id"]:
                cells += '<td class="p-2 text-center bg-gray-700/30 text-gray-600">—</td>'
            else:
                key = (row_pair["id"], col_pair["id"])
                if key in scores and scores[key][0] is not None:
                    s_row, s_col = scores[key]
                    color = "text-green-400" if s_row > s_col else "text-red-400"
                    cells += f'<td class="p-2 text-center text-xs {color} font-semibold">{s_row}–{s_col}</td>'
                else:
                    cells += '<td class="p-2 text-center text-gray-600 text-xs">vs</td>'
        rows += f"<tr class='border-b border-gray-700/50'>{cells}</tr>"

    return f"""
    <div class="overflow-x-auto mt-4">
      <table class="text-sm w-full border-collapse">
        <thead><tr class="border-b border-gray-600">{header_cells}</tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>"""


def rounds_section(group_data, current_round_idx):
    pairs = {p["id"]: p for p in group_data["pairs"]}
    rounds = group_data["rounds"]
    html = ""
    for r_idx, rnd in enumerate(rounds):
        is_current = r_idx == current_round_idx
        label = f"Round {r_idx + 1}"
        if is_current:
            label += ' <span class="text-xs bg-green-600 text-white px-2 py-0.5 rounded-full ml-1">Current</span>'
        header_class = "text-green-300 font-semibold" if is_current else "text-gray-400"
        match_rows = ""
        for match in rnd:
            p1 = pairs[match["pair1"]]
            p2 = pairs[match["pair2"]]
            n1 = f"{p1['players'][0]} & {p1['players'][1]}"
            n2 = f"{p2['players'][0]} & {p2['players'][1]}"
            s1, s2 = match.get("score1"), match.get("score2")
            if s1 is not None and s2 is not None:
                score_display = f'<span class="text-green-400 font-bold">{s1}–{s2}</span>'
            else:
                score_display = '<span class="text-gray-500 text-xs">TBD</span>'

            bg = "bg-green-900/20 border border-green-800/40" if is_current and s1 is None else "bg-gray-800/40"
            match_rows += f"""
            <div class="flex items-center justify-between {bg} rounded px-3 py-2 mb-1 text-sm">
              <span class="text-gray-200 flex-1">{n1}</span>
              <span class="mx-2 text-gray-500">vs</span>
              <span class="text-gray-200 flex-1 text-right">{n2}</span>
              <span class="ml-3 min-w-[50px] text-right">{score_display}</span>
            </div>"""
        html += f"""
        <div class="mb-3">
          <h4 class="{header_class} text-sm mb-2">{label}</h4>
          {match_rows}
        </div>"""
    return html


def generate_index():
    data = load_data()
    teams = data.get("teams", [])

    # Build teams section HTML
    teams_html = ""
    for t in teams:
        a = t["A"]
        b = t["B"]
        c = t["C"]
        teams_html += f"""
        <div class="bg-gray-800 rounded-xl p-4 border border-green-900/40">
          <h3 class="text-green-400 font-bold text-lg mb-3">{t['name']}</h3>
          <div class="space-y-1 text-sm">
            <div class="flex items-center gap-2">
              <span class="text-xs bg-green-700/40 text-green-300 px-2 py-0.5 rounded">Advanced</span>
              <span class="text-gray-200">{a[0]} &amp; {a[1]}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-xs bg-blue-700/40 text-blue-300 px-2 py-0.5 rounded">Intermediate</span>
              <span class="text-gray-200">{b[0]} &amp; {b[1]}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-xs bg-yellow-700/40 text-yellow-300 px-2 py-0.5 rounded">Beginner</span>
              <span class="text-gray-200">{c[0]} &amp; {c[1]}</span>
            </div>
          </div>
        </div>"""

    # Build group sections
    group_sections = ""
    for g in GROUP_ORDER:
        if g not in data["groups"]:
            continue
        gd = data["groups"][g]
        label = GROUP_LABELS[g]
        standings = calc_standings(gd)
        current_round = find_current_round(gd["rounds"])
        st_rows = standings_table(standings, gd)
        grid = match_grid(gd, standings)
        rounds_html = rounds_section(gd, current_round)

        color_map = {"A": "green", "B": "blue", "C": "yellow"}
        c = color_map[g]

        group_sections += f"""
      <!-- {label} Section -->
      <section class="mb-10">
        <h2 class="text-2xl font-bold text-{c}-400 mb-4 flex items-center gap-2">
          <span class="text-3xl">🏸</span> {label}
        </h2>

        <!-- Standings -->
        <div class="bg-gray-800 rounded-xl overflow-hidden mb-4 border border-gray-700">
          <div class="px-4 py-3 bg-gray-700/50 border-b border-gray-600">
            <h3 class="font-semibold text-gray-200">Standings</h3>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="text-gray-400 text-xs border-b border-gray-700 bg-gray-800/80">
                  <th class="py-2 px-2 text-center">#</th>
                  <th class="py-2 px-3 text-left">Pair</th>
                  <th class="py-2 px-2 text-center">W</th>
                  <th class="py-2 px-2 text-center">L</th>
                  <th class="py-2 px-2 text-center">PF</th>
                  <th class="py-2 px-2 text-center">PA</th>
                  <th class="py-2 px-2 text-center">+/-</th>
                </tr>
              </thead>
              <tbody>{st_rows}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Match Results Grid -->
        <div class="bg-gray-800 rounded-xl overflow-hidden mb-4 border border-gray-700">
          <div class="px-4 py-3 bg-gray-700/50 border-b border-gray-600">
            <h3 class="font-semibold text-gray-200">Results Grid</h3>
          </div>
          <div class="p-3">
            {grid}
          </div>
        </div>

        <!-- Schedule -->
        <div class="bg-gray-800 rounded-xl overflow-hidden border border-gray-700">
          <div class="px-4 py-3 bg-gray-700/50 border-b border-gray-600">
            <h3 class="font-semibold text-gray-200">Schedule</h3>
          </div>
          <div class="p-4">
            {rounds_html}
          </div>
        </div>
      </section>"""

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Supersmash Saturdays</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {{
      darkMode: 'class',
      theme: {{
        extend: {{
          colors: {{
            green: {{
              400: '#4ade80',
              500: '#22c55e',
              600: '#16a34a',
              700: '#15803d',
              800: '#166534',
              900: '#14532d',
            }}
          }}
        }}
      }}
    }}
  </script>
  <style>
    body {{ background-color: #111827; color: #f3f4f6; font-family: system-ui, -apple-system, sans-serif; }}
    .shuttle {{ display: inline-block; }}
  </style>
</head>
<body class="min-h-screen bg-gray-900 text-gray-100">

  <!-- Header -->
  <header class="bg-gray-800 border-b border-green-900/50 sticky top-0 z-10 shadow-lg">
    <div class="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
      <div>
        <h1 class="text-xl font-black text-green-400 tracking-tight">🏸 Supersmash Saturdays</h1>
        <p class="text-xs text-gray-400">Live Tournament Standings</p>
      </div>
      <div class="text-right text-xs text-gray-500">
        <div id="last-updated">—</div>
      </div>
    </div>
  </header>

  <main class="max-w-2xl mx-auto px-4 py-6">

    <!-- Teams Section -->
    <section class="mb-8">
      <h2 class="text-xl font-bold text-gray-200 mb-3 flex items-center gap-2">
        <span>🤝</span> Cross-Skill Teams
      </h2>
      <div class="grid gap-3">
        {teams_html}
      </div>
    </section>

    <!-- Group Sections -->
    {group_sections}

  </main>

  <footer class="text-center text-xs text-gray-600 pb-8 pt-4">
    Supersmash Saturdays &bull; Powered by rallies and good vibes
  </footer>

  <script>
    const now = new Date();
    document.getElementById('last-updated').textContent = 'Updated ' + now.toLocaleTimeString([], {{hour: '2-digit', minute: '2-digit'}});
  </script>
</body>
</html>"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    generate_index()
    print(f"Generated {OUTPUT_FILE}")
