from contextlib import asynccontextmanager

from fastapi import FastAPI

# Import all models so that Base.metadata knows about every table
# before create_all() is called inside init_db().
import app.models  # noqa: F401
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Backsberger Open", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
