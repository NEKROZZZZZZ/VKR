import uuid
import logging
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from database import init_db, save_message
from chatbot import chatbot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ChatReq(BaseModel):
    session_id: str = ""
    message: str

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
    sid = req.session_id.strip()
    if not sid:
        sid = str(uuid.uuid4())
    # сохраняем сообщение пользователя
    save_message(sid, 'user', req.message)
    # получаем ответ бота
    result = chatbot.process_message(req.message, sid)
    # сохраняем ответ бота
    save_message(sid, 'bot', result['response'], result['intent'], result['confidence'])
    return ChatResp(
        intent=result['intent'],
        confidence=result['confidence'],
        response=result['response'],
        session_id=sid,
        timestamp=datetime.now().isoformat()
    )

@app.post("/api/operator/escalate")
async def escalate():
    return {"message": "Оператор скоро подключится", "ticket_id": f"T-{int(datetime.now().timestamp())}"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)