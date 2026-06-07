"""Set 4-digit PINs for players before the tournament.

Usage:
    cd backend
    uv run python scripts/set_pins.py

Edit the PINS dictionary below before running.
Each key is the player's exact name as stored in the database.
Each value is a 4-digit string PIN.

Example:
    PINS = {
        "Lars": "1234",
        "Mike": "5678",
        "Philipp": "9012",
    }
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure the backend package is importable when run from the backend/ directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.database import AsyncSessionLocal, init_db
from app.models.player import Player

# --- Edit this dict before running ---
PINS: dict[str, str] = {
    "Lars": "0000",
    "Mike": "0000",
    "Henrik": "0000",
    "Philipp": "0000",
    "Jonas": "0000",
    "Janni": "0000",
    "Jens": "0000",
    "Elina": "0000",
    "Lena": "0000",
    "Joachim": "0000",
}
# -------------------------------------


async def main() -> None:
    await init_db()
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Player))
        players = result.scalars().all()
        player_map = {p.name: p for p in players}

        updated = []
        not_found = []
        for name, pin in PINS.items():
            if name in player_map:
                player_map[name].pin = pin
                updated.append(name)
            else:
                not_found.append(name)

        await db.commit()

    print(f"Updated PINs for: {', '.join(updated)}")
    if not_found:
        print(f"WARNING — players not found in DB: {', '.join(not_found)}")


if __name__ == "__main__":
    asyncio.run(main())
