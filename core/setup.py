#!/usr/bin/env python3
"""Setup pipeline for Supersmash Saturdays tournament."""

import json
import os
import shutil
import subprocess
import sys
from itertools import combinations

_REPO_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE    = os.path.join(_REPO_ROOT, "tournament.json")
PLAYERS_FILE = os.path.join(_REPO_ROOT, "players.txt")

from constants import GROUP_NAMES, SKILL_ORDER, VALID_GENDERS



def strip_invisible(s):
    """Strip zero-width and other invisible Unicode characters."""
    invisible = {'​', '‌', '‍', '⁠', '﻿', ' ', ' ', ' '}
    return ''.join(c for c in s if c not in invisible).strip()


def parse_players(filepath=None):
    if filepath is None:
        filepath = PLAYERS_FILE
    players = []
    skipped = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        for lineno, raw in enumerate(f, 1):
            line = strip_invisible(raw)
            if not line or line.startswith("#"):
                continue
            parts = [strip_invisible(p) for p in line.split(":")]
            if len(parts) < 2:
                print(f"  [line {lineno}] SKIP — no colon separator: {repr(raw.rstrip())}")
                skipped.append(lineno)
                continue

            # Support: Name : Rating  OR  Name : Rating : M/F
            last = parts[-1].upper()
            if last in VALID_GENDERS and len(parts) >= 3:
                gender = last
                rating = parts[-2]
                name = strip_invisible(":".join(parts[:-2]))
            else:
                gender = None
                rating = parts[-1]
                name = strip_invisible(":".join(parts[:-1]))

            if not name:
                print(f"  [line {lineno}] SKIP — empty name after stripping: {repr(raw.rstrip())}")
                skipped.append(lineno)
                continue
            if rating not in SKILL_ORDER:
                print(f"  [line {lineno}] SKIP — unknown rating '{rating}' for '{name}' (expected one of {', '.join(SKILL_ORDER)})")
                skipped.append(lineno)
                continue
            player = {"name": name, "rating": rating}
            if gender:
                player["gender"] = gender
            players.append(player)
            gender_str = f", {gender}" if gender else ""
            print(f"  [line {lineno}] OK   — {name} ({rating}{gender_str})")

    if skipped:
        print(f"\n  WARNING: {len(skipped)} line(s) skipped (lines {skipped})")
    print(f"\n  Loaded {len(players)} valid players.")
    return players


def assign_groups(players):
    """Sort all players by skill rating, then split evenly into Advanced/Intermediate/Beginner."""
    sorted_all = sorted(players, key=lambda x: SKILL_ORDER.index(x["rating"]))
    n = len(sorted_all)
    size = n // 3
    remainder = n % 3

    if remainder != 0:
        print(f"\n  NOTE: {n} players can't split evenly into 3 groups.")
        print(f"  The bottom {remainder} player(s) will be dropped for balance:")
        for p in sorted_all[n - remainder:]:
            print(f"    - {p['name']} ({p['rating']})")
        sorted_all = sorted_all[:n - remainder]
        size = len(sorted_all) // 3
        print(f"  Proceeding with {len(sorted_all)} players ({size} per group).")

    groups = {
        "A": sorted_all[:size],
        "B": sorted_all[size:size * 2],
        "C": sorted_all[size * 2:],
    }
    print(f"\n  Group sizes: Advanced={len(groups['A'])}, Intermediate={len(groups['B'])}, Beginner={len(groups['C'])}")
    return groups


def display_groups(groups):
    for g, label in GROUP_NAMES.items():
        print(f"\n  [{label}]")
        for i, p in enumerate(groups[g], 1):
            print(f"    {i:2}. {p['name']} ({p['rating']})")


def _group_size_problems(groups):
    """Return a list of human-readable problems with group sizes."""
    problems = []
    for g, label in GROUP_NAMES.items():
        n = len(groups[g])
        if n < 2:
            problems.append(f"  {label} has {n} player(s) — need at least 2")
        elif n % 2 != 0:
            problems.append(f"  {label} has {n} players (odd) — add or remove 1 so everyone can be paired")
    sizes = [len(groups[g]) for g in ["A", "B", "C"]]
    if len(set(sizes)) > 1:
        size_str = ", ".join(f"{GROUP_NAMES[g]}={len(groups[g])}" for g in ["A", "B", "C"])
        problems.append(
            f"  Unequal group sizes ({size_str})"
            f" — move players until all groups have the same count"
            f" (equal groups = equal pairs = balanced teams)"
        )
    return problems


