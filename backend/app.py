import uuid
import logging
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from database import init_db, save_message, get_dialog_history, get_escalated_sessions, has_operator_replied
from chatbot import chatbot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatReq(BaseModel):
    session_id: str = ""
    message: str = Field(..., min_length=1)

class ChatResp(BaseModel):
    intent: str
    confidence: float
    response: str
    session_id: str
    timestamp: str

@app.on_event("startup")
def startup():
    init_db()

@app.post("/api/chat", response_model=ChatResp)
async def chat(req: ChatReq):
    sid = req.session_id.strip() or str(uuid.uuid4())
    user_intent = chatbot.detect_intent(req.message) or 'unknown'
    save_message(sid, 'user', req.message, intent=user_intent, confidence=0.9)
    result = chatbot.process_message(req.message, sid)
    save_message(sid, 'bot', result['response'], intent=result['intent'], confidence=result['confidence'])
    
    # Если пользователь вызвал оператора и оператор ещё не отвечал в этой сессии
    if result['intent'] == 'operator' and not has_operator_replied(sid):
        template = "Здравствуйте! Я оператор. Чем могу помочь?"
        save_message(sid, 'operator', template, intent='operator_greeting', confidence=1.0)
    
    return ChatResp(
        intent=result['intent'],
        confidence=result['confidence'],
        response=result['response'],
        session_id=sid,
        timestamp=datetime.now().isoformat()
    )

@app.get("/api/history/{session_id}")
async def history(session_id: str, limit: int = 50):
    return {"session_id": session_id, "messages": get_dialog_history(session_id, limit)}

@app.get("/api/admin/escalated_sessions")
async def admin_escalated_sessions():
    return get_escalated_sessions()

@app.get("/api/admin/messages/{session_key}")
async def admin_messages(session_key: str, limit: int = 200):
    return {"session_key": session_key, "messages": get_dialog_history(session_key, limit)}

@app.post("/api/admin/reply")
async def admin_reply(session_key: str, message: str):
    save_message(session_key, 'operator', message)
    return {"status": "sent", "session_key": session_key}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)