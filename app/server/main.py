from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from pathlib import Path
import os, json, datetime, uuid, asyncio, requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
UI_INDEX = ROOT / "app" / "ui" / "index.html"
LOG_DIR = ROOT / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="SGR Prompt Lab — Minimal")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
def root():
    return UI_INDEX.read_text(encoding="utf-8")

@app.get("/api/models/ollama_live")
def get_models():
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    names = []
    try:
        r = requests.get(base_url.rstrip("/") + "/models", timeout=3)
        if r.ok:
            data = r.json()
            if isinstance(data, dict) and "data" in data:  # OpenAI format
                for m in data["data"]:
                    names.append(m.get("id") or m.get("name") or m.get("model"))
            if isinstance(data, dict) and "models" in data:
                for m in data["models"]:
                    names.append(m.get("name") or m.get("model"))
            elif isinstance(data, list):
                for m in data:
                    names.append(m.get("name") or m.get("model"))
    except Exception:
        pass
    if not names:
        try:
            r = requests.get(base_url.rstrip("/") + "/api/tags", timeout=3)
            if r.ok:
                data = r.json()
                for m in data.get("models", []):
                    names.append(m.get("name"))
        except Exception:
            pass
    return JSONResponse({"models": sorted(set(filter(None, names)))} )

class ChatRequest(BaseModel):
    model_id: str
    params: dict
    messages: list

def get_client():
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    api_key = os.getenv("OLLAMA_API_KEY", "ollama")
    return OpenAI(base_url=base_url, api_key=api_key)

def log_interaction(payload, response):
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    fname = LOG_DIR / f"{ts}_{uuid.uuid4().hex[:6]}.json"
    with fname.open("w", encoding="utf-8") as f:
        json.dump({"timestamp": ts, "request": payload, "response": response}, f, ensure_ascii=False, indent=2)

@app.post("/api/chat")
def chat(req: ChatRequest):
    client = get_client()
    completion = client.chat.completions.create(
        model=req.model_id, messages=req.messages, **req.params
    )
    content = completion.choices[0].message.content
    out = {"content": content, "raw": completion.model_dump()}
    log_interaction(req.model_dump(), out)
    return out

@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest):
    client = get_client()
    params = dict(req.params or {}); params["stream"] = True
    completion = client.chat.completions.create(model=req.model_id, messages=req.messages, **params)
    acc = ""
    async def gen():
        nonlocal acc
        for chunk in completion:
            piece = chunk.choices[0].delta.content or ""
            acc += piece
            yield piece
            await asyncio.sleep(0.01)
        log_interaction(req.model_dump(), {"content": acc})
    return StreamingResponse(gen(), media_type="text/plain")