def edit_groups(groups):
    while True:
        problems = _group_size_problems(groups)
        if problems:
            print("\n  ⚠ Fix before continuing:")
            for p in problems:
                print(p)
        print("\nOptions: [c]ontinue, [m]ove player, [r]emove player")
        choice = input("  > ").strip().lower()
        if choice == "c":
            if problems:
                print("  Cannot continue until group sizes are balanced.")
                continue
            break
        elif choice == "m":
            name = input("  Player name to move: ").strip()
            dest = input("  Move to group (A=Advanced, B=Intermediate, C=Beginner): ").strip().upper()
            if dest not in groups:
                print("  Invalid group. Enter A, B, or C.")
                continue
            found = False
            for g in groups:
                for p in groups[g]:
                    if p["name"].lower() == name.lower():
                        if g == dest:
                            print(f"  {name} is already in that group.")
                            found = True
                            break
                        groups[g].remove(p)
                        groups[dest].append(p)
                        print(f"  Moved {name} from {GROUP_NAMES[g]} to {GROUP_NAMES[dest]}.")
                        found = True
                        break
                if found:
                    break
            if not found:
                print(f"  Player '{name}' not found.")
            else:
                display_groups(groups)
        elif choice == "r":
            name = input("  Player name to remove: ").strip()
            found = False
            for g in groups:
                for p in groups[g]:
                    if p["name"].lower() == name.lower():
                        groups[g].remove(p)
                        found = True
                        break
                if found:
                    break
            if not found:
                print("  Player not found.")
            else:
                display_groups(groups)
        else:
            print("  Unknown option.")


def write_players_txt(groups, filepath=None):
    if filepath is None:
        filepath = PLAYERS_FILE
    lines = []
    for g, label in GROUP_NAMES.items():
        lines.append(f"# {label}")
        for p in groups[g]:
            if p.get("gender"):
                lines.append(f"{p['name']} : {p['rating']} : {p['gender']}")
            else:
                lines.append(f"{p['name']} : {p['rating']}")
        lines.append("")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")
    print(f"  Updated {filepath} with confirmed groups.")


