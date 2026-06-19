#!/usr/bin/env python3
"""Generate the public index.html from tournament.json."""

import json
import os
from datetime import datetime
from html import escape as esc

from constants import GROUP_NAMES

_REPO_ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE   = os.path.join(_REPO_ROOT, "tournament.json")
OUTPUT_FILE = os.path.join(_REPO_ROOT, "index.html")

GROUP_ORDER  = ["A", "B", "C"]
GROUP_ACCENT = {"A": "green", "B": "blue", "C": "amber"}

RANK_MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


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
    for i, rnd in enumerate(rounds):
        for match in rnd:
            if match.get("score1") is None or match.get("score2") is None:
                return i
    return None  # all rounds complete


def pair_display(pair_obj):
    players = pair_obj["players"]
    team = pair_obj.get("team") or ""
    return f"{esc(players[0])} & {esc(players[1])}", esc(team)


def standings_table(standings, group_data, accent, complete=False):
    rows = ""
    accent_styles = {
        "green": ("text-green-400", "text-green-300", "bg-green-950/60 text-green-300"),
        "blue":  ("text-blue-400",  "text-blue-300",  "bg-blue-950/60 text-blue-300"),
        "amber": ("text-amber-400", "text-amber-300", "bg-amber-950/60 text-amber-300"),
    }
    a_text, a_light, a_badge = accent_styles.get(accent, accent_styles["green"])

    for s in standings:
        pair_obj = s["pair"]
        name, team = pair_display(pair_obj)
        diff = s["pts_for"] - s["pts_against"]
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        diff_color = "text-green-400" if diff > 0 else ("text-red-400" if diff < 0 else "text-slate-500")
        medal = RANK_MEDALS.get(s["rank"], "")
        rank_cell = f'<span class="text-base">{medal}</span>' if medal else f'<span class="text-slate-500 font-semibold text-sm">{s["rank"]}</span>'
        team_badge = f'<span class="text-xs {a_badge} px-1.5 py-0.5 rounded-md font-medium ml-1">{team}</span>' if team else ""

        if complete and s["rank"] == 1:
            row_bg = "bg-amber-950/30"
            name_class = "font-semibold text-white text-sm"
        else:
            row_bg = "bg-white/[0.02]" if s["rank"] % 2 == 0 else ""
            name_class = "font-semibold text-slate-200 text-sm"

        rows += f"""
        <tr class="border-b border-white/5 {row_bg} hover:bg-white/[0.04] transition-colors">
          <td class="py-2.5 px-3 text-center">{rank_cell}</td>
          <td class="py-2.5 px-3">
            <span class="{name_class}">{name}</span>{team_badge}
          </td>
          <td class="py-2.5 px-3 text-center font-bold {a_text}">{s['W']}</td>
          <td class="py-2.5 px-3 text-center text-slate-400">{s['L']}</td>
          <td class="py-2.5 px-3 text-center text-slate-400 text-sm">{s['pts_for']}</td>
          <td class="py-2.5 px-3 text-center text-slate-400 text-sm">{s['pts_against']}</td>
          <td class="py-2.5 px-3 text-center font-bold {diff_color} text-sm">{diff_str}</td>
        </tr>"""
    return rows


def match_grid(group_data, standings, accent):
    pairs = group_data["pairs"]
    rounds = group_data["rounds"]
    n = len(pairs)
    if n < 2:
        return ""

    scores = {}
    for rnd in rounds:
        for match in rnd:
            p1, p2 = match["pair1"], match["pair2"]
            s1, s2 = match.get("score1"), match.get("score2")
            scores[(p1, p2)] = (s1, s2)
            scores[(p2, p1)] = (s2, s1)

    ordered = [s["pair"] for s in standings]

    header_cells = '<th class="p-2"></th>'
    for p in ordered:
        first = esc(p["players"][0].split()[0])
        last = esc(p["players"][1].split()[0])
        header_cells += f'<th class="p-2 text-[10px] text-slate-500 text-center font-semibold min-w-[48px] leading-tight">{first}<br/>&amp;<br/>{last}</th>'

    rows = ""
    for row_pair in ordered:
        first_r = esc(row_pair["players"][0].split()[0])
        last_r = esc(row_pair["players"][1].split()[0])
        cells = f'<td class="p-2 text-xs font-semibold text-slate-400 whitespace-nowrap pr-3">{first_r} &amp; {last_r}</td>'
        for col_pair in ordered:
            if row_pair["id"] == col_pair["id"]:
                cells += '<td class="p-2 text-center text-slate-700 text-xs">—</td>'
            else:
                key = (row_pair["id"], col_pair["id"])
                if key in scores and scores[key][0] is not None:
                    s_r, s_c = scores[key]
                    won = s_r > s_c
                    bg = "bg-green-950/50 text-green-300" if won else "bg-red-950/50 text-red-400"
                    cells += f'<td class="p-1 text-center"><span class="inline-block {bg} rounded-md px-1.5 py-0.5 text-xs font-bold">{s_r}–{s_c}</span></td>'
                else:
                    cells += '<td class="p-2 text-center text-slate-700 text-[10px]">·</td>'
        rows += f"<tr class='border-b border-white/5'>{cells}</tr>"

    return f"""
    <div class="overflow-x-auto">
      <table class="text-sm w-full border-collapse">
        <thead><tr class="border-b border-white/10">{header_cells}</tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>"""


