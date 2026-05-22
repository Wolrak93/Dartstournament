from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Import all models so that Base.metadata knows about every table
# before create_all() is called inside init_db().
import app.models  # noqa: F401
from app.database import init_db
from app.exceptions import AppError
from app.routers import matches, players, tournaments, ws

# Resolve user_input/pics relative to this file (backend/app/main.py → ../../user_input/pics)
_PICS_DIR = Path(__file__).resolve().parent.parent.parent / "user_input" / "pics"
_SOUND_DIR = Path(__file__).resolve().parent.parent.parent / "user_input" / "sound"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Backsberger Open", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if _PICS_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_PICS_DIR)), name="static")

if _SOUND_DIR.exists():
    app.mount("/sounds", StaticFiles(directory=str(_SOUND_DIR)), name="sounds")


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(players.router)
app.include_router(tournaments.router)
app.include_router(matches.router)
app.include_router(ws.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