def make_pairs(group_players):
    """
    Gender-aware pairing: maximise mixed (M+F) pairs, then top-to-bottom
    skill balance within each pool. Players without a gender field are treated
    as unspecified and fall back to the same-gender/remainder pool.
    """
    players = list(group_players)
    if len(players) % 2 != 0:
        print(f"  Warning: odd number of players ({len(players)}), last player gets a bye.")
        players = players[:-1]

    males   = [p for p in players if p.get("gender") == "M"]
    females = [p for p in players if p.get("gender") == "F"]
    unspec  = [p for p in players if p.get("gender") not in ("M", "F")]

    has_gender = len(males) + len(females) > 0

    pairs = []

    if has_gender:
        # Mixed pairs: top male with bottom female (skill-balanced across genders)
        n_mixed = min(len(males), len(females))
        for i in range(n_mixed):
            pairs.append([males[i]["name"], females[len(females) - 1 - i]["name"]])

        # Remaining players after mixed pairing
        remaining = males[n_mixed:] + females[n_mixed:] + unspec
        n_mixed_made = n_mixed
    else:
        remaining = players
        n_mixed_made = 0

    # Top-to-bottom pairing on the remainder
    n = len(remaining)
    for i in range(n // 2):
        pairs.append([remaining[i]["name"], remaining[n - 1 - i]["name"]])

    if has_gender:
        n_same = len(pairs) - n_mixed_made
        print(f"  Pairing: {n_mixed_made} mixed pair(s), {n_same} same-gender/unspecified pair(s)")

    return pairs


def display_pairs(all_pairs, groups=None):
    for g, label in GROUP_NAMES.items():
        print(f"\n  [{label} Pairs]")
        # Build a name->player lookup for gender display if groups provided
        player_map = {}
        if groups:
            for p in groups[g]:
                player_map[p["name"]] = p
        for i, pair in enumerate(all_pairs[g], 1):
            def fmt(name):
                p = player_map.get(name)
                if p and p.get("gender"):
                    return f"{name} ({p['rating']}, {p['gender']})"
                elif p:
                    return f"{name} ({p['rating']})"
                return name
            print(f"    Pair {i}: {fmt(pair[0])} & {fmt(pair[1])}")


def edit_pairs(all_pairs, groups):
    while True:
        print("\nOptions: [c]ontinue, [s]wap players between pairs")
        choice = input("  > ").strip().lower()
        if choice == "c":
            break
        elif choice == "s":
            g = input("  Group (A/B/C): ").strip().upper()
            if g not in all_pairs:
                print("  Invalid group.")
                continue
            try:
                i1 = int(input("  First pair number: ")) - 1
                p1_slot = int(input("  Player slot in first pair (1 or 2): ")) - 1
                i2 = int(input("  Second pair number: ")) - 1
                p2_slot = int(input("  Player slot in second pair (1 or 2): ")) - 1
                all_pairs[g][i1][p1_slot], all_pairs[g][i2][p2_slot] = (
                    all_pairs[g][i2][p2_slot],
                    all_pairs[g][i1][p1_slot],
                )
                display_pairs(all_pairs)
            except (ValueError, IndexError):
                print("  Invalid input.")
        else:
            print("  Unknown option.")


def make_teams(all_pairs):
    """Assign one pair from each group into cross-skill teams."""
    a_pairs = all_pairs["A"]
    b_pairs = all_pairs["B"]
    c_pairs = all_pairs["C"]
    n_teams = min(len(a_pairs), len(b_pairs), len(c_pairs))
    teams = []
    for i in range(n_teams):
        teams.append({
            "name": f"Team {i + 1}",
            "A": list(a_pairs[i]),
            "B": list(b_pairs[i]),
            "C": list(c_pairs[i]),
        })
    return teams


def display_teams(teams):
    for t in teams:
        print(f"\n  [{t['name']}]")
        print(f"    Advanced:     {t['A'][0]} & {t['A'][1]}")
        print(f"    Intermediate: {t['B'][0]} & {t['B'][1]}")
        print(f"    Beginner:     {t['C'][0]} & {t['C'][1]}")


def edit_teams(teams):
    while True:
        print("\nOptions: [c]ontinue, [n]ame a team, [s]wap pairs between teams")
        choice = input("  > ").strip().lower()
        if choice == "c":
            break
        elif choice == "n":
            try:
                idx = int(input("  Team number: ")) - 1
                new_name = input("  New name: ").strip()
                if 0 <= idx < len(teams):
                    teams[idx]["name"] = new_name
                    display_teams(teams)
                else:
                    print("  Invalid team number.")
            except ValueError:
                print("  Invalid input.")
        elif choice == "s":
            try:
                g = input("  Group to swap (A=Advanced, B=Intermediate, C=Beginner): ").strip().upper()
                if g not in ("A", "B", "C"):
                    print("  Invalid group. Enter A, B, or C.")
                    continue
                t1 = int(input("  First team number: ")) - 1
                t2 = int(input("  Second team number: ")) - 1
                if not (0 <= t1 < len(teams) and 0 <= t2 < len(teams)):
                    print("  Invalid team number.")
                    continue
                if t1 == t2:
                    print("  Same team — nothing to swap.")
                    continue
                teams[t1][g], teams[t2][g] = teams[t2][g], teams[t1][g]
                print(f"  Swapped {GROUP_NAMES[g]} pairs between {teams[t1]['name']} and {teams[t2]['name']}.")
                display_teams(teams)
            except ValueError:
                print("  Invalid input.")
        else:
            print("  Unknown option.")


def make_matchups(pairs):
    """Generate flat list of all round-robin matchups (no round structure)."""
    matchups = []
    pair_ids = list(range(len(pairs)))
    for i, (p1, p2) in enumerate(combinations(pair_ids, 2)):
        matchups.append({
            "id": i,
            "pair1": p1,
            "pair2": p2,
            "score1": None,
            "score2": None,
            "status": "pending",
            "court": None,
            "seq": None,
        })
    return matchups


def get_pair_team(pair_players, teams, group):
    for t in teams:
        if set(t[group]) == set(pair_players):
            return t["name"]
    return None


DEFAULT_COURTS = [1, 3, 5, 7, 9, 11, 13, 15]


def build_tournament_data(groups, all_pairs, teams, courts=None):
    data = {
        "courts": courts or DEFAULT_COURTS,
        "next_seq": 1,
        "groups": {},
        "teams": teams,
    }
    for g, label in GROUP_NAMES.items():
        pairs = all_pairs[g]
        pair_objects = []
        for i, p in enumerate(pairs):
            team_name = get_pair_team(p, teams, g)
            pair_objects.append({
                "id": i,
                "players": p,
                "team": team_name,
            })
        matches = make_matchups(pairs)
        data["groups"][g] = {
            "label": label,
            "pairs": pair_objects,
            "matches": matches,
        }
    return data


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)
    backup_dir = os.path.join(_REPO_ROOT, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    bak = os.path.join(backup_dir, "tournament.session.bak")
    shutil.copy2(DATA_FILE, bak)
    print(f"\n  Saved tournament state to {DATA_FILE}")
    print(f"  Backup written to         {bak}")


def git_push_initial():
    print("\n  Pushing initial index.html to GitHub Pages...")
    try:
        # Import here to reuse the generator
        from generate_index import generate_index
        generate_index()

        cmds = [
            ["git", "add", "index.html"],
            ["git", "commit", "-m", "Initial tournament setup"],
            ["git", "push", "origin", "main"],
        ]
        for cmd in cmds:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=_REPO_ROOT)
            if result.returncode != 0:
                print(f"  Git error: {result.stderr.strip()}")
                return False
        print("  Pushed to GitHub Pages successfully.")
        return True
    except Exception as e:
        print(f"  Push failed: {e}")
        return False


