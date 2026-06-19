#!/usr/bin/env python3
"""Flask admin server for Supersmash Saturdays."""

import json
import os
import re
import shutil
import subprocess
import threading
from datetime import datetime

from flask import Flask, jsonify, render_template, request

from generate_index import generate_index

_REPO_ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE        = os.path.join(_REPO_ROOT, "tournament.json")
_BACKUP_DIR      = os.path.join(_REPO_ROOT, "backups")
BAK_SESSION      = os.path.join(_BACKUP_DIR, "tournament.session.bak")
BAK_PRE_REGEN    = os.path.join(_BACKUP_DIR, "tournament.pre-regen.bak")
_data_lock       = threading.Lock()
app = Flask(__name__, template_folder=os.path.join(_REPO_ROOT, "templates"))
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True


def get_pages_url():
    """Derive the GitHub Pages URL from the git remote, e.g. https://user.github.io/repo."""
    try:
        r = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, cwd=_REPO_ROOT
        )
        if r.returncode != 0:
            return None
        remote = r.stdout.strip()
        m = (re.match(r'https://github\.com/([^/]+)/([^/\n]+?)(?:\.git)?$', remote) or
             re.match(r'git@github\.com:([^/]+)/([^\n]+?)(?:\.git)?$', remote))
        if m:
            return f"https://{m.group(1)}.github.io/{m.group(2)}"
        return None
    except Exception:
        return None


def load_data():
    if not os.path.exists(DATA_FILE):
        return None
    with open(DATA_FILE) as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def git_publish():
    """Regenerate index.html, commit to dev, merge to main, push both.

    Returns (errors, steps) where steps is a list of completed step labels.
    Aborts on the first git failure to avoid operating on the wrong branch.
    """
    generate_index()
    errors = []
    steps = ["Generated index.html"]

    def run(cmd, label):
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=_REPO_ROOT)
        if r.returncode != 0:
            stderr = r.stderr.strip()
            errors.append(f"{label}: {stderr}" if stderr else label)
            return False
        steps.append(label)
        return True

    if not run(["git", "checkout", "dev"], "Checked out dev"):
        return errors, steps
    run(["git", "add", "index.html"], "Staged files")
    if not run(["git", "commit", "-m", "Update scores and standings"], "Committed to dev"):
        # Nothing to commit is not fatal — treat as already up to date
        if any("nothing to commit" in e for e in errors):
            errors.clear()
            steps.append("Nothing new to commit")
        else:
            return errors, steps
    if not run(["git", "push", "origin", "dev"], "Pushed dev"):
        return errors, steps
    if not run(["git", "checkout", "main"], "Checked out main"):
        run(["git", "checkout", "dev"], "Returned to dev")
        return errors, steps
    if not run(["git", "merge", "dev", "--no-edit"], "Merged dev → main"):
        run(["git", "checkout", "dev"], "Returned to dev")
        return errors, steps
    if not run(["git", "push", "origin", "main"], "Pushed main → GitHub Pages"):
        run(["git", "checkout", "dev"], "Returned to dev")
        return errors, steps
    run(["git", "checkout", "dev"], "Returned to dev")

    return errors, steps


@app.route("/")
def admin():
    data = load_data()
    if data is None:
        return "tournament.json not found. Run setup.py first.", 500
    return render_template("admin.html", data=data, pages_url=get_pages_url())


@app.route("/api/data")
def api_data():
    data = load_data()
    if data is None:
        return jsonify({"error": "No data"}), 500
    return jsonify(data)


def _find_match(data, group, match_id):
    """Find a match by group key and match ID. Returns (match, error_response)."""
    if group not in data["groups"]:
        return None, (jsonify({"error": f"Unknown group '{group}'"}), 400)
    for m in data["groups"][group]["matches"]:
        if m["id"] == match_id:
            return m, None
    return None, (jsonify({"error": f"Match {match_id} not found in group {group}"}), 404)


