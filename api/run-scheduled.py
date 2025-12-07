# api/run-scheduled.py
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/", methods=["GET"])
def handler():
    auth = request.headers.get("Authorization", "")
    expected = f"Bearer {os.environ.get('CRON_SECRET','')}"
    if auth != expected:
        return jsonify({"detail":"Unauthorized"}), 401

    # --- place your scheduling logic here (call scheduler.process or read CSV etc)
    # example response:
    return jsonify({"status":"ok","message":"scheduled run started"})

# For Vercel Python serverless, file should expose `app`