def rounds_section(group_data, current_round_idx, accent):
    pairs = {p["id"]: p for p in group_data["pairs"]}
    rounds = group_data["rounds"]
    accent_map = {
        "green": "text-green-400 bg-green-950/60 border-green-900/50",
        "blue":  "text-blue-400 bg-blue-950/60 border-blue-900/50",
        "amber": "text-amber-400 bg-amber-950/60 border-amber-900/50",
    }
    a_badge = accent_map.get(accent, accent_map["green"])
    html = ""
    for r_idx, rnd in enumerate(rounds):
        is_current = current_round_idx is not None and r_idx == current_round_idx
        all_done = all(m.get("score1") is not None and m.get("score2") is not None for m in rnd)

        if is_current:
            badge = f'<span class="{a_badge} border text-xs font-semibold px-2 py-0.5 rounded-full ml-2">Live</span>'
            hdr = f'<span class="font-bold text-slate-200">Round {r_idx + 1}</span>{badge}'
        elif all_done:
            hdr = f'<span class="font-semibold text-slate-600">Round {r_idx + 1}</span><span class="text-xs text-slate-700 ml-2">Complete</span>'
        else:
            hdr = f'<span class="font-semibold text-slate-500">Round {r_idx + 1}</span>'

        match_rows = ""
        for match in rnd:
            p1 = pairs[match["pair1"]]
            p2 = pairs[match["pair2"]]
            n1 = f"{esc(p1['players'][0])} & {esc(p1['players'][1])}"
            n2 = f"{esc(p2['players'][0])} & {esc(p2['players'][1])}"
            s1, s2 = match.get("score1"), match.get("score2")

            if s1 is not None and s2 is not None:
                if s1 > s2:
                    score_html = f'<span class="font-bold text-green-400">{s1}</span><span class="text-slate-600 mx-1">–</span><span class="text-slate-400">{s2}</span>'
                else:
                    score_html = f'<span class="text-slate-400">{s1}</span><span class="text-slate-600 mx-1">–</span><span class="font-bold text-green-400">{s2}</span>'
            else:
                score_html = '<span class="text-slate-700 text-xs">TBD</span>'

            live_bg = "bg-white/[0.03] border border-white/10" if is_current and s1 is None else "bg-transparent border border-transparent"
            match_rows += f"""
            <div class="flex items-center {live_bg} rounded-xl px-3 py-2 mb-1">
              <span class="text-slate-300 text-sm flex-1 truncate">{n1}</span>
              <span class="mx-3 text-sm font-mono shrink-0">{score_html}</span>
              <span class="text-slate-300 text-sm flex-1 text-right truncate">{n2}</span>
            </div>"""

        html += f"""
        <div class="mb-4">
          <div class="text-xs mb-2 px-1">{hdr}</div>
          {match_rows}
        </div>"""
    return html


def calc_team_standings(teams, groups_data):
    """Rank teams by combined wins (primary) then combined point diff (tiebreaker)."""
    # (group, pair_id) → team_index, built from the canonical team name on each pair
    name_to_idx = {t["name"]: i for i, t in enumerate(teams)}
    pair_to_team = {}
    for g in ["A", "B", "C"]:
        for pair in groups_data[g]["pairs"]:
            team_name = pair.get("team")
            if team_name and team_name in name_to_idx:
                pair_to_team[(g, pair["id"])] = name_to_idx[team_name]

    wins  = [0] * len(teams)
    diffs = [0] * len(teams)

    for g in ["A", "B", "C"]:
        for rnd in groups_data[g]["rounds"]:
            for match in rnd:
                s1, s2 = match.get("score1"), match.get("score2")
                if s1 is None or s2 is None:
                    continue
                t1 = pair_to_team.get((g, match["pair1"]))
                t2 = pair_to_team.get((g, match["pair2"]))
                if t1 is not None:
                    wins[t1]  += 1 if s1 > s2 else 0
                    diffs[t1] += s1 - s2
                if t2 is not None:
                    wins[t2]  += 1 if s2 > s1 else 0
                    diffs[t2] += s2 - s1

    team_stats = [{"team": t, "wins": wins[i], "diff": diffs[i]} for i, t in enumerate(teams)]
    team_stats.sort(key=lambda x: (-x["wins"], -x["diff"]))
    return team_stats