def _parse_score(val):
    if val is None or val == "":
        return None
    n = int(val)
    if not (0 <= n <= 99):
        raise ValueError(f"Score {n} out of range (0-99)")
    return n


@app.route("/api/score", methods=["POST"])
def api_score():
    body = request.json
    group = body.get("group")
    match_id = body.get("match_id")
    score1 = body.get("score1")
    score2 = body.get("score2")

    with _data_lock:
        data = load_data()
        if data is None:
            return jsonify({"error": "No data"}), 500
        try:
            match, err = _find_match(data, group, match_id)
            if err:
                return err
            if match["status"] not in ("in_progress", "scored"):
                return jsonify({"error": f"Cannot score a {match['status']} match"}), 400
            match["score1"] = _parse_score(score1)
            match["score2"] = _parse_score(score2)
            if match["score1"] is not None and match["score2"] is not None:
                match["status"] = "scored"
            save_data(data)
            return jsonify({"ok": True})
        except (KeyError, TypeError, ValueError) as e:
            return jsonify({"error": str(e)}), 400


@app.route("/api/courts", methods=["POST"])
def api_courts():
    body = request.json
    courts = body.get("courts")
    if not isinstance(courts, list) or not all(isinstance(c, int) for c in courts):
        return jsonify({"error": "courts must be a list of integers"}), 400

    with _data_lock:
        data = load_data()
        if data is None:
            return jsonify({"error": "No data"}), 500
        data["courts"] = sorted(courts)
        save_data(data)
        return jsonify({"ok": True, "courts": data["courts"]})


@app.route("/api/assign", methods=["POST"])
def api_assign():
    body = request.json
    group = body.get("group")
    match_id = body.get("match_id")
    court = body.get("court")

    with _data_lock:
        data = load_data()
        if data is None:
            return jsonify({"error": "No data"}), 500

        if court not in data.get("courts", []):
            return jsonify({"error": f"Court {court} is not configured"}), 400

        match, err = _find_match(data, group, match_id)
        if err:
            return err
        if match["status"] != "pending":
            return jsonify({"error": f"Match is {match['status']}, not pending"}), 400

        # Check court is free
        for gd in data["groups"].values():
            for m in gd["matches"]:
                if m["court"] == court and m["status"] in ("in_progress", "scored"):
                    return jsonify({"error": f"Court {court} is occupied"}), 400

        # Check neither pair is currently playing
        for m in data["groups"][group]["matches"]:
            if m["status"] in ("in_progress", "scored"):
                if m["pair1"] in (match["pair1"], match["pair2"]) or \
                   m["pair2"] in (match["pair1"], match["pair2"]):
                    return jsonify({"error": "One of the pairs is already on court"}), 400

        match["status"] = "in_progress"
        match["court"] = court
        save_data(data)
        return jsonify({"ok": True})


@app.route("/api/unassign", methods=["POST"])
def api_unassign():
    body = request.json
    group = body.get("group")
    match_id = body.get("match_id")

    with _data_lock:
        data = load_data()
        if data is None:
            return jsonify({"error": "No data"}), 500

        match, err = _find_match(data, group, match_id)
        if err:
            return err
        if match["status"] not in ("in_progress", "scored"):
            return jsonify({"error": f"Match is {match['status']}, cannot unassign"}), 400

        match["status"] = "pending"
        match["court"] = None
        match["score1"] = None
        match["score2"] = None
        save_data(data)
        return jsonify({"ok": True})


@app.route("/api/finalise_match", methods=["POST"])
def api_finalise_match():
    body = request.json
    group = body.get("group")
    match_id = body.get("match_id")

    with _data_lock:
        data = load_data()
        if data is None:
            return jsonify({"error": "No data"}), 500

        match, err = _find_match(data, group, match_id)
        if err:
            return err
        if match["status"] != "scored":
            return jsonify({"error": "Match must be scored before finalising"}), 400
        if match["score1"] is None or match["score2"] is None:
            return jsonify({"error": "Both scores must be entered"}), 400

        match["status"] = "finalised"
        match["seq"] = data.get("next_seq", 1)
        data["next_seq"] = match["seq"] + 1
        match["court"] = None
        save_data(data)
        return jsonify({"ok": True})


