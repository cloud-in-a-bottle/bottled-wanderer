from wanderer.gpx import downsample
from wanderer.gpx import parse_gpx_points

_GPX = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>'
    '<trkpt lat="37.7694" lon="-122.4862"><ele>10</ele></trkpt>'
    '<trkpt lat="37.7701" lon="-122.4790"></trkpt>'
    '<trkpt lat="37.7715" lon="-122.4700"></trkpt>'
    "</trkseg></trk></gpx>"
)


def test_parse_extracts_points_in_order() -> None:
    points = parse_gpx_points(_GPX)
    assert points == [(37.7694, -122.4862), (37.7701, -122.4790), (37.7715, -122.4700)]


def test_parse_handles_garbage() -> None:
    assert parse_gpx_points("not xml") == []
    assert parse_gpx_points("<gpx></gpx>") == []


def test_downsample_drops_collinear_points() -> None:
    # A dead-straight line of many points should reduce to its endpoints.
    line = [(37.0 + i * 0.001, -122.0) for i in range(50)]
    out = downsample(line)
    assert out[0] == (37.0, -122.0)
    assert out[-1] == (37.049, -122.0)
    assert len(out) == 2


def test_downsample_keeps_corners_and_caps_size() -> None:
    # A zig-zag's corners must survive; total stays under the cap.
    zig = []
    for i in range(5000):
        zig.append((37.0 + (i % 2) * 0.01, -122.0 + i * 0.0005))
    out = downsample(zig, max_points=1500)
    assert 2 < len(out) <= 1500
    assert all(len(p) == 2 for p in out)


def test_downsample_rounds_coordinates() -> None:
    out = downsample([(37.123456789, -122.987654321), (37.2, -122.0)])
    assert out[0] == (37.12346, -122.98765)