def main():
    print("=" * 50)
    print("  SUPERSMASH SATURDAYS — Tournament Setup")
    print("=" * 50)

    # Step 1: Load players
    if not os.path.exists(PLAYERS_FILE):
        print("  players.txt not found. Create it first.")
        sys.exit(1)

    players = parse_players()
    print(f"\n  Loaded {len(players)} players from players.txt")
    groups = assign_groups(players)

    print("\n--- SKILL GROUPS ---")
    display_groups(groups)
    print("\nReview the skill groups above.")
    edit_groups(groups)
    write_players_txt(groups)

    # Step 2: Generate pairs
    all_pairs = {}
    for g in ["A", "B", "C"]:
        all_pairs[g] = make_pairs(groups[g])

    print("\n--- PAIRS ---")
    display_pairs(all_pairs, groups)
    print("\nReview the pairs above.")
    edit_pairs(all_pairs, groups)

    # Step 3: Assign teams
    teams = make_teams(all_pairs)

    print("\n--- CROSS-SKILL TEAMS ---")
    display_teams(teams)
    print("\nReview the cross-skill teams above.")
    edit_teams(teams)

    # Step 4: Configure courts
    print("\n--- COURTS ---")
    default_str = ",".join(str(c) for c in DEFAULT_COURTS)
    courts_input = input(f"  Court numbers (comma-separated, default {default_str}): ").strip()
    if courts_input:
        courts = [int(c.strip()) for c in courts_input.split(",") if c.strip().isdigit()]
        courts.sort()
    else:
        courts = list(DEFAULT_COURTS)
    print(f"  Using {len(courts)} courts: {courts}")

    # Step 5: Build and save tournament data
    data = build_tournament_data(groups, all_pairs, teams, courts)
    save_data(data)

    # Step 5: Generate and push initial index.html
    print("\n--- GENERATING INDEX.HTML ---")
    try:
        from generate_index import generate_index
        generate_index()
        print("  index.html generated.")
    except Exception as e:
        print(f"  Failed to generate index.html: {e}")
        sys.exit(1)

    print("\n--- GIT PUSH ---")
    push = input("  Push to GitHub Pages now? [y/N]: ").strip().lower()
    if push == "y":
        git_push_initial()

    print("\n  Setup complete! Run the admin server with:")
    print("    python app.py")
    print("\n  Players can view standings at:")
    print("    https://sasiru98.github.io/supersmash-saturdays")


if __name__ == "__main__":
    main()