@app.route("/api/queue")
def api_queue():
    data = load_data()
    if data is None:
        return jsonify({"error": "No data"}), 500

    queue = []
    for g, gd in data["groups"].items():
        pairs = {p["id"]: p for p in gd["pairs"]}

        # Per-pair stats: matches played and last sequence number
        pair_played = {}
        pair_last_seq = {}
        busy_pairs = set()
        for m in gd["matches"]:
            for pid in (m["pair1"], m["pair2"]):
                pair_played.setdefault(pid, 0)
                pair_last_seq.setdefault(pid, 0)
            if m["status"] in ("finalised", "scored", "in_progress"):
                pair_played[m["pair1"]] = pair_played.get(m["pair1"], 0) + 1
                pair_played[m["pair2"]] = pair_played.get(m["pair2"], 0) + 1
            if m["status"] == "finalised" and m["seq"]:
                pair_last_seq[m["pair1"]] = max(pair_last_seq.get(m["pair1"], 0), m["seq"])
                pair_last_seq[m["pair2"]] = max(pair_last_seq.get(m["pair2"], 0), m["seq"])
            if m["status"] in ("in_progress", "scored"):
                busy_pairs.add(m["pair1"])
                busy_pairs.add(m["pair2"])

        for m in gd["matches"]:
            if m["status"] != "pending":
                continue
            if m["pair1"] in busy_pairs or m["pair2"] in busy_pairs:
                continue
            p1_played = pair_played.get(m["pair1"], 0)
            p2_played = pair_played.get(m["pair2"], 0)
            p1_seq = pair_last_seq.get(m["pair1"], 0)
            p2_seq = pair_last_seq.get(m["pair2"], 0)
            queue.append({
                "group": g,
                "match_id": m["id"],
                "pair1": pairs[m["pair1"]],
                "pair2": pairs[m["pair2"]],
                "priority_played": max(p1_played, p2_played),
                "priority_seq": max(p1_seq, p2_seq),
            })

    queue.sort(key=lambda x: (x["priority_played"], x["priority_seq"]))
    return jsonify({"queue": queue})


@app.route("/api/team_name", methods=["POST"])
def api_team_name():
    body = request.json
    team_idx = body.get("index")
    name = body.get("name", "").strip()
    if not name:
        return jsonify({"error": "Name cannot be empty"}), 400

    with _data_lock:
        data = load_data()
        if data is None:
            return jsonify({"error": "No data"}), 500
        try:
            old_name = data["teams"][team_idx]["name"]
            data["teams"][team_idx]["name"] = name

            # Update team references in groups
            for g in data["groups"].values():
                for pair in g["pairs"]:
                    if pair.get("team") == old_name:
                        pair["team"] = name

            save_data(data)
            return jsonify({"ok": True})
        except (IndexError, KeyError, TypeError) as e:
            return jsonify({"error": str(e)}), 400


def _backup_info(path):
    if not os.path.exists(path):
        return {"exists": False}
    mtime = os.path.getmtime(path)
    label = datetime.fromtimestamp(mtime).strftime("%a %d %b · %H:%M")
    return {"exists": True, "time": label}


@app.route("/api/backups")
def api_backups():
    return jsonify({
        "session":   _backup_info(BAK_SESSION),
        "pre_regen": _backup_info(BAK_PRE_REGEN),
    })


@app.route("/api/restore", methods=["POST"])
def api_restore():
    body  = request.json or {}
    which = body.get("backup")
    src   = BAK_SESSION if which == "session" else BAK_PRE_REGEN if which == "pre_regen" else None
    if src is None:
        return jsonify({"error": "Invalid backup type"}), 400
    if not os.path.exists(src):
        return jsonify({"error": "Backup file not found"}), 404
    with _data_lock:
        shutil.copy2(src, DATA_FILE)
    return jsonify({"ok": True})


