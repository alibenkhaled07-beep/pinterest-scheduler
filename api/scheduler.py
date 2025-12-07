# api/scheduler.py
from fastapi import FastAPI, Header, HTTPException
import os, requests, base64, time, csv, logging, json

app = FastAPI()
logger = logging.getLogger("scheduler")
logging.basicConfig(level=logging.INFO)

GITHUB_API = "https://api.github.com"

# helper: list repo files (root)
def list_repo_files(owner, repo, branch, token):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents?ref={branch}"
    headers = {"Authorization": f"token {token}"}
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()  # list of items

# helper: get raw url for file
def raw_url(owner, repo, branch, path):
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"

# helper: fetch file content (base64 via GitHub) and sha
def get_file_info(owner, repo, path, branch, token):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    headers = {"Authorization": f"token {token}"}
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()  # contains 'content' (base64), 'sha', 'encoding'

# helper: create file (used to create processed/<name>)
def create_file(owner, repo, path, content_bytes, message, branch, token):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}"}
    data = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode(),
        "branch": branch
    }
    r = requests.put(url, headers=headers, json=data, timeout=30)
    r.raise_for_status()
    return r.json()

# helper: delete file (use sha)
def delete_file(owner, repo, path, sha, message, branch, token):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}"}
    data = {"message": message, "sha": sha, "branch": branch}
    r = requests.delete(url, headers=headers, json=data, timeout=30)
    r.raise_for_status()
    return r.json()

# Re-use your run logic by calling your /run endpoint internally (HTTP)
def run_raw_csv(raw_csv_url, dry_run, delay, token):
    # call local endpoint /run - adjust domain as needed from env
    # We'll call internal function by issuing an HTTP request to live endpoint
    VERCEL_DOMAIN = os.environ.get("VERCEL_URL")  # e.g. pinterest-scheduler-psi.vercel.app
    if VERCEL_DOMAIN:
        base = f"https://{VERCEL_DOMAIN}"
    else:
        # fallback to hard-coded; better to set VERCEL_URL env var in Vercel
        base = "https://pinterest-scheduler-psi.vercel.app"
    url = f"{base}/run"
    params = {"raw_csv_url": raw_csv_url, "dry_run": str(dry_run).lower(), "delay": delay}
    if token:
        params["token"] = token
    r = requests.get(url, params=params, timeout=300)
    r.raise_for_status()
    return r.json()

@app.get("/run-scheduled")
def run_scheduled(x_scheduler_token: str | None = Header(None)):
    # auth
    secret = os.environ.get("SCHEDULER_SECRET")
    if not secret or x_scheduler_token != secret:
        raise HTTPException(status_code=403, detail="Forbidden")

    owner = os.environ.get("REPO_OWNER")
    repo = os.environ.get("REPO_NAME")
    branch = os.environ.get("REPO_BRANCH", "main")
    gh_token = os.environ.get("GITHUB_TOKEN")
    pinterest_token = os.environ.get("PINTEREST_TOKEN")
    default_delay = float(os.environ.get("DEFAULT_DELAY", "1"))

    if not all([owner, repo, gh_token]):
        raise HTTPException(status_code=500, detail="Missing repo configuration envs")

    # 1) list root files and find next pins_bulk_*.csv
    items = list_repo_files(owner, repo, branch, gh_token)
    # filter by name pattern
    candidates = [it["name"] for it in items if it["type"] == "file" and it["name"].startswith("pins_bulk_")]
    candidates.sort()  # alphabetical => predictable order
    if not candidates:
        return {"status": "idle", "message": "no pins_bulk files found"}

    next_file = candidates[0]
    # get raw url
    rurl = raw_url(owner, repo, branch, next_file)

    # 2) call run (real) - here we run dry_run=false to send pins
    try:
        result = run_raw_csv(rurl, dry_run=False, delay=default_delay, token=None)
    except Exception as e:
        logger.exception("run failed")
        return {"status": "error", "error": str(e)}

    # 3) if result indicates success (you can change condition), then move the file to processed/
    # here assume result['status'] == 'done' or we check results for ok flags
    success = result.get("status") == "done" or (result.get("rows_sent",0) > 0)
    if success:
        # fetch file info (content + sha)
        info = get_file_info(owner, repo, next_file, branch, gh_token)
        content_b64 = info.get("content", "")
        sha = info.get("sha")
        if not content_b64 or not sha:
            return {"status": "error", "message": "failed to read file content for moving"}

        # create new file under processed/<name>
        processed_path = f"processed/{next_file}"
        create_msg = f"Move {next_file} to processed/"
        try:
            create_file(owner, repo, processed_path, base64.b64decode(content_b64), create_msg, branch, gh_token)
            # delete original
            delete_file(owner, repo, next_file, sha, f"Remove original {next_file} after processing", branch, gh_token)
        except Exception as e:
            logger.exception("move failed")
            return {"status": "partial_success", "run_result": result, "move_error": str(e)}

        return {"status": "done_and_moved", "file": next_file, "run_result": result}
    else:
        return {"status": "run_failed", "run_result": result}
