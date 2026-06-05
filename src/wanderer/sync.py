import asyncio
import logging

from health_data_service import HealthDataClient
from health_data_service import WorkoutsRequest

from . import db
from .gpx import downsample
from .gpx import parse_gpx_points
from .models import SyncResult
from .models import Track

log = logging.getLogger(__name__)

# Max new workout details to pull per pass, so the frontend renders
# progressively and a single request never blocks on hundreds of fetches.
BATCH = 24


async def _fetch_track(client: HealthDataClient, summary: object) -> Track | None:
    """Pull one workout's full detail and reduce its route to a cached Track.
    Returns None only on fetch failure (so it'll be retried next pass); a
    workout with no GPS route yields a Track with empty points."""
    workout_id: str = summary.id  # type: ignore[attr-defined]
    try:
        full = await client.get_workout_merged(workout_id)
    except Exception:
        log.warning("detail fetch failed for %s", workout_id)
        return None
    gpx = getattr(full, "route_gpx", None) if full else None
    points = downsample(parse_gpx_points(gpx)) if gpx else []
    return Track(
        workout_id=workout_id,
        workout_type=summary.workout_type,  # type: ignore[attr-defined]
        start=summary.start.isoformat(),  # type: ignore[attr-defined]
        points=points,
    )


async def sync_pass(client: HealthDataClient) -> SyncResult:
    """Fetch detail for up to BATCH not-yet-cached workouts and store them."""
    summaries = await client.get_workouts_merged(WorkoutsRequest(limit=100000))
    known = await db.cached_ids()
    missing = [s for s in summaries if s.id not in known]
    batch = missing[:BATCH]

    results = await asyncio.gather(*[_fetch_track(client, s) for s in batch])
    stored = [t for t in results if t is not None]
    for track in stored:
        await db.store_track(track)

    return SyncResult(
        fetched=len(stored),
        cached=len(known) + len(stored),
        pending=len(missing) - len(stored),
        total=len(summaries),
    )
