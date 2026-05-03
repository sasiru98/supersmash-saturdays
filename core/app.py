#!/usr/bin/env python3
"""Flask admin server for Supersmash Saturdays."""

import json
import os
import subprocess

from flask import Flask, jsonify, render_template, request

from generate_index import generate_index

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE  = os.path.join(_REPO_ROOT, "tournament.json")
app = Flask(__name__, template_folder=os.path.join(_REPO_ROOT, "templates"))


def load_data():
    if not os.path.exists(DATA_FILE):
        return None
    with open(DATA_FILE) as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def git_publish():
    """Regenerate index.html, commit to dev, merge to main, push both."""
    generate_index()
    errors = []

    def run(cmd):
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=_REPO_ROOT)
        if r.returncode != 0:
            errors.append(f"{' '.join(cmd)}: {r.stderr.strip()}")
        return r.returncode == 0

    # Stage and commit on dev
    run(["git", "checkout", "dev"])
    run(["git", "add", "tournament.json", "index.html"])
    run(["git", "commit", "-m", "Update scores and standings"])
    run(["git", "push", "origin", "dev"])

    # Merge dev into main
    run(["git", "checkout", "main"])
    run(["git", "merge", "dev", "--no-edit"])
    run(["git", "push", "origin", "main"])

    # Return to dev
    run(["git", "checkout", "dev"])

    return errors


@app.route("/")
def admin():
    data = load_data()
    if data is None:
        return "tournament.json not found. Run setup.py first.", 500
    return render_template("admin.html", data=data)


@app.route("/api/data")
def api_data():
    data = load_data()
    if data is None:
        return jsonify({"error": "No data"}), 500
    return jsonify(data)


@app.route("/api/score", methods=["POST"])
def api_score():
    body = request.json
    data = load_data()
    if data is None:
        return jsonify({"error": "No data"}), 500

    group = body.get("group")
    round_idx = body.get("round")
    match_idx = body.get("match")
    score1 = body.get("score1")
    score2 = body.get("score2")

    try:
        match = data["groups"][group]["rounds"][round_idx][match_idx]
        match["score1"] = int(score1) if score1 != "" and score1 is not None else None
        match["score2"] = int(score2) if score2 != "" and score2 is not None else None
        save_data(data)
        return jsonify({"ok": True})
    except (KeyError, IndexError, TypeError, ValueError) as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/team_name", methods=["POST"])
def api_team_name():
    body = request.json
    data = load_data()
    if data is None:
        return jsonify({"error": "No data"}), 500

    team_idx = body.get("index")
    name = body.get("name", "").strip()
    if not name:
        return jsonify({"error": "Name cannot be empty"}), 400

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


@app.route("/api/publish", methods=["POST"])
def api_publish():
    data = load_data()
    if data is None:
        return jsonify({"error": "No data"}), 500

    errors = git_publish()
    if errors:
        return jsonify({"ok": False, "errors": errors})
    return jsonify({"ok": True})


if __name__ == "__main__":
    import socket
    from validate import validate_and_sync

    print("\n  Validating players.txt...")
    ok, msg = validate_and_sync()
    print(msg)
    if not ok:
        print("\n  Fix the errors above, then restart.\n")
        raise SystemExit(1)

    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "localhost"
    print(f"\n  Supersmash Saturdays Admin Server")
    print(f"  Admin panel: http://{local_ip}:5000")
    print(f"  Also at:     http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
