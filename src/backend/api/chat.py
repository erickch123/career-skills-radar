import json
import os
from collections.abc import Generator

import anthropic
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from core.agent_tools import TOOL_SCHEMAS, run_tool

router = APIRouter()

MODEL = "claude-haiku-4-5-20251001"
MAX_TOOL_ITERS = 5
CHUNK_SIZE = 20  # chars per fake-stream chunk for final response

SYSTEM_PROMPT = """\
You are Career Radar, an AI career advisor specialised in Singapore's job market \
and the SkillsFuture Skills Framework.

You have access to tools that let you read the user's CV skills, saved jobs, \
skills gap analysis, career pathfinder, and work log. Use them proactively \
when answering career questions — for example, call get_gap_analysis before \
recommending what to learn, or call list_saved_jobs before ranking opportunities.

Guidelines:
- Be specific and practical — name actual skills, courses, and roles
- Keep responses concise; use bullet points for lists
- Refer to Singapore context where relevant (SkillsFuture credits, WSQ, etc.)
- When the user asks "which job am I most ready for?", call list_saved_jobs \
  then get_gap_analysis to give a data-backed answer
"""


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    cv_text: str | None = None
    jd_text: str | None = None


@router.post("/api/chat")
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    def generate() -> Generator[str, None, None]:
        yield from _agent_stream(messages, db, req.cv_text)
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ── Agentic loop ──────────────────────────────────────────────────────────────

def _err(msg: str) -> str:
    return f"data: {json.dumps({'type': 'error', 'message': msg})}\n\n"


def _agent_stream(
    messages: list[dict],
    db: Session,
    cv_text: str | None = None,
) -> Generator[str, None, None]:
    """
    Run the agentic tool loop then stream the final text response.

    SSE event shapes:
      {"type": "tool_call", "tool": "<name>"}      — one per tool invocation
      {"text": "<chunk>"}                           — chunks of the final answer
      {"type": "error", "message": "<human msg>"}  — any failure
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        yield _err("ANTHROPIC_API_KEY is not configured. Add it to your .env file.")
        return

    client = anthropic.Anthropic(api_key=api_key)

    system = SYSTEM_PROMPT
    if cv_text:
        system += f"\n\n--- USER'S CV ---\n{cv_text}\n--- END CV ---"

    history = list(messages)

    try:
        for _ in range(MAX_TOOL_ITERS):
            resp = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=system,
                tools=TOOL_SCHEMAS,
                messages=history,
            )

            if resp.stop_reason != "tool_use":
                final_text = "".join(
                    b.text for b in resp.content if hasattr(b, "text")
                )
                for i in range(0, len(final_text), CHUNK_SIZE):
                    yield f"data: {json.dumps({'text': final_text[i:i + CHUNK_SIZE]})}\n\n"
                return

            tool_blocks = [b for b in resp.content if b.type == "tool_use"]
            for tb in tool_blocks:
                yield f"data: {json.dumps({'type': 'tool_call', 'tool': tb.name})}\n\n"

            tool_results = []
            for tb in tool_blocks:
                result = run_tool(tb.name, tb.input, db)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tb.id,
                    "content": result,
                })

            assistant_content = []
            for b in resp.content:
                if b.type == "text":
                    assistant_content.append({"type": "text", "text": b.text})
                elif b.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": b.id,
                        "name": b.name,
                        "input": b.input,
                    })
            history.append({"role": "assistant", "content": assistant_content})
            history.append({"role": "user", "content": tool_results})

        yield f"data: {json.dumps({'text': 'I was unable to complete the full analysis. Please try again.'})}\n\n"

    except anthropic.AuthenticationError:
        yield _err("API key is invalid or missing. Check ANTHROPIC_API_KEY in your .env file.")
    except anthropic.PermissionDeniedError:
        yield _err("API access denied — your Anthropic account may be out of credits or the key lacks permissions.")
    except anthropic.RateLimitError:
        yield _err("Rate limit reached. Please wait a moment and try again.")
    except anthropic.BadRequestError as e:
        yield _err(f"Bad request: {e.message}")
    except anthropic.APIConnectionError:
        yield _err("Cannot reach the Anthropic API. Check your internet connection.")
    except anthropic.APIStatusError as e:
        yield _err(f"Anthropic API error {e.status_code}: {e.message}")
    except Exception as e:
        yield _err(f"Unexpected server error: {type(e).__name__}")
