from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from api.match import router as match_router

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


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "career-radar-api"}
