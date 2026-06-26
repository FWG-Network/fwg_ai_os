from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import gradio as gr
import os

app = FastAPI()

# Agent endpoint
@app.post("/agent")
async def agent(request: Request):
    data = await request.json()
    task = data.get("task", "")
    
    # Agent logic នៅទីនេះ
    result = f"Agent processed: {task}"
    return JSONResponse({"status": "ok", "result": result})

@app.get("/health")
async def health():
    return {"status": "running"}

# Gradio UI (required for HF Space)
demo = gr.Interface(
    fn=lambda x: f"Agent: {x}",
    inputs="text",
    outputs="text",
    title="FWG AI OS Agent"
)

app = gr.mount_gradio_app(app, demo, path="/")
