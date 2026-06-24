import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from api.match import router as match_router
from api.chat import router as chat_router
from api.profile import router as profile_router
from api.jobs import router as jobs_router
from api.gap import router as gap_router
from api.insights import router as insights_router
from api.worklog import router as worklog_router
from api.email_jobs import router as email_router
from api.notifications import router as notify_router
from api.timeline import router as timeline_router

load_dotenv()

app = FastAPI(title="Career Radar API", version="0.1.0")

# Read-only demo mode — set DEMO_READONLY=true in .env to block all writes.
# Chat, match, and insights still work (they read DB but never write).
_DEMO_PASSTHROUGH_POSTS = {"/api/chat", "/match", "/api/insights/classify", "/api/apify/search"}

@app.middleware("http")
async def demo_readonly_guard(request: Request, call_next):
    if os.getenv("DEMO_READONLY", "").lower() == "true":
        if request.method not in ("GET", "HEAD", "OPTIONS") and \
                request.url.path not in _DEMO_PASSTHROUGH_POSTS:
            return JSONResponse(
                status_code=403,
                content={
                    "demo": True,
                    "message": "This is a read-only demo — adding or removing data is disabled.",
                },
            )
    return await call_next(request)

_deployed_origin = os.getenv("FRONTEND_ORIGIN", "")
_allowed_origins = ["http://localhost:5173"]
if _deployed_origin:
    _allowed_origins.append(_deployed_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(match_router)
app.include_router(chat_router)
app.include_router(profile_router)
app.include_router(jobs_router)
app.include_router(gap_router)
app.include_router(insights_router)
app.include_router(worklog_router)
app.include_router(email_router)
app.include_router(notify_router)
app.include_router(timeline_router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "career-radar-api"}
