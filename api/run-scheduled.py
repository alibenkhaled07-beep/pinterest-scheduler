import os
import requests
from fastapi import Request
from fastapi.responses import JSONResponse

CRON_SECRET = os.getenv("CRON_SECRET")

async def handler(request: Request):
    auth = request.headers.get("authorization")

    if auth != f"Bearer {CRON_SECRET}":
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    # CALL YOUR PINTEREST SCRIPT HERE
    return JSONResponse({"status": "cron executed!"})
