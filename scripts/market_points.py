"""Public, coordinate-bound SA2 evidence; display polygons are only a fallback."""
import json
from functools import lru_cache
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / 'data/market_point_links.json'


def point_key(point):
    return f"{float(point['latitude']):.7f},{float(point['longitude']):.7f}"


@lru_cache(maxsize=1)
def load_point_links():
    return json.loads(PATH.read_text()).get('links', {}) if PATH.exists() else {}


def authoritative_link(point, links=None):
    return (load_point_links() if links is None else links).get(point_key(point))


def in_ring(x, y, ring):
    inside = False
    previous = ring[-1]
    for current in ring:
        x1, y1 = previous
        x2, y2 = current
        if (y1 > y) != (y2 > y) and x < (x2-x1)*(y-y1)/(y2-y1)+x1:
            inside = not inside
        previous = current
    return inside


def contains(point, geometry):
    polygons = geometry.get('coordinates', [])
    if geometry.get('type') == 'Polygon':
        polygons = [polygons]
    x, y = float(point['longitude']), float(point['latitude'])
    return any(poly and in_ring(x, y, poly[0]) and not any(in_ring(x, y, hole) for hole in poly[1:]) for poly in polygons)


def resolve_market(point, features, links=None):
    if point.get('country', 'Australia') != 'Australia':
        return None, 'Not available'
    verified = authoritative_link(point, links)
    if verified is not None:
        if verified.get('match_status') != 'Unique':
            return None, 'Authoritative boundary match unresolved'
        props = next((f['properties'] for f in features if f['properties'].get('sa2_code') == verified.get('sa2_code')), None)
        return props, 'ABS authoritative point query' if props else 'Authoritative code missing from demographic layer'
    matches = [f['properties'] for f in features if contains(point, f.get('geometry') or {})]
    return (matches[0], 'Generalised display polygon') if len(matches) == 1 else (None, 'Display boundary match unresolved')
