from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = "sqlite+aiosqlite:///./darts.db"

engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Migration: add 'name' column to tournaments if it does not exist yet
        result = await conn.execute(text("PRAGMA table_info(tournaments)"))
        columns = [row[1] for row in result.fetchall()]
        if "name" not in columns:
            await conn.execute(text("ALTER TABLE tournaments ADD COLUMN name VARCHAR"))
        result = await conn.execute(text("PRAGMA table_info(players)"))
        columns = [row[1] for row in result.fetchall()]
        if "pin" not in columns:
            await conn.execute(text("ALTER TABLE players ADD COLUMN pin VARCHAR(4)"))
