import httpx
from openhost_test_harness import OpenhostStack
from playwright.sync_api import Page
from playwright.sync_api import expect


def test_health_endpoint(stack: OpenhostStack) -> None:
    response = httpx.get(f"{stack.app_url}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_sync_fetches_routes_and_skips_routeless(stack: OpenhostStack) -> None:
    # Drive the incremental sync to completion.
    result = {"pending": 1}
    for _ in range(10):
        result = httpx.post(f"{stack.url}/api/sync").json()
        if result["pending"] <= 0:
            break
    assert result["total"] == 2  # the two mock workouts
    assert result["cached"] == 2  # both cached (the routeless one too, so it isn't refetched)

    # Only the workout with a GPS route is returned for drawing.
    routes = httpx.get(f"{stack.url}/api/routes").json()
    assert routes["count"] == 1
    track = routes["tracks"][0]
    assert track["workout_type"] == "running"
    assert len(track["points"]) >= 2
    # Points are in SF.
    lat, lon = track["points"][0]
    assert 37 < lat < 38 and -123 < lon < -122


def test_map_page_renders(stack: OpenhostStack, page: Page) -> None:
    page.goto(stack.url)
    expect(page.get_by_role("heading", name="Wanderer")).to_be_visible()
    # Leaflet adds the "leaflet-container" class to #map once initialized.
    # (We don't assert on tiles — those come from an external CDN.)
    expect(page.locator("#map.leaflet-container")).to_be_visible(timeout=20000)
