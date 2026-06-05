import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from Agent_models import RiopailaAgent

app = FastAPI(
    title="Riopaila Castilla API",
    description="API del asistente corporativo Riopaila Castilla",
    version="1.0.0",
)

agent = RiopailaAgent()


class ChatRequest(BaseModel):
    message: str
    user_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    user_id: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        uid = req.user_id or f"api_{os.urandom(4).hex()}"
        ans = agent.ask(req.message, thread_id=uid)
        return ChatResponse(response=ans, user_id=uid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
