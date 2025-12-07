# api/run-scheduled.py
from urllib.parse import unquote_plus
import os
import requests
from http import HTTPStatus

def handler(request):
    # Vercel Python functions expect some frameworks; if you're using plain python handler adjust accordingly.
    # If you use the example app in repo, adapt to that style. This is pseudo logic to show checks.

    # check Authorization header
    auth = request.headers.get("Authorization") or ""
    expected = f"Bearer {os.environ.get('CRON_SECRET','')}"
    if auth != expected:
        return ({"detail": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)

    # get raw_csv_url param
    raw_csv_url = request.args.get("raw_csv_url") or request.query.get("raw_csv_url")
    if not raw_csv_url:
        return ({"detail":"missing raw_csv_url"}, HTTPStatus.BAD_REQUEST)

    # (example) fetch the CSV and do processing
    try:
        r = requests.get(raw_csv_url, timeout=10)
        r.raise_for_status()
    except Exception as e:
        return ({"detail":"fetch error","err":str(e)}, HTTPStatus.BAD_GATEWAY)

    # TODO: parse CSV and create pins (your existing logic)
    # for now return preview info
    return ({"status":"ok","len": len(r.text.splitlines())}, HTTPStatus.OK)
