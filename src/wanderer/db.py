import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aiosqlite

from .models import Track

_DB_PATH = os.environ["OPENHOST_SQLITE_ROUTES"]


@asynccontextmanager
async def connect() -> AsyncIterator[aiosqlite.Connection]:
    conn = await aiosqlite.connect(_DB_PATH)
    try:
        yield conn
    finally:
        await conn.close()


async def init_db() -> None:
    async with connect() as conn:
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS routes (
                workout_id   TEXT PRIMARY KEY,
                workout_type TEXT NOT NULL,
                start_ts     TEXT NOT NULL,
                points       TEXT NOT NULL
            )"""
        )
        await conn.commit()


async def cached_ids() -> set[str]:
    async with connect() as conn:
        rows = await (await conn.execute("SELECT workout_id FROM routes")).fetchall()
    return {r[0] for r in rows}


async def store_track(track: Track) -> None:
    async with connect() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO routes (workout_id, workout_type, start_ts, points) VALUES (?, ?, ?, ?)",
            (track.workout_id, track.workout_type, track.start, json.dumps(track.points)),
        )
        await conn.commit()


async def get_tracks() -> list[Track]:
    """All cached tracks that actually have GPS points, newest first."""
    async with connect() as conn:
        rows = await (
            await conn.execute("SELECT workout_id, workout_type, start_ts, points FROM routes ORDER BY start_ts DESC")
        ).fetchall()
    tracks = [Track(workout_id=r[0], workout_type=r[1], start=r[2], points=json.loads(r[3])) for r in rows]
    return [t for t in tracks if t.points]
