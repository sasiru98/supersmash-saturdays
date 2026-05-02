#!/usr/bin/env python3
"""Setup pipeline for Supersmash Saturdays tournament."""

import json
import os
import subprocess
import sys
from itertools import combinations

SKILL_ORDER = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-"]
GROUP_NAMES = {"A": "Advanced", "B": "Intermediate", "C": "Beginner"}
DATA_FILE = "tournament.json"


def rating_to_group(rating):
    return rating[0]


def parse_players(filepath="players.txt"):
    players = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(":")
            if len(parts) != 2:
                print(f"  Skipping malformed line: {line}")
                continue
            name = parts[0].strip()
            rating = parts[1].strip()
            if rating not in SKILL_ORDER:
                print(f"  Unknown rating '{rating}' for {name}, skipping.")
                continue
            players.append({"name": name, "rating": rating, "group": rating_to_group(rating)})
    return players


def sort_players(players):
    groups = {"A": [], "B": [], "C": []}
    for p in players:
        groups[p["group"]].append(p)
    for g in groups:
        groups[g].sort(key=lambda x: SKILL_ORDER.index(x["rating"]))
    return groups


def display_groups(groups):
    for g, label in GROUP_NAMES.items():
        print(f"\n  [{label}]")
        for i, p in enumerate(groups[g], 1):
            print(f"    {i:2}. {p['name']} ({p['rating']})")


def edit_groups(groups):
    while True:
        print("\nOptions: [c]ontinue, [m]ove player, [r]emove player")
        choice = input("  > ").strip().lower()
        if choice == "c":
            break
        elif choice == "m":
            name = input("  Player name to move: ").strip()
            new_rating = input("  New rating (A+/A/A-/B+/B/B-/C+/C/C-): ").strip()
            if new_rating not in SKILL_ORDER:
                print("  Invalid rating.")
                continue
            found = False
            for g in groups:
                for p in groups[g]:
                    if p["name"].lower() == name.lower():
                        groups[g].remove(p)
                        p["rating"] = new_rating
                        p["group"] = rating_to_group(new_rating)
                        new_g = p["group"]
                        groups[new_g].append(p)
                        groups[new_g].sort(key=lambda x: SKILL_ORDER.index(x["rating"]))
                        found = True
                        break
                if found:
                    break
            if not found:
                print("  Player not found.")
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


def make_pairs(group_players):
    """Top-to-bottom pairing: 1st with last, 2nd with second-last, etc."""
    players = list(group_players)
    if len(players) % 2 != 0:
        print(f"  Warning: odd number of players ({len(players)}), last player gets a bye.")
        players = players[:-1]
    pairs = []
    n = len(players)
    for i in range(n // 2):
        pairs.append([players[i]["name"], players[n - 1 - i]["name"]])
    return pairs


def display_pairs(all_pairs):
    for g, label in GROUP_NAMES.items():
        print(f"\n  [{label} Pairs]")
        for i, pair in enumerate(all_pairs[g], 1):
            print(f"    Pair {i}: {pair[0]} & {pair[1]}")


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
        print("\nOptions: [c]ontinue, [n]ame a team")
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
        else:
            print("  Unknown option.")


def make_schedule(pairs):
    """Generate full round-robin schedule for a list of pairs."""
    pair_ids = list(range(len(pairs)))
    matchups = list(combinations(pair_ids, 2))
    rounds = []
    scheduled = set()
    pair_busy = set()

    round_matches = []
    remaining = list(matchups)

    while remaining:
        round_matches = []
        pair_busy = set()
        next_remaining = []
        for m in remaining:
            if m[0] not in pair_busy and m[1] not in pair_busy:
                round_matches.append({"pair1": m[0], "pair2": m[1], "score1": None, "score2": None})
                pair_busy.add(m[0])
                pair_busy.add(m[1])
            else:
                next_remaining.append(m)
        rounds.append(round_matches)
        remaining = next_remaining

    return rounds


def get_pair_team(pair_players, teams, group):
    for t in teams:
        if set(t[group]) == set(pair_players):
            return t["name"]
    return None


def build_tournament_data(groups, all_pairs, teams):
    data = {
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
        schedule = make_schedule(pairs)
        data["groups"][g] = {
            "label": label,
            "pairs": pair_objects,
            "rounds": schedule,
        }
    return data


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\n  Saved tournament state to {DATA_FILE}")


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
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
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
    if not os.path.exists("players.txt"):
        print("  players.txt not found. Create it first.")
        sys.exit(1)

    players = parse_players("players.txt")
    print(f"\n  Loaded {len(players)} players from players.txt")
    groups = sort_players(players)

    print("\n--- SKILL GROUPS ---")
    display_groups(groups)
    print("\nReview the skill groups above.")
    edit_groups(groups)

    # Step 2: Generate pairs
    all_pairs = {}
    for g in ["A", "B", "C"]:
        all_pairs[g] = make_pairs(groups[g])

    print("\n--- PAIRS ---")
    display_pairs(all_pairs)
    print("\nReview the pairs above.")
    edit_pairs(all_pairs, groups)

    # Step 3: Assign teams
    teams = make_teams(all_pairs)

    print("\n--- CROSS-SKILL TEAMS ---")
    display_teams(teams)
    print("\nReview the cross-skill teams above.")
    edit_teams(teams)

    # Step 4: Build and save tournament data
    data = build_tournament_data(groups, all_pairs, teams)
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
