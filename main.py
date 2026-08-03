import logging

from dotenv import load_dotenv

load_dotenv()  # must run before database.py / ai_setup.py read env vars at import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from database import Base, engine
from rate_limit import limiter
from routers import auth, conversations, messages, survey, chat, resources, tiles, insights

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="SENTI API", version="1.0.0")

# Rate limiting — keyed by client IP. Auth endpoints (login/signup/forgot-password)
# set their own tighter per-route limits (see routers/auth.py); this is just the
# app-wide wiring + the 429 handler.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Loosened for local dev (Android emulator / device on the same network).
# Tighten this to your actual client origin(s) before shipping anywhere real.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(conversations.router)
app.include_router(messages.router)
app.include_router(survey.router)
app.include_router(chat.router)
app.include_router(resources.router)
app.include_router(tiles.router)
app.include_router(insights.router)


@app.on_event("startup")
def on_startup():
    # Convenience for local dev via `uvicorn main:app`. For anything beyond
    # a single dev machine, switch to Alembic migrations instead.
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}