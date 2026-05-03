#!/usr/bin/env python3
"""Validate players.txt and sync tournament.json if groups have changed."""

import json
import os

_REPO_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_ORDER   = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-"]
GROUP_NAMES   = {"A": "Advanced", "B": "Intermediate", "C": "Beginner"}
VALID_GENDERS = {"M", "F"}
DATA_FILE    = os.path.join(_REPO_ROOT, "tournament.json")
PLAYERS_FILE = os.path.join(_REPO_ROOT, "players.txt")

# Zero-width and invisible Unicode characters (by code point — no copy-paste ambiguity)
INVISIBLE = {
    "​",  # zero-width space
    "‌",  # zero-width non-joiner
    "‍",  # zero-width joiner
    "⁠",  # word joiner
    "﻿",  # BOM / zero-width no-break space
    " ",  # non-breaking space
    " ",  # thin space
    " ",  # narrow no-break space
    "­",  # soft hyphen
}

SECTION_MAP = {
    "advanced":    "A",
    "intermediate":"B",
    "beginner":    "C",
}


def clean(s):
    return "".join(c for c in s if c not in INVISIBLE).strip()


def parse_players_sectioned(filepath=PLAYERS_FILE):
    """
    Parse a sectioned players.txt.
    Section headers: # Advanced / # Intermediate / # Beginner
    Returns (groups_dict, errors_list).
    """
    errors  = []
    groups  = {"A": [], "B": [], "C": []}
    current_group = None
    sections_seen = set()

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()

    for lineno, raw in enumerate(lines, 1):
        line = clean(raw)
        if not line:
            continue

        # ── Section header ─────────────────────────────────────
        if line.startswith("#"):
            # Strip all leading # and whitespace, lowercase, compare
            label = line.lstrip("#").strip().lower()
            matched_key = next(
                (k for k in SECTION_MAP if label == k or label.startswith(k + " ")),
                None
            )
            if matched_key:
                current_group = SECTION_MAP[matched_key]
                sections_seen.add(current_group)
            # Ignore unrecognised comment lines
            continue

        # ── Player line ─────────────────────────────────────────
        if ":" not in line:
            errors.append(f"  line {lineno}: No colon separator — {repr(raw.rstrip())}")
            continue

        parts = [clean(p) for p in line.split(":")]

        # Support: Name : Rating  OR  Name : Rating : M/F
        last = parts[-1].upper()
        if last in VALID_GENDERS and len(parts) >= 3:
            gender = last
            rating = parts[-2]
            name   = clean(":".join(parts[:-2]))
        else:
            gender = None
            rating = parts[-1]
            name   = clean(":".join(parts[:-1]))

        if not name:
            errors.append(f"  line {lineno}: Empty name — {repr(raw.rstrip())}")
            continue

        if rating not in SKILL_ORDER:
            errors.append(
                f"  line {lineno}: Unknown rating '{rating}' for '{name}' "
                f"— valid values: {', '.join(SKILL_ORDER)}"
            )
            continue

        if current_group is None:
            errors.append(
                f"  line {lineno}: Player '{name}' appears before any section header "
                f"(add '# Advanced', '# Intermediate', or '# Beginner' above them)"
            )
            continue

        player = {"name": name, "rating": rating}
        if gender:
            player["gender"] = gender
        groups[current_group].append(player)

    # ── Cross-checks ─────────────────────────────────────────────
    for g in ["A", "B", "C"]:
        if g not in sections_seen:
            errors.append(f"  Missing section header: # {GROUP_NAMES[g]}")

    all_names = [p["name"] for g in groups.values() for p in g]
    seen = set()
    for name in all_names:
        key = name.lower()
        if key in seen:
            errors.append(f"  Duplicate player name: '{name}'")
        seen.add(key)

    for g, label in GROUP_NAMES.items():
        n = len(groups[g])
        if n < 2:
            errors.append(f"  {label} group has {n} player(s) — need at least 2 to make a pair")

    return groups, errors


def groups_match_tournament(groups, data):
    for g in ["A", "B", "C"]:
        txt  = sorted(p["name"] for p in groups[g])
        json_names = sorted(
            player
            for pair in data["groups"][g]["pairs"]
            for player in pair["players"]
        )
        if txt != json_names:
            return False
    return True


def diff_groups(groups, data):
    lines = []
    for g, label in GROUP_NAMES.items():
        txt       = set(p["name"] for p in groups[g])
        in_json   = set(
            player
            for pair in data["groups"][g]["pairs"]
            for player in pair["players"]
        )
        added   = txt - in_json
        removed = in_json - txt
        if added:
            lines.append(f"  {label}: added   {', '.join(sorted(added))}")
        if removed:
            lines.append(f"  {label}: removed {', '.join(sorted(removed))}")
    return lines


def regenerate_from_groups(groups):
    from setup import make_pairs, make_teams, build_tournament_data, save_data
    all_pairs = {g: make_pairs(groups[g]) for g in ["A", "B", "C"]}
    teams     = make_teams(all_pairs)
    data      = build_tournament_data(groups, all_pairs, teams)
    save_data(data)
    return data


def validate_and_sync():
    """
    Called on app.py startup.
    - Format errors in players.txt → print them, prompt to rerun setup.py
    - Groups changed vs tournament.json → show diff, prompt to regenerate
    - All good → proceed
    Returns (ok: bool, message: str)
    """
    if not os.path.exists(PLAYERS_FILE):
        return False, f"  {PLAYERS_FILE} not found. Run setup.py first."

    groups, errors = parse_players_sectioned(PLAYERS_FILE)

    if errors:
        print(f"\n  players.txt has {len(errors)} error(s):\n")
        for e in errors:
            print(e)
        print("\n  Fix the errors above and restart, or run setup.py to regenerate players.txt.")
        return False, ""

    total = sum(len(v) for v in groups.values())
    sizes = ", ".join(f"{GROUP_NAMES[g]}={len(groups[g])}" for g in ["A", "B", "C"])

    if not os.path.exists(DATA_FILE):
        return False, f"  {DATA_FILE} not found. Run setup.py first."

    with open(DATA_FILE) as f:
        data = json.load(f)

    if groups_match_tournament(groups, data):
        return True, f"  players.txt OK — {total} players ({sizes})"

    # Groups have changed
    diff = diff_groups(groups, data)
    print(f"\n  players.txt differs from tournament.json:")
    for line in diff:
        print(line)

    print(
        "\n  Regenerate pairings and schedule from players.txt?"
        "\n  WARNING: This will reset all entered scores."
        "\n  [y] regenerate   [n] abort   [s] rerun setup.py"
    )
    print("  > ", end="", flush=True)
    answer = input().strip().lower()

    if answer == "y":
        regenerate_from_groups(groups)
        from generate_index import generate_index
        generate_index()
        return True, f"  Regenerated — {total} players ({sizes})"
    elif answer == "s":
        print("\n  Run:  python setup.py\n")
        return False, ""
    else:
        return False, "  Aborted. Edit players.txt or run setup.py."
