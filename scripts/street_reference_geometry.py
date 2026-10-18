"""Road-derived display points only; never evidence of tenant membership."""
import math
import re
import xml.etree.ElementTree as ET
from functools import lru_cache

ROAD_TYPES = {'motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'unclassified', 'residential', 'living_street', 'pedestrian', 'service'}


def normalise_road_name(name):
    return re.sub(r'\s+', ' ', str(name).strip()).casefold()


@lru_cache(maxsize=2)
def _named_segments(xml_bytes):
    """Index one retained response once, including original source identifiers."""
    root = ET.fromstring(xml_bytes)
    nodes = {n.get('id'): n for n in root.findall('node')}
    index = {}
    for way in root.findall('way'):
        tags = {t.get('k'): t.get('v') for t in way.findall('tag')}
        if not tags.get('name') or tags.get('highway') not in ROAD_TYPES | {'footway'}:
            continue
        refs = [n.get('ref') for n in way.findall('nd')]
        for first, second in zip(refs, refs[1:]):
            if first not in nodes or second not in nodes:
                continue
            a, b = nodes[first], nodes[second]
            alon, alat, blon, blat = map(float, (a.get('lon'), a.get('lat'), b.get('lon'), b.get('lat')))
            index.setdefault(normalise_road_name(tags['name']), []).append({
                'way_id': way.get('id'), 'way_version': way.get('version'),
                'way_timestamp': way.get('timestamp'), 'road_name': tags['name'], 'highway': tags['highway'],
                'source_tags': {k: tags[k] for k in ('indoor', 'level', 'tunnel', 'access', 'foot', 'covered', 'service') if k in tags},
                'node_ids': [first, second], 'segment': [[alon, alat], [blon, blat]]})
    return index


def nearest_named_road(xml_bytes, name, latitude, longitude, max_distance_m=250,
                       allow_named_pedestrian_paths=False):
    """Return the nearest point on an exact-name mapped road, or an explicit gap.

    The caller must first establish the named locality and study area. A local
    road match cannot validate that identity or establish the study boundary.
    Returned dictionaries are fresh, so review annotations cannot alter the cache.
    """
    xscale = 111320 * math.cos(math.radians(latitude))
    yscale = 111320
    candidates = []
    for source in _named_segments(xml_bytes).get(normalise_road_name(name), []):
        if (source['source_tags'].get('indoor') == 'yes'
                or source['source_tags'].get('tunnel') == 'building_passage'):
            continue
        if source['highway'] == 'footway' and not allow_named_pedestrian_paths:
            continue
        (alon, alat), (blon, blat) = source['segment']
        ax, ay = (alon-longitude)*xscale, (alat-latitude)*yscale
        dx, dy = (blon-alon)*xscale, (blat-alat)*yscale
        length2 = dx*dx + dy*dy
        if not length2:
            continue
        t = max(0, min(1, -(ax*dx+ay*dy)/length2))
        distance = math.hypot(ax+t*dx, ay+t*dy)
        candidates.append({**source, 'source_tags': dict(source['source_tags']), 'node_ids': list(source['node_ids']),
            'segment': [list(p) for p in source['segment']],
            'latitude': alat+t*(blat-alat), 'longitude': alon+t*(blon-alon),
            'displacement_m': distance, 'fraction': t})
    if not candidates:
        return {'status': 'unresolved', 'reason': 'No exact-name eligible road segment in bounded source response'}
    result = min(candidates, key=lambda x: (x['displacement_m'], x['way_id'], x['node_ids']))
    if result['displacement_m'] > max_distance_m:
        return {'status': 'unresolved', 'reason': 'Named road exceeds review distance; no automatic relocation', 'nearest_distance_m': result['displacement_m']}
    return {'status': 'matched', **result}
