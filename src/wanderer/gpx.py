import xml.etree.ElementTree as ET

# A single GPS fix: (latitude, longitude) in decimal degrees.
Point = tuple[float, float]


def parse_gpx_points(gpx: str) -> list[Point]:
    """Extract the ordered (lat, lon) track points from a GPX 1.1 document.

    Namespaces vary between exporters, so we match on the local element name
    (``trkpt``) rather than a fully-qualified tag.
    """
    try:
        root = ET.fromstring(gpx)
    except ET.ParseError:
        return []
    points: list[Point] = []
    for el in root.iter():
        if el.tag.rsplit("}", 1)[-1] != "trkpt":
            continue
        lat, lon = el.get("lat"), el.get("lon")
        if lat is None or lon is None:
            continue
        points.append((float(lat), float(lon)))
    return points


def _rdp(points: list[Point], epsilon: float) -> list[Point]:
    """Ramer–Douglas–Peucker simplification, iterative to avoid recursion limits
    on long tracks. ``epsilon`` is the max allowed deviation in degrees."""
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        start, end = stack.pop()
        ax, ay = points[start]
        bx, by = points[end]
        dx, dy = bx - ax, by - ay
        seg_sq = dx * dx + dy * dy
        max_dist = -1.0
        index = start
        for i in range(start + 1, end):
            px, py = points[i]
            if seg_sq == 0:
                dist = ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
            else:
                # Perpendicular distance from point to the segment a–b.
                dist = abs(dy * px - dx * py + bx * ay - by * ax) / (seg_sq**0.5)
            if dist > max_dist:
                max_dist, index = dist, i
        if max_dist > epsilon:
            keep[index] = True
            stack.append((start, index))
            stack.append((index, end))
    return [p for p, k in zip(points, keep, strict=True) if k]


def downsample(points: list[Point], epsilon: float = 0.00005, max_points: int = 1500) -> list[Point]:
    """Simplify a track and cap its size, rounding coordinates to ~1m precision
    to keep the payload small. ``epsilon`` defaults to roughly 5m."""
    simplified = _rdp(points, epsilon)
    if len(simplified) > max_points:
        stride = len(simplified) // max_points + 1
        simplified = simplified[::stride]
    return [(round(lat, 5), round(lon, 5)) for lat, lon in simplified]
