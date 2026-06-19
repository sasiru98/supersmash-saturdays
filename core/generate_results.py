#!/usr/bin/env python3
"""Generate finalised results pages and the tournament archive."""

import json
import os
import sys
from datetime import datetime
from html import escape as esc

_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
if _CORE_DIR not in sys.path:
    sys.path.insert(0, _CORE_DIR)

from generate_index import (
    GROUP_ORDER, GROUP_ACCENT, GROUP_TAB, TAB_CONFIG,
    load_data, group_section, teams_grid,
    calc_standings, calc_team_standings,
)

_REPO_ROOT       = os.path.dirname(_CORE_DIR)
PAST_RESULTS_DIR = os.path.join(_REPO_ROOT, "past_results")
ARCHIVE_INDEX    = os.path.join(PAST_RESULTS_DIR, "index.json")
ARCHIVE_HTML     = os.path.join(_REPO_ROOT, "archive.html")


def _extract_winners(data):
    """Return 1st-place pair name per group and overall team name."""
    w = {}
    for g in GROUP_ORDER:
        if g not in data["groups"]:
            continue
        standings = calc_standings(data["groups"][g])
        if standings:
            players = standings[0]["pair"]["players"]
            w[g] = f"{players[0]} & {players[1]}"
    team_stats = calc_team_standings(data.get("teams", []), data["groups"])
    if team_stats:
        w["team"] = team_stats[0]["team"]["name"]
    return w


