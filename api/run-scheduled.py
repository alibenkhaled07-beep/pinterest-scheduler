# api/run-scheduled.py
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

def check_auth():
    # Vercel cron sends Authorization: Bearer <CRON_SECRET>
    auth = request.headers.get("Authorization") or request.headers.get("authorization")
    # older code sometimes used x-scheduler-token — allow both (fallback)
    x_token = request.headers.get("x-scheduler-token") or request.headers.get("X-Scheduler-Token")
    secret = os.environ.get("CRON_SECRET") or os.environ.get("SCHEDULER_SECRET")

    if auth:
        # auth looks like "Bearer secret"
        if auth.strip() == f"Bearer {secret}":
            return True
    if x_token and secret and x_token.strip() == secret:
        return True
    return False

@app.route("/", methods=["GET"])
def run():
    if not check_auth():
        # If header missing or wrong -> 401 so cron won't be executed
        return jsonify(detail="unauthorized"), 401

    # example: get raw_csv_url query param
    raw_csv = request.args.get("raw_csv_url") or os.environ.get("RAW_CSV_URL")
    # here you put your job logic: read CSV, post to Pinterest, etc.
    # For now return preview response so you can test:
    if not raw_csv:
        return jsonify(detail="no raw_csv_url provided"), 400

    # (put your real scheduler code here)
    # Example placeholder:
    return jsonify(status="ok", message="scheduled-run started", raw_csv=raw_csv)
