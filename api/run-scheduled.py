import os
from fastapi import Request, HTTPException

async def run_scheduled(request: Request):
    auth = request.headers.get("Authorization")
    if auth != f"Bearer {os.getenv('CRON_SECRET')}":
        raise HTTPException(status_code=401, detail="Unauthorized")
import os
from fastapi import FastAPI, Request
import requests

app = FastAPI()

SECRET = os.getenv("SCHEDULER_SECRET")

@app.get("/api/run-scheduled")
async def run_scheduled(request: Request):
    token = request.headers.get("x-scheduler-token")
    if token != SECRET:
        return {"error": "Unauthorized"}

    # Call main runner
    url = "https://" + request.url.hostname + "/api/run"
    resp = requests.get(url).json()

    return {"status": "triggered", "result": resp}