TEAM_MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


def pair_rank_lookup(groups_data):
    """Build a dict: frozenset(player_names) -> rank within their group."""
    lookup = {}
    for g in ["A", "B", "C"]:
        standings = calc_standings(groups_data[g])
        for s in standings:
            key = frozenset(s["pair"]["players"])
            lookup[key] = s["rank"]
    return lookup


def teams_grid(teams, groups_data):
    ranked = calc_team_standings(teams, groups_data)
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    p_ranks = pair_rank_lookup(groups_data)

    def pair_row(group_label, group_style, players):
        key = frozenset(players)
        rank = p_ranks.get(key)
        medal = f'<span class="ml-1">{medals[rank]}</span>' if rank in medals else ""
        return f"""
            <div class="flex items-center gap-2">
              <span class="text-[10px] font-semibold uppercase tracking-wider {group_style} px-2 py-0.5 rounded-md w-[78px] text-center shrink-0">{group_label}</span>
              <span class="text-xs text-slate-300">{esc(players[0])} &amp; {esc(players[1])}{medal}</span>
            </div>"""

    cards = ""
    for i, s in enumerate(ranked):
        t = s["team"]
        rank = i + 1
        diff = s["diff"]
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        diff_color = "text-green-400" if diff > 0 else ("text-red-400" if diff < 0 else "text-slate-500")
        cards += f"""
        <div class="bg-white/[0.03] border border-white/[0.07] rounded-2xl p-4 hover:bg-white/[0.05] transition-colors">
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold text-slate-600 w-5">#{rank}</span>
              <span class="text-base font-bold text-white">{esc(t['name'])}</span>
            </div>
            <div class="text-right">
              <span class="text-xs text-slate-500">{s['wins']}W</span>
              <span class="text-xs {diff_color} ml-2 font-semibold">{diff_str}</span>
            </div>
          </div>
          <div class="space-y-2">
            {pair_row("Advanced",     "bg-green-950/70 text-green-400 border border-green-900/40", t["A"])}
            {pair_row("Intermediate","bg-blue-950/70 text-blue-400 border border-blue-900/40",   t["B"])}
            {pair_row("Beginner",    "bg-amber-950/70 text-amber-400 border border-amber-900/40", t["C"])}
          </div>
        </div>"""
    return cards


def group_section(group_key, gd, accent):
    standings = calc_standings(gd)
    current_round = find_current_round(gd["rounds"])
    complete = current_round is None
    st_rows = standings_table(standings, gd, accent, complete=complete)
    grid = match_grid(gd, standings, accent)
    rounds_html = rounds_section(gd, current_round, accent)

    accent_styles = {
        "green": ("from-green-900/40 to-transparent", "text-green-400", "border-green-900/30"),
        "blue":  ("from-blue-900/40 to-transparent",  "text-blue-400",  "border-blue-900/30"),
        "amber": ("from-amber-900/40 to-transparent", "text-amber-400", "border-amber-900/30"),
    }
    grad, a_text, a_border = accent_styles.get(accent, accent_styles["green"])

    return f"""
      <section class="mb-10">
        <!-- Section header -->
        <div class="flex items-center gap-3 mb-4">
          <div class="h-px flex-1 bg-gradient-to-r {grad}"></div>
          <h2 class="text-sm font-bold uppercase tracking-[0.15em] {a_text}">{esc(GROUP_NAMES[group_key])}</h2>
          <div class="h-px flex-1 bg-gradient-to-l {grad}"></div>
        </div>

        <!-- Standings -->
        <div class="bg-white/[0.03] border {a_border} rounded-2xl overflow-hidden mb-3">
          <div class="px-4 py-2.5 border-b border-white/5">
            <span class="text-xs font-semibold uppercase tracking-wider text-slate-500">Standings</span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead>
                <tr class="border-b border-white/5">
                  <th class="py-2 px-3 text-center text-[10px] uppercase tracking-wider text-slate-600 font-semibold w-8">#</th>
                  <th class="py-2 px-3 text-left text-[10px] uppercase tracking-wider text-slate-600 font-semibold">Pair</th>
                  <th class="py-2 px-3 text-center text-[10px] uppercase tracking-wider text-slate-600 font-semibold">W</th>
                  <th class="py-2 px-3 text-center text-[10px] uppercase tracking-wider text-slate-600 font-semibold">L</th>
                  <th class="py-2 px-3 text-center text-[10px] uppercase tracking-wider text-slate-600 font-semibold">PF</th>
                  <th class="py-2 px-3 text-center text-[10px] uppercase tracking-wider text-slate-600 font-semibold">PA</th>
                  <th class="py-2 px-3 text-center text-[10px] uppercase tracking-wider text-slate-600 font-semibold">+/−</th>
                </tr>
              </thead>
              <tbody>{st_rows}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Results Grid -->
        <div class="bg-white/[0.03] border {a_border} rounded-2xl overflow-hidden mb-3">
          <div class="px-4 py-2.5 border-b border-white/5">
            <span class="text-xs font-semibold uppercase tracking-wider text-slate-500">Results Grid</span>
          </div>
          <div class="p-3">{grid}</div>
        </div>

        <!-- Schedule -->
        <div class="bg-white/[0.03] border {a_border} rounded-2xl overflow-hidden">
          <div class="px-4 py-2.5 border-b border-white/5">
            <span class="text-xs font-semibold uppercase tracking-wider text-slate-500">Schedule</span>
          </div>
          <div class="p-3">{rounds_html}</div>
        </div>
      </section>"""


