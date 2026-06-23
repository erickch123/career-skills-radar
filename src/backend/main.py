from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

load_dotenv()

app = FastAPI(title="Career Radar API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
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


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "career-radar-api"}
