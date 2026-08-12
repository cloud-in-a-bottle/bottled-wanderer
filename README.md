# Wanderer

A Cloud in a Bottle app that plots **every GPS route from your workouts on a single map** —
so you can see all the places you've ever been. It opens zoomed into San Francisco.

Wanderer is a pure consumer of the
[health-data service](https://github.com/imbue-openhost/health-data-service-spec):
it pulls workouts from whatever provider apps you have installed (e.g.
`apple-health`), extracts each workout's GPS route, downsamples it, and draws
them all as overlapping polylines coloured by activity type.

## How it works

- `/api/sync` (POST) pulls detail for the next batch of not-yet-seen workouts,
  parses the GPX route, simplifies it with Ramer–Douglas–Peucker, and caches the
  result in the `routes` SQLite DB. The frontend calls it repeatedly so the map
  fills in progressively; once a workout is cached it's never refetched (even
  routeless indoor sessions are recorded so they're skipped).
- `/api/routes` (GET) returns every cached track that has GPS points.
- `/` serves the Leaflet map.

## Development

```bash
just setup   # install deps, pre-commit hooks, and the playwright chromium browser
just run     # run locally on http://localhost:8080
just test    # build + run under podman, fronted by a mock health-data service
just check   # lint, format, typecheck
```

`just test` uses `openhost-test-harness`, which builds the Dockerfile and runs
the app under **podman** (so podman must be running) fronted by a mock Cloud in a Bottle
router. `tests/conftest.py` stands up a fake health-data provider.

## Deploying

It consumes the health-data service, so it needs the `full_access` grant at
install time:

```bash
oh app deploy https://github.com/imbue-openhost/bottled-wanderer \
  --name wanderer --grant-permissions-v2 --instance <name> --wait
```

Subsequent updates: `oh app reload wanderer --update --wait --instance <name>`.