TAB_CONFIG = [
    ("teams", "Teams"),
    ("advanced",     "Advanced"),
    ("intermediate", "Intermediate"),
    ("beginner",     "Beginner"),
]

GROUP_TAB = {"A": "advanced", "B": "intermediate", "C": "beginner"}


def generate_index():
    data = load_data()
    teams = data.get("teams", [])
    published_at = datetime.now().strftime("%H:%M · %a %d %b")

    all_complete = all(
        find_current_round(data["groups"][g]["rounds"]) is None
        for g in GROUP_ORDER if g in data["groups"]
    )

    total_matches  = sum(
        len(rnd)
        for g in GROUP_ORDER if g in data["groups"]
        for rnd in data["groups"][g]["rounds"]
    )
    played_matches = sum(
        1
        for g in GROUP_ORDER if g in data["groups"]
        for rnd in data["groups"][g]["rounds"]
        for m in rnd
        if m.get("score1") is not None and m.get("score2") is not None
    )
    pct = round(played_matches / total_matches * 100) if total_matches else 0

    auto_refresh_js = "" if all_complete else (
        "// Auto-refresh every 60s; pauses when tab is backgrounded to save battery\n"
        "    let _refreshTimer;\n"
        "    function _scheduleRefresh() {\n"
        "      clearTimeout(_refreshTimer);\n"
        "      _refreshTimer = setTimeout(() => location.reload(), 60000);\n"
        "    }\n"
        "    document.addEventListener('visibilitychange', () => {\n"
        "      if (document.hidden) { clearTimeout(_refreshTimer); }\n"
        "      else { _scheduleRefresh(); }\n"
        "    });\n"
        "    _scheduleRefresh();"
    )

    t_cards = teams_grid(teams, data["groups"])

    group_panels = ""
    for g in GROUP_ORDER:
        if g not in data["groups"]:
            continue
        tab_id = GROUP_TAB[g]
        inner = group_section(g, data["groups"][g], GROUP_ACCENT[g])
        group_panels += f'<div id="tab-{tab_id}" class="tab-panel hidden">{inner}</div>\n'

    tab_buttons = ""
    for tab_id, label in TAB_CONFIG:
        tab_buttons += f'<button data-tab="{tab_id}" class="tab-btn whitespace-nowrap px-4 py-1.5 rounded-full text-sm font-semibold text-slate-500 hover:text-slate-300 transition-colors">{label}</button>\n'

    archive_link = (
        '<div><a href="archive.html" class="text-sm text-slate-500 hover:text-green-400 transition-colors">'
        'Past tournaments →</a></div>'
        if os.path.exists(os.path.join(_REPO_ROOT, "archive.html")) else ""
    )

    if all_complete:
        hero_label = '<span class="text-xs font-semibold uppercase tracking-[0.2em] text-amber-400">Final Results</span>'
        complete_banner = (
            '<!-- Tournament complete banner -->'
            '<div class="bg-amber-950/40 border-b border-amber-900/50">'
            '<div class="max-w-2xl mx-auto px-4 py-3 flex items-center justify-center gap-3">'
            '<span class="text-lg">🏆</span>'
            '<span class="text-sm font-bold text-amber-300 uppercase tracking-[0.15em]">Tournament Complete</span>'
            '<span class="text-lg">🏆</span></div></div>'
        )
        progress_label = "Final"
        bar_color = "bg-amber-500"
    else:
        hero_label = '<span class="text-xs font-semibold uppercase tracking-[0.2em] text-green-500">Live Tournament</span>'
        complete_banner = ""
        progress_label = "Progress"
        bar_color = "bg-green-500"

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Supersmash Saturdays</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet" />
  <script src="https://cdn.tailwindcss.com"></script>
  <script>tailwind.config = {{ darkMode: 'class' }}</script>
  <style>
    * {{ font-family: 'Inter', system-ui, sans-serif; }}
    body {{ background: #080d14; color: #f1f5f9; }}
    .hero-glow {{ background: radial-gradient(ellipse 80% 50% at 50% -10%, rgba(34,197,94,0.12), transparent); }}
    .tab-btn.active {{ color: #22c55e; background: rgba(34,197,94,0.1); }}
    ::-webkit-scrollbar {{ display: none; }}
  </style>
</head>
<body class="min-h-screen">

  <!-- Hero Header -->
  <header class="relative overflow-hidden border-b border-white/5">
    <div class="hero-glow absolute inset-0 pointer-events-none"></div>
    <div class="relative max-w-2xl mx-auto px-4 pt-8 pb-6">
      <div class="flex items-start justify-between">
        <div>
          <div class="flex items-center gap-2 mb-1">
            <span class="text-2xl">🏸</span>
            {hero_label}</div>
          <h1 class="text-3xl font-black text-white tracking-tight leading-none">Supersmash<br/><span class="text-green-400">Saturdays</span></h1>
        </div>
        <div class="text-right mt-1">
          <div class="text-xs text-slate-600 mb-0.5">Last updated</div>
          <div class="text-xs font-semibold text-slate-400">{published_at}</div>
        </div>
      </div>
    </div>
  </header>

  {complete_banner}

  <!-- Sticky tab bar -->
  <nav class="sticky top-0 z-10 bg-[#080d14]/95 backdrop-blur-sm border-b border-white/5">
    <div class="max-w-2xl mx-auto px-4">
      <div class="flex gap-1 overflow-x-auto py-2">
        {tab_buttons}
      </div>
    </div>
  </nav>

  <!-- Match progress bar -->
  <div class="max-w-2xl mx-auto px-4 pt-4 pb-1">
    <div class="flex items-center justify-between mb-1.5">
      <span class="text-[10px] font-semibold uppercase tracking-wider text-slate-600">{progress_label}</span>
      <span class="text-[10px] font-semibold text-slate-500">{played_matches} / {total_matches} matches</span>
    </div>
    <div class="h-1 rounded-full bg-white/5 overflow-hidden">
      <div class="h-full rounded-full {bar_color} transition-all" style="width:{pct}%"></div>
    </div>
  </div>

  <main class="max-w-2xl mx-auto px-4 py-4">

    <!-- Teams tab -->
    <div id="tab-teams" class="tab-panel">
      <section class="mb-10">
        <div class="flex items-center gap-3 mb-4">
          <div class="h-px flex-1 bg-gradient-to-r from-slate-800 to-transparent"></div>
          <h2 class="text-xs font-bold uppercase tracking-[0.15em] text-slate-500">Cross-Skill Teams</h2>
          <div class="h-px flex-1 bg-gradient-to-l from-slate-800 to-transparent"></div>
        </div>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {t_cards}
        </div>
      </section>
    </div>

    <!-- Group tabs -->
    {group_panels}

  </main>

  <footer class="text-center pb-10 pt-4 space-y-2">
    {archive_link}
    <div class="text-xs text-slate-700">Supersmash Saturdays &bull; Powered by rallies and good vibes</div>
  </footer>

  <script>
    function showTab(id) {{
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === id));
      const panel = document.getElementById('tab-' + id);
      if (panel) panel.classList.remove('hidden');
      history.replaceState(null, '', id === 'teams' ? location.pathname : '#' + id);
    }}

    const initialTab = location.hash.replace('#', '') || 'teams';
    showTab(initialTab);

    document.querySelectorAll('.tab-btn').forEach(btn => {{
      btn.addEventListener('click', () => showTab(btn.dataset.tab));
    }});

    {auto_refresh_js}
  </script>
</body>
</html>"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    generate_index()
    print(f"Generated {OUTPUT_FILE}")
