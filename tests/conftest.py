import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
from pathlib import Path
from urllib.parse import urlparse

import pytest
from openhost_test_harness import OpenhostStack

_CALL = "/api/services/v2/call/health/v1/workouts"

# A short GPS track near Golden Gate Park, SF.
_GPX = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>'
    '<trkpt lat="37.7694" lon="-122.4862"><time>2026-06-01T08:00:00Z</time></trkpt>'
    '<trkpt lat="37.7701" lon="-122.4790"><time>2026-06-01T08:05:00Z</time></trkpt>'
    '<trkpt lat="37.7715" lon="-122.4700"><time>2026-06-01T08:10:00Z</time></trkpt>'
    '<trkpt lat="37.7730" lon="-122.4610"><time>2026-06-01T08:15:00Z</time></trkpt>'
    "</trkseg></trk></gpx>"
)


def _summary(workout_id: str, workout_type: str, start: str) -> dict:
    return {
        "id": workout_id,
        "start": start,
        "end": start,
        "workout_type": workout_type,
        "source": "mock",
        "duration": {
            "metric_id": "duration",
            "display_name": "Duration",
            "unit": "min",
            "value": 30.0,
            "source": "mock",
        },
        "calories": {
            "metric_id": "calories",
            "display_name": "Calories",
            "unit": "kcal",
            "value": 300.0,
            "source": "mock",
        },
    }


# A run with a GPS route, and an indoor strength session with none.
_SUMMARIES = [
    _summary("wk-run", "running", "2026-06-02T08:00:00+00:00"),
    _summary("wk-gym", "strength", "2026-06-01T18:00:00+00:00"),
]
_ROUTES = {"wk-run": _GPX}


class _MockHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/api/services/v2/providers":
            return self._json(
                {
                    "providers": [
                        {
                            "app_id": "mock-provider",
                            "app_name": "mock-health",
                            "service_version": "0.1.0",
                            "endpoint": "/api/",
                            "status": "running",
                            "is_default": True,
                        }
                    ]
                }
            )

        if path.startswith(_CALL):
            workout_id = path[len(_CALL) :].strip("/")
            if not workout_id:
                return self._json({"data": _SUMMARIES})
            match = next((s for s in _SUMMARIES if s["id"] == workout_id), None)
            if match is None:
                return self._json({"error": "not found"}, 404)
            detail = dict(match)
            if workout_id in _ROUTES:
                detail["route_gpx"] = _ROUTES[workout_id]
            return self._json(detail)

        self._json({"error": "not found"}, 404)

    def _json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture(scope="session")
def mock_service_port() -> Iterator[int]:
    server = HTTPServer(("0.0.0.0", 0), _MockHandler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield port
    server.shutdown()


@pytest.fixture(scope="session")
def stack(mock_service_port: int) -> Iterator[OpenhostStack]:
    with OpenhostStack(
        app_dir=Path(__file__).resolve().parent.parent,
        extra_env={
            "OPENHOST_ROUTER_URL": f"http://host.containers.internal:{mock_service_port}",
            "OPENHOST_APP_TOKEN": "test-token",
        },
    ) as s:
        yield s
