from fastapi import FastAPI
app = FastAPI()

@app.get("/hello")
def hello():
    return {"ok": True, "message": "Hello from Vercel!"}
