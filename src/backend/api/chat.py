import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.llm_provider import stream_chat

router = APIRouter()


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    cv_text: str | None = None
    jd_text: str | None = None


@router.post("/api/chat")
def chat(req: ChatRequest):
    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    def generate():
        for chunk in stream_chat(messages, req.cv_text, req.jd_text):
            yield f"data: {json.dumps({'text': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
