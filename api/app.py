import csv
import requests
from fastapi import FastAPI, HTTPException

app = FastAPI()

def post_to_pinterest(row, token):
    url = "https://api.pinterest.com/v5/pins"

    payload = {
        "title": row.get("title",""),
        "description": row.get("description",""),
        "alt_text": row.get("alt_text",""),
        "link": row.get("link",""),
        "board_id": row.get("board_id",""),
        "media_source": {
            "source_type": "image_url",
            "url": row.get("image_url","")
        }
    }

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    return {"status_code": response.status_code, "body": response.text}

@app.get("/run")
def run_scheduler(raw_csv_url: str, token: str):
    try:
        resp = requests.get(raw_csv_url, timeout=30)
        resp.raise_for_status()
        csv_text = resp.text.splitlines()
        reader = csv.DictReader(csv_text)

        results = []
        for row in reader:
            result = post_to_pinterest(row, token)
            results.append(result)

        return {"status": "done", "pins_sent": len(results)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
