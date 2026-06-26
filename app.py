from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/")
def root():
    return {"status": "FWG Agent Running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/agent")
async def agent(request: Request):
    data = await request.json()
    task = data.get("task", "")
    return JSONResponse({"status": "ok", "task": task})
