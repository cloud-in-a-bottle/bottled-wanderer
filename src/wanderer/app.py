import logging
from pathlib import Path

import attr
from health_data_service import HealthDataClient
from litestar import Litestar
from litestar import MediaType
from litestar import get
from litestar import post

from . import db
from . import sync
from .models import RoutesResponse
from .models import SyncResult

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)

MAP_HTML = (Path(__file__).parent / "templates" / "map.html").read_text()

_client: HealthDataClient | None = None


@attr.s(auto_attribs=True, frozen=True)
class HealthStatus:
    status: str


@get("/health", sync_to_thread=False)
def health() -> HealthStatus:
    return HealthStatus(status="ok")


@get("/", media_type=MediaType.HTML, sync_to_thread=False)
def index() -> str:
    return MAP_HTML


@get("/api/routes")
async def routes() -> RoutesResponse:
    tracks = await db.get_tracks()
    return RoutesResponse(count=len(tracks), tracks=tracks)


@post("/api/sync")
async def run_sync() -> SyncResult:
    """Pull detail for the next batch of not-yet-cached workouts. The frontend
    calls this repeatedly until ``pending`` reaches zero."""
    if _client is None:
        cached = len(await db.cached_ids())
        return SyncResult(fetched=0, cached=cached, pending=0, total=cached)
    return await sync.sync_pass(_client)


async def on_startup() -> None:
    global _client
    await db.init_db()
    try:
        _client = HealthDataClient()
        await _client.__aenter__()
    except Exception:
        log.warning("HealthDataClient unavailable (service env vars not set); serving cache only")
        _client = None


async def on_shutdown() -> None:
    global _client
    if _client is not None:
        await _client.__aexit__(None, None, None)
        _client = None


app = Litestar(
    route_handlers=[health, index, routes, run_sync],
    on_startup=[on_startup],
    on_shutdown=[on_shutdown],
)
