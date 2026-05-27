import uuid
import logging
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from database import init_db, save_message
from chatbot import chatbot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ChatRequest(BaseModel):
    session_id: str = ""
    message: str = Field(..., min_length=1)

class ChatResponse(BaseModel):
    intent: str
    confidence: float
    response: str
    session_id: str
    timestamp: str

@app.on_event("startup")
def startup():
    init_db()

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session_id = request.session_id.strip()
    if not session_id:
        session_id = str(uuid.uuid4())
    # сохраняем вопрос
    save_message(session_id, 'user', request.message)
    # ответ бота
    result = chatbot.process_message(request.message, session_id)
    # сохраняем ответ
    save_message(session_id, 'bot', result['response'], result['intent'], result['confidence'])
    return ChatResponse(
        intent=result['intent'],
        confidence=result['confidence'],
        response=result['response'],
        session_id=session_id,
        timestamp=datetime.now().isoformat()
    )

@app.post("/api/operator/escalate")
async def escalate():
    return {"message": "Оператор скоро подключится", "ticket_id": f"T-{int(datetime.now().timestamp())}"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)