import asyncio
import logging

from health_data_service import HealthDataClient

from . import db
from .gpx import downsample
from .gpx import parse_gpx_points
from .models import SyncResult
from .models import Track

log = logging.getLogger(__name__)

# Max new workout details to pull per pass, so the frontend renders
# progressively and a single request never blocks on hundreds of fetches.
BATCH = 24


async def _fetch_track(client: HealthDataClient, summary: dict[str, object]) -> Track | None:
    """Pull one workout's full detail and reduce its route to a cached Track.
    Returns None only on fetch failure (so it's retried next pass); a workout
    with no GPS route yields a Track with empty points."""
    workout_id = str(summary["id"])
    try:
        results = await client._fan_out(f"/v1/workouts/{workout_id}")
    except Exception:
        log.warning("detail fetch failed for %s", workout_id)
        return None
    detail = next((r for r in results if r), None)
    gpx = detail.get("route_gpx") if detail else None
    points = downsample(parse_gpx_points(gpx)) if isinstance(gpx, str) else []
    return Track(
        workout_id=workout_id,
        workout_type=str(summary.get("workout_type", "other")),
        start=str(summary.get("start", "")),
        points=points,
    )


async def sync_pass(client: HealthDataClient) -> SyncResult:
    """Fetch detail for up to BATCH not-yet-cached workouts and store them.

    Works with raw dicts (not the typed Workout model) so it's robust to the
    full variety of real provider data."""
    results = await client._fan_out("/v1/workouts", {"limit": "100000"})
    summaries: list[dict[str, object]] = []
    for r in results:
        summaries.extend(r.get("data", []))
    summaries = [s for s in summaries if s.get("id")]
    summaries.sort(key=lambda s: str(s.get("start", "")), reverse=True)

    known = await db.cached_ids()
    missing = [s for s in summaries if str(s["id"]) not in known]
    batch = missing[:BATCH]

    fetched = await asyncio.gather(*[_fetch_track(client, s) for s in batch])
    stored = [t for t in fetched if t is not None]
    for track in stored:
        await db.store_track(track)

    return SyncResult(
        fetched=len(stored),
        cached=len(known) + len(stored),
        pending=len(missing) - len(stored),
        total=len(summaries),
    )
