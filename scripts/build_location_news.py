"""Build append-only public news history from existing signals and reviewed news records."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
try:
    from .location_news_schema import document
except ImportError:
    from location_news_schema import document

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ALIASES = {
    'development-westfield-bondi-level-6': 'project-bondi-junction-level6',
    'development-westfield-penrith-entertainment': 'project-penrith-entertainment',
    'development-westfield-warringah-housing': 'project-warringah-housing-concept',
    'development-westfield-eastgardens-housing': 'project-eastgardens-housing-proposal',
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def revision_id(event_id, version):
    # Observation timestamps do not make a new story/revision by themselves.
    return event_id + '-' + digest({k: v for k, v in version.items() if k not in ('recorded_at', 'revision_id')})[:16]


def merge_events(rows):
    result, identity = {}, {}
    for row in rows:
        identities = [row['event_id'], *row['aliases']]
        matches = {identity[x] for x in identities if x in identity}
        if len(matches) > 1:
            raise ValueError('Conflicting project aliases require review')
        key = next(iter(matches), row['event_id'])
        if key not in result:
            result[key] = {**row, 'aliases': list(row['aliases']), 'relations': [], 'versions': []}
        target = result[key]
        target['kind'], target['scope'] = row['kind'], row['scope']
        target['parent_event_id'] = row['parent_event_id']
        target['aliases'] = sorted(set(target['aliases'] + identities) - {key})
        for field in ('relations', 'versions'):
            known = {digest(x) if field == 'relations' else x['revision_id']: x for x in target[field]}
            for item in row[field]:
                item_key = digest(item) if field == 'relations' else item['revision_id']
                if item_key in known and field == 'versions':
                    a, b = known[item_key], item
                    if {k:v for k,v in a.items() if k != 'recorded_at'} != {k:v for k,v in b.items() if k != 'recorded_at'}:
                        raise ValueError('Revision ID reused for different evidence')
                elif item_key not in known:
                    target[field].append(item); known[item_key] = item
        for ident in identities:
            identity[ident] = key
    return sorted(result.values(), key=lambda e: e['event_id'])


def nearest_store(latitude, longitude, country, stores):
    """News relevance only; never writes or infers canonical membership."""
    if latitude is None or longitude is None or not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    candidates = []
    for store in stores:
        if store.get('country') != country or str(store.get('usable_for_network')).lower() != 'true':
            continue
        if store.get('status') == 'Closed':
            continue
        try:
            lat, lon = float(store['latitude']), float(store['longitude'])
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                continue
        except (ValueError, TypeError, KeyError):
            continue
        a,b = math.radians(latitude), math.radians(lat)
        h = math.sin((b-a)/2)**2 + math.cos(a)*math.cos(b)*math.sin(math.radians(lon-longitude)/2)**2
        distance = 6371 * 2 * math.asin(min(1, math.sqrt(h)))
        candidates.append((distance, store['store_id'], store))
    if not candidates:
        return None
    distance, _, store = min(candidates)
    return store, round(distance, 3)


def legacy_events(data):
    rows = json.loads((data / 'growth_development_signals.json').read_text())['signals']
    result = []
    for row in rows:
        eid = PROJECT_ALIASES.get(row['signal_id'], row['signal_id'])
        sid = 'source-' + digest(row['source_url'])[:12]
        published = row.get('published_at') or None
        if 'resido' in eid:
            published = '2024'  # Legacy Jan 1 was a year placeholder, not a publication date.
        v = dict(published_on=published, recorded_at=row['last_verified_at'],
                 date_basis='Retained public source date; year precision where the legacy date was a placeholder.',
                 title=row['title'], statements=[dict(text=row['summary'], kind='source_report', source_ids=[sid])],
                 sources=[dict(source_id=sid, url=row['source_url'], title=row['source_type'])],
                 timing=row.get('impact_horizon') or '', uncertainty='Retained project baseline; current completion has not been rechecked.', metrics=[])
        v['revision_id'] = revision_id(eid, v)
        result.append(dict(event_id=eid, aliases=[row['signal_id']] if eid != row['signal_id'] else [],
                           parent_event_id=None, kind='background', scope='location',
                           relations=[dict(kind='direct_place', entity_id=row['place_id'], label=row['place_name'],
                                           basis='Existing public project names this place.', source_urls=[row['source_url']], distance_km=None)], versions=[v]))
    return result


def build(data=None):
    data = Path(data or ROOT / 'data')
    curated = document(json.loads((data / 'location_news_records.json').read_text()))
    places = {x['place_id'] for x in json.loads((data / 'retail_places.json').read_text())['places']}
    stores = {x['store_id'] for x in csv.DictReader((data / 'optical_stores.csv').open())}
    result = document(dict(schema_version=1, document_type='location_news',
                           events=merge_events(legacy_events(data) + curated['events']), checks=curated['checks']), places, stores)
    (data / 'location_news.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--data', type=Path)
    print(f"Built {len(build(p.parse_args().data)['events'])} news histories")
