import attr

from .gpx import Point


@attr.s(auto_attribs=True, frozen=True)
class Track:
    """One workout's downsampled GPS route, ready to draw on the map.

    ``points`` is empty for a workout we've fetched but that had no GPS route
    (e.g. an indoor session) — we still cache it so we don't refetch it."""

    workout_id: str
    workout_type: str
    start: str
    points: list[Point]


@attr.s(auto_attribs=True, frozen=True)
class RoutesResponse:
    """Payload for the map: every cached track with GPS points."""

    count: int
    tracks: list[Track]


@attr.s(auto_attribs=True, frozen=True)
class SyncResult:
    """Outcome of one incremental sync pass."""

    fetched: int  # workouts whose detail we pulled this pass
    cached: int  # total workouts now in the cache
    pending: int  # workouts known but not yet fetched
    total: int  # total workouts the providers report