def git_finalise(date_str=None):
    """Freeze results, update archive, commit to dev, merge to main, push both.

    Returns (errors, steps, date_str).  Aborts on first git failure.
    """
    from generate_results import finalise as _finalise

    generate_index()
    errors = []
    steps = ["Generated index.html"]

    date_str, results_path, archive_html, archive_index = _finalise(date_str)
    steps.append(f"Generated results page for {date_str}")
    steps.append("Updated tournament archive")

    # Normalise to forward-slash paths for git
    def rel(p):
        return os.path.relpath(p, _REPO_ROOT).replace("\\", "/")

    def run(cmd, label):
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=_REPO_ROOT)
        if r.returncode != 0:
            stderr = r.stderr.strip()
            errors.append(f"{label}: {stderr}" if stderr else label)
            return False
        steps.append(label)
        return True

    if not run(["git", "checkout", "dev"], "Checked out dev"):
        return errors, steps, date_str
    run(
        ["git", "add", "index.html", rel(archive_html), rel(results_path), rel(archive_index)],
        "Staged files",
    )
    if not run(["git", "commit", "-m", f"Finalise {date_str} tournament results"], "Committed to dev"):
        if any("nothing to commit" in e for e in errors):
            errors.clear()
            steps.append("Nothing new to commit")
        else:
            return errors, steps, date_str
    if not run(["git", "push", "origin", "dev"], "Pushed dev"):
        return errors, steps, date_str
    if not run(["git", "checkout", "main"], "Checked out main"):
        run(["git", "checkout", "dev"], "Returned to dev")
        return errors, steps, date_str
    if not run(["git", "merge", "dev", "--no-edit"], "Merged dev → main"):
        run(["git", "checkout", "dev"], "Returned to dev")
        return errors, steps, date_str
    if not run(["git", "push", "origin", "main"], "Pushed main → GitHub Pages"):
        run(["git", "checkout", "dev"], "Returned to dev")
        return errors, steps, date_str
    run(["git", "checkout", "dev"], "Returned to dev")
    return errors, steps, date_str


@app.route("/api/publish", methods=["POST"])
def api_publish():
    data = load_data()
    if data is None:
        return jsonify({"error": "No data"}), 500

    errors, steps = git_publish()
    if errors:
        return jsonify({"ok": False, "errors": errors, "steps": steps})
    return jsonify({"ok": True, "steps": steps})


@app.route("/api/finalise", methods=["POST"])
def api_finalise():
    data = load_data()
    if data is None:
        return jsonify({"error": "No data"}), 500

    body     = request.json or {}
    date_str = body.get("date")  # optional override

    errors, steps, date_str = git_finalise(date_str)
    pages_url   = get_pages_url()
    results_url = f"{pages_url}/past_results/{date_str}.html" if pages_url else None
    archive_url = f"{pages_url}/archive.html" if pages_url else None

    if errors:
        return jsonify({"ok": False, "errors": errors, "steps": steps, "date_str": date_str})
    return jsonify({
        "ok": True, "steps": steps, "date_str": date_str,
        "results_url": results_url, "archive_url": archive_url,
    })


if __name__ == "__main__":
    import socket
    from validate import validate_and_sync

    print("\n  Validating players.txt...")
    ok, msg = validate_and_sync()
    print(msg)
    if not ok:
        print("\n  Fix the errors above, then restart.\n")
        raise SystemExit(1)

    if os.path.exists(DATA_FILE):
        os.makedirs(_BACKUP_DIR, exist_ok=True)
        shutil.copy2(DATA_FILE, BAK_SESSION)
        print(f"  Session backup written to {BAK_SESSION}")

    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "localhost"
    print(f"\n  Supersmash Saturdays Admin Server")
    print(f"  Admin panel: http://{local_ip}:5000")
    print(f"  Also at:     http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
