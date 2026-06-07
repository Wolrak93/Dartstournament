"""Seed the database with the known tournament players.

Run from the backend/ directory:
    uv run python seed.py
"""

import asyncio

from app.database import AsyncSessionLocal, init_db
from app.models.player import Player

PLAYERS = [
    {"name": "Philipp",  "photo_path": "Philipp.png",  "music_path": "Philipp.mp3",  "championship_count": 3},
    {"name": "Mike",     "photo_path": "Mike.png",     "music_path": "Mike.mp3",     "championship_count": 0},
    {"name": "Henrik",   "photo_path": "Henrik.png",   "music_path": "Henrik.mp3",   "championship_count": 0},
    {"name": "Lars",     "photo_path": "Lars.png",     "music_path": "Lars.mp3",     "championship_count": 0},
    {"name": "Joachim",  "photo_path": "Joachim.png",  "music_path": "Joachim.mp3",  "championship_count": 2},
    {"name": "Jonas",    "photo_path": "Jonas.png",    "music_path": "Jonas.mp3",    "championship_count": 0},
    {"name": "Janni",    "photo_path": "Janni.png",    "music_path": "Janni.mp3",    "championship_count": 0},
    {"name": "Jens",     "photo_path": "Jens.png",     "music_path": "Jens.mp3",     "championship_count": 1},
    {"name": "Elina",    "photo_path": "Elina.png",    "music_path": "Elina.mp3",    "championship_count": 0},
    {"name": "Lena",     "photo_path": "Lena.png",     "music_path": "Lena.mp3",     "championship_count": 0},
]


async def seed() -> None:
    await init_db()
    async with AsyncSessionLocal() as session:
        async with session.begin():
            for data in PLAYERS:
                session.add(Player(**data))
    print(f"Seeded {len(PLAYERS)} players.")


if __name__ == "__main__":
    asyncio.run(seed())
