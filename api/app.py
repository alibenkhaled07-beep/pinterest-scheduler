# api/app.py
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
import os, csv, requests, time, logging
from typing import List, Dict, Optional

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pinterest-scheduler")

# Simple model for a CSV row (helps clarity)
class PinRow(BaseModel):
    title: str
    description: Optional[str] = ""
    alt_text: Optional[str] = ""
    link: Optional[str] = ""
    image_url: str
    board_id: str

# Helper: fetch CSV and parse
def fetch_csv_rows(raw_csv_url: str) -> List[Dict]:
    resp = requests.get(raw_csv_url, timeout=20)
    resp.raise_for_status()
    text = resp.text
    lines = text.splitlines()
    if not lines:
        return []
    reader = csv.DictReader(lines)
    rows = [r for r in reader]
    return rows

# Helper: create a pin (real POST)
def create_pin(pin_data: Dict, token: str) -> Dict:
    url = "https://api.pinterest.com/v5/pins"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    resp = requests.post(url, json=pin_data, headers=headers, timeout=20)
    # raise_for_status may raise for 4xx/5xx, but we catch later
    return {"status_code": resp.status_code, "text": resp.text}

@app.get("/run")
def run(
    raw_csv_url: str = Query(..., description="Raw CSV URL (raw.githubusercontent...)"),
    dry_run: bool = Query(True, description="If true then DO NOT send pins (default True)"),
    batch_size: int = Query(5, description="How many pins per batch"),
    delay: float = Query(1.0, description="Seconds to sleep between pins (float)"),
    token: Optional[str] = Query(None, description="Optional token override (not recommended)")
):
    """
    - dry_run=True : only preview (safe)
    - dry_run=False: will actually POST pins (ensure PINTEREST_TOKEN env var is set)
    """
    # get token from query OR env
    pinterest_token = token or os.environ.get("PINTEREST_TOKEN")
    if not dry_run and not pinterest_token:
        raise HTTPException(status_code=400, detail="Missing token: set PINTEREST_TOKEN in Vercel env or pass &token=... (not recommended)")

    # fetch CSV
    try:
        rows = fetch_csv_rows(raw_csv_url)
    except Exception as e:
        logger.exception("Failed to fetch CSV")
        raise HTTPException(status_code=400, detail=f"Failed to fetch CSV: {e}")

    if not rows:
        return {"status": "ok", "rows": 0, "message": "CSV is empty or only header"}

    # Validate and build PinRow list (ignore bad rows)
    valid_rows = []
    errors = []
    for i, row in enumerate(rows, start=1):
        # required: image_url and board_id (and title)
        title = row.get("title","").strip()
        image_url = row.get("image_url","").strip()
        board_id = row.get("board_id","").strip()
        if not title or not image_url or not board_id:
            errors.append({"line": i, "reason": "missing title or image_url or board_id", "row": row})
            continue
        # create validated dict
        pin = {
            "title": title,
            "description": row.get("description","").strip(),
            "alt_text": row.get("alt_text","").strip(),
            "link": row.get("link","").strip() or None,
            # Pinterest v5 expects media_source object for image url:
            "media_source": {"source_type": "image_url", "url": image_url},
            "board_id": board_id
        }
        valid_rows.append(pin)

    preview_count = min(5, len(valid_rows))
    preview = valid_rows[:preview_count]

    # If dry_run just return preview and counts
    if dry_run:
        return {
            "status": "preview",
            "rows_total": len(rows),
            "rows_valid": len(valid_rows),
            "preview": preview,
            "errors": errors
        }

    # If here => we will send pins for real
    results = []
    sent = 0
    for idx, pin in enumerate(valid_rows, start=1):
        # batch handling: optional, but we don't need complex batching; use delay between each
        try:
            res = create_pin(pin, pinterest_token)
            results.append({"index": idx, "ok": res["status_code"] in (200,201,202), "status_code": res["status_code"], "response": res["text"]})
            logger.info(f"Pin {idx} posted: status={res['status_code']}")
        except Exception as e:
            logger.exception("Error posting pin")
            results.append({"index": idx, "ok": False, "error": str(e)})
        sent += 1
        # delay to avoid rate limits
        time.sleep(delay)

        # optional: stop if too many failures? here we continue

    return {"status": "done", "rows_total": len(rows), "rows_sent": sent, "results": results, "errors": errors}