def _results_page_html(data, date_label):
    teams    = data.get("teams", [])
    t_cards  = teams_grid(teams, data["groups"])

    group_panels = ""
    for g in GROUP_ORDER:
        if g not in data["groups"]:
            continue
        tab_id = GROUP_TAB[g]
        inner  = group_section(g, data["groups"][g], GROUP_ACCENT[g])
        group_panels += f'<div id="tab-{tab_id}" class="tab-panel hidden">{inner}</div>\n'

    tab_buttons = ""
    for tab_id, label in TAB_CONFIG:
        tab_buttons += (
            f'<button data-tab="{tab_id}" class="tab-btn whitespace-nowrap px-4 py-1.5 '
            f'rounded-full text-sm font-semibold text-slate-500 hover:text-slate-300 '
            f'transition-colors">{label}</button>\n'
        )

    total = sum(
        len(data["groups"][g]["matches"])
        for g in GROUP_ORDER if g in data["groups"]
    )

    return f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Supersmash Saturdays · {esc(date_label)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet" />
  <script src="https://cdn.tailwindcss.com"></script>
  <script>tailwind.config = {{ darkMode: 'class' }}</script>
  <style>
    * {{ font-family: 'Inter', system-ui, sans-serif; }}
    body {{ background: #080d14; color: #f1f5f9; }}
    .hero-glow {{ background: radial-gradient(ellipse 80% 50% at 50% -10%, rgba(245,158,11,0.08), transparent); }}
    .tab-btn.active {{ color: #22c55e; background: rgba(34,197,94,0.1); }}
    ::-webkit-scrollbar {{ display: none; }}
  </style>
</head>
<body class="min-h-screen">

  <header class="relative overflow-hidden border-b border-white/5">
    <div class="hero-glow absolute inset-0 pointer-events-none"></div>
    <div class="relative max-w-2xl mx-auto px-4 pt-8 pb-6">
      <div class="flex items-start justify-between">
        <div>
          <div class="flex items-center gap-2 mb-1">
            <span class="text-2xl">🏸</span>
            <span class="text-xs font-semibold uppercase tracking-[0.2em] text-amber-400">Final Results</span>
          </div>
          <h1 class="text-3xl font-black text-white tracking-tight leading-none">Supersmash<br/><span class="text-green-400">Saturdays</span></h1>
        </div>
        <div class="text-right mt-1">
          <div class="text-xs text-slate-600 mb-0.5">Played on</div>
          <div class="text-xs font-semibold text-slate-400">{esc(date_label)}</div>
        </div>
      </div>
    </div>
  </header>

  <div class="bg-amber-950/40 border-b border-amber-900/50">
    <div class="max-w-2xl mx-auto px-4 py-3 flex items-center justify-center gap-3">
      <span class="text-lg">🏆</span>
      <span class="text-sm font-bold text-amber-300 uppercase tracking-[0.15em]">Tournament Complete</span>
      <span class="text-lg">🏆</span>
    </div>
  </div>

  <nav class="sticky top-0 z-10 bg-[#080d14]/95 backdrop-blur-sm border-b border-white/5">
    <div class="max-w-2xl mx-auto px-4">
      <div class="flex gap-1 overflow-x-auto py-2">
        {tab_buttons}
      </div>
    </div>
  </nav>

  <div class="max-w-2xl mx-auto px-4 pt-4 pb-1">
    <div class="flex items-center justify-between mb-1.5">
      <span class="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Final</span>
      <span class="text-[10px] font-semibold text-slate-500">{total} / {total} matches</span>
    </div>
    <div class="h-1 rounded-full bg-white/5 overflow-hidden">
      <div class="h-full rounded-full bg-amber-500" style="width:100%"></div>
    </div>
  </div>

  <main class="max-w-2xl mx-auto px-4 py-4">
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
    {group_panels}
  </main>

  <footer class="text-center pb-10 pt-4 space-y-2">
    <div><a href="../archive.html" class="text-sm text-slate-500 hover:text-green-400 transition-colors">← All tournaments</a></div>
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
  </script>
</body>
</html>"""


def _archive_page_html(entries):
    cards = ""
    for e in sorted(entries, key=lambda x: x["date"], reverse=True):
        sun_w   = esc(e.get("sun_winner",   "—"))
        moon_w  = esc(e.get("moon_winner",  "—"))
        stars_w = esc(e.get("stars_winner", "—"))
        team_w  = esc(e.get("team_winner",  "—"))
        cards += f"""
        <a href="{esc(e['file'])}" class="block bg-white/[0.03] border border-white/[0.07] rounded-2xl p-4 hover:bg-white/[0.05] transition-colors">
          <div class="flex items-center justify-between mb-3">
            <span class="text-base font-bold text-white">{esc(e['label'])}</span>
            <span class="text-xs text-slate-500">View →</span>
          </div>
          <div class="space-y-1.5 text-xs">
            <div class="flex items-center gap-2">
              <span class="text-green-400 w-16 shrink-0">☀️ Sun</span>
              <span class="text-slate-300">🥇 {sun_w}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-blue-400 w-16 shrink-0">🌙 Moon</span>
              <span class="text-slate-300">🥇 {moon_w}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-amber-400 w-16 shrink-0">⭐ Stars</span>
              <span class="text-slate-300">🥇 {stars_w}</span>
            </div>
            <div class="flex items-center gap-2 pt-1.5 border-t border-white/5">
              <span class="text-slate-500 w-16 shrink-0">Team</span>
              <span class="text-slate-300 font-semibold">🏆 {team_w}</span>
            </div>
          </div>
        </a>"""

    if not cards:
        cards = '<p class="text-center text-slate-600 text-sm py-10">No past tournaments yet.</p>'

    return f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Supersmash Saturdays · Archive</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet" />
  <script src="https://cdn.tailwindcss.com"></script>
  <script>tailwind.config = {{ darkMode: 'class' }}</script>
  <style>
    * {{ font-family: 'Inter', system-ui, sans-serif; }}
    body {{ background: #080d14; color: #f1f5f9; }}
    .hero-glow {{ background: radial-gradient(ellipse 80% 50% at 50% -10%, rgba(34,197,94,0.08), transparent); }}
    ::-webkit-scrollbar {{ display: none; }}
  </style>
</head>
<body class="min-h-screen">

  <header class="relative overflow-hidden border-b border-white/5">
    <div class="hero-glow absolute inset-0 pointer-events-none"></div>
    <div class="relative max-w-2xl mx-auto px-4 pt-8 pb-6">
      <div class="flex items-center gap-2 mb-1">
        <span class="text-2xl">🏸</span>
        <span class="text-xs font-semibold uppercase tracking-[0.2em] text-green-500">History</span>
      </div>
      <h1 class="text-3xl font-black text-white tracking-tight leading-none">Tournament<br/><span class="text-green-400">Archive</span></h1>
    </div>
  </header>

  <main class="max-w-2xl mx-auto px-4 py-6">
    <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {cards}
    </div>
  </main>

  <footer class="text-center pb-10 pt-4 space-y-2">
    <div><a href="index.html" class="text-sm text-slate-500 hover:text-green-400 transition-colors">← Live tournament</a></div>
    <div class="text-xs text-slate-700">Supersmash Saturdays &bull; Powered by rallies and good vibes</div>
  </footer>

</body>
</html>"""


def generate_results_page(date_str, data):
    """Write past_results/YYYY-MM-DD.html and return its absolute path."""
    os.makedirs(PAST_RESULTS_DIR, exist_ok=True)
    out_path   = os.path.join(PAST_RESULTS_DIR, f"{date_str}.html")
    date_label = datetime.strptime(date_str, "%Y-%m-%d").strftime("%a %d %b %Y")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(_results_page_html(data, date_label))
    return out_path


def update_archive_index(date_str, data):
    """Add or replace this date's entry in past_results/index.json."""
    os.makedirs(PAST_RESULTS_DIR, exist_ok=True)
    entries = []
    if os.path.exists(ARCHIVE_INDEX):
        with open(ARCHIVE_INDEX, encoding="utf-8") as f:
            entries = json.load(f)
    entries = [e for e in entries if e["date"] != date_str]
    w = _extract_winners(data)
    entries.append({
        "date":         date_str,
        "label":        datetime.strptime(date_str, "%Y-%m-%d").strftime("%a %d %b %Y"),
        "file":         f"past_results/{date_str}.html",
        "sun_winner":   w.get("A",    ""),
        "moon_winner":  w.get("B",    ""),
        "stars_winner": w.get("C",    ""),
        "team_winner":  w.get("team", ""),
    })
    with open(ARCHIVE_INDEX, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


def generate_archive_page():
    """Regenerate archive.html from past_results/index.json."""
    entries = []
    if os.path.exists(ARCHIVE_INDEX):
        with open(ARCHIVE_INDEX, encoding="utf-8") as f:
            entries = json.load(f)
    with open(ARCHIVE_HTML, "w", encoding="utf-8") as f:
        f.write(_archive_page_html(entries))


def finalise(date_str=None):
    """Generate results page, update archive index, regenerate archive.html.

    Returns (date_str, results_path, archive_html_path, archive_index_path).
    """
    data = load_data()
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    results_path = generate_results_page(date_str, data)
    update_archive_index(date_str, data)
    generate_archive_page()
    return date_str, results_path, ARCHIVE_HTML, ARCHIVE_INDEX


if __name__ == "__main__":
    date_str, results, archive, _ = finalise()
    print(f"Results : {results}")
    print(f"Archive : {archive}")
