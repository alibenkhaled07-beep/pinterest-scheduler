# api/app.py
from fastapi import FastAPI, Query, HTTPException
import os, csv, requests

app = FastAPI()

@app.get("/run")
def run(raw_csv_url: str = Query(...), token: str | None = Query(None)):
    # أولًا نحاول ناخدو التوكن من query، وإلا من env
    token = token or os.environ.get("PINTEREST_TOKEN")
    if not token:
        raise HTTPException(status_code=400, detail="missing token (pass ?token=... or set PINTEREST_TOKEN in env)")

    # جلب CSV من GitHub
    resp = requests.get(raw_csv_url, timeout=15)
    resp.raise_for_status()
    rows = list(csv.DictReader(resp.text.splitlines()))

    # هنا غير نردّو عدد الأسطر باش نختبرو — بعد ما تتأكد تقدر تبعّث Pins فعلياً
    return {"status": "ok", "rows": len(rows)}
