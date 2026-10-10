#!/usr/bin/env python3
"""Build compact destination summaries and reproducible directory comparisons.

Directory listings never admit optical stores or establish tenancy denominators.
The full public research database is separate from the small browser payload.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
DIRECTORY = DATA / 'destination_directory.json'
SUMMARY = DATA / 'destination_research.json'
COMPARISONS = DATA / 'destination_directory_comparisons.json'
SCOPE_ACCEPTED = 'In declared research scope'
LISTED = 'Directory listed; trading not independently checked'


def name_key(value):
    """Text comparison only: does not assert common ownership or exact tenancy."""
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', ' ', value.lower().replace('&', ' and ')).strip()


def usable_directory_row(row):
    return (row['scope_status'] == SCOPE_ACCEPTED
            and row['listing_status'] == LISTED
            and row['role'] != 'Optical')


def validate_records(payload, places, store_ids):
    seen = set()
    for row in payload['records']:
        rid = row['record_id']
        if rid in seen or not row['source_record_id']:
            raise ValueError(f'Duplicate or missing source identity: {rid}')
        seen.add(rid)
        if row['place_id'] not in places:
            raise ValueError(f'Unknown destination: {rid}')
        if not row['source_url'].startswith('https://') or not row['source_name'].strip():
            raise ValueError(f'Missing public source/name: {rid}')
        if not row['categories'] or not isinstance(row['source_categories'], list):
            raise ValueError(f'Missing declared category treatment: {rid}')
        if row['listing_status'] not in {LISTED, 'Coming soon (directory label)'}:
            raise ValueError(f'Undeclared trading-status inference: {rid}')
        if row['scope_status'] not in {SCOPE_ACCEPTED, 'Review required', 'Outside declared street or unresolved address'}:
            raise ValueError(f'Undeclared membership inference: {rid}')
        sid = row.get('canonical_optical_store_id')
        if sid and sid not in store_ids:
            raise ValueError(f'Unknown canonical optical link: {rid}')
        if row['role'] == 'Optical' and not sid:
            raise ValueError(f'Optical role needs an explicit reviewed identity link: {rid}')
        if places[row['place_id']]['location_setting'] == 'High Street' and row['scope_status'] == SCOPE_ACCEPTED:
            address = row['source_address']
            if not re.search(r'\bJetty Road\b', address, re.I) or not re.search(r'\bGlenelg\b', address, re.I):
                raise ValueError(f'Pilot street membership lacks explicit address evidence: {rid}')


def make_summaries(payload, places):
    summaries = []
    for pid in sorted({r['place_id'] for r in payload['records']}):
        rows = [r for r in payload['records'] if r['place_id'] == pid]
        usable = [r for r in rows if usable_directory_row(r)]
        cat_counts = Counter(c for r in usable for c in r['categories'])
        corridor = places[pid]['location_setting'] == 'High Street'
        summaries.append({
            'place_id': pid, 'name': places[pid]['name'],
            'research_status': 'Directory captured; limitations retained',
            'observed_at': max(r['observed_at'] for r in rows),
            'source_effective_date': None,
            'source_listing_count': len(rows),
            'in_scope_non_optical_listings': len(usable),
            'coming_soon_listings': sum(r['listing_status'] == 'Coming soon (directory label)' for r in rows),
            'held_scope_listings': sum(r['scope_status'] == 'Review required' for r in rows),
            'outside_or_unresolved_address_listings': sum(r['scope_status'] == 'Outside declared street or unresolved address' for r in rows),
            'rows_with_exceptions': sum(bool(r['exceptions']) for r in rows),
            'unclassified_listings': sum('Unclassified directory listing' in r['categories'] for r in usable),
            'categories': [{'name': c, 'listing_count': n, 'examples': [{'name': r['display_name'], 'source_url': r['source_url']} for r in sorted((r for r in usable if c in r['categories']), key=lambda r:r['display_name'].casefold())[:3]]} for c, n in sorted(cat_counts.items(), key=lambda p: (-p[1], p[0]))],
            'scope': ('Published district directory, restricted for comparison to explicit Jetty Road/Glenelg addresses. Address conflicts and unclear identities remain held.' if corridor else 'Published official centre directory. Listings include services and may include internal outlets or concessions.'),
            'coverage_limitations': [
                'Directory-listed businesses have not all been independently checked for current trading.',
                'Listing counts are not unique brands, occupied tenancies, frontage exposure or floor-area shares.',
                'A listing may have more than one category; category counts must not be added as a total.',
                'Source categories may be broad or inconsistent; unclassified and combined categories remain visible.',
                'Optical competition uses the separately validated census, including accepted concessions missing from directories.',
            ],
            'tenancy_count_share': None, 'floor_area_share': None,
            'share_unavailable_reason': 'No compatible occupied-tenancy or category-floor-area denominator.',
            'source_urls': sorted(set('https://www.jettyroadglenelg.com.au/directory/stores-services' if corridor else ('https://edsquare.shopping/stores/' if 'ed-square' in pid else 'https://www.karrinyupcentre.com.au/stores-services') for _ in rows)),
        })
    return summaries


def compare_directories(records, places):
    indexes = {}
    for row in records:
        if usable_directory_row(row):
            indexes.setdefault(row['place_id'], {}).setdefault(name_key(row['display_name']), []).append(row)
    pairs = []
    for left, right in combinations(sorted(indexes), 2):
        shared = sorted(set(indexes[left]) & set(indexes[right]))
        pairs.append({'left_place_id': left, 'right_place_id': right,
                      'left_name': places[left]['name'], 'right_name': places[right]['name'],
                      'shared_normalized_names': [
                          {'name_key': key, 'left_records': [r['record_id'] for r in indexes[left][key]],
                           'right_records': [r['record_id'] for r in indexes[right][key]]} for key in shared],
                      'method': 'Exact normalized listing-name intersection; punctuation/case/accents and ampersand normalized. Branch-name variants are not silently merged.',
                      'interpretation': 'A lower-bound name overlap within declared directory scope, not an attractiveness score, predictive benchmark or proof of common tenancy economics.'})
    return pairs


def search_directory(records, query):
    q = name_key(query)
    return [r for r in records if usable_directory_row(r)
            and q in name_key(' '.join([r['display_name'], *r['categories'], *r['source_categories']]))]


def build(data=DATA):
    source_path = data / DIRECTORY.name
    if not source_path.exists():
        return
    payload = json.loads(source_path.read_text())
    places = {p['place_id']: p for p in json.loads((data/'retail_places.json').read_text())['places']}
    with (data/'optical_stores.csv').open() as f:
        store_ids = {r['store_id'] for r in csv.DictReader(f)}
    validate_records(payload, places, store_ids)
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    metadata = {'schema_version': 1, 'directory_sha256': digest,
                'census_sha256': hashlib.sha256((data/'optical_stores.csv').read_bytes()).hexdigest(),
                'purpose': 'Public research summaries; no census admissions or score changes.'}
    (data/SUMMARY.name).write_text(json.dumps({'metadata': metadata, 'profiles': make_summaries(payload, places)}, ensure_ascii=False, indent=2)+'\n')
    (data/COMPARISONS.name).write_text(json.dumps({'metadata': metadata, 'comparisons': compare_directories(payload['records'], places)}, ensure_ascii=False, indent=2)+'\n')
    try:
        from .destination_profiles import build_profiles
    except ImportError:
        from destination_profiles import build_profiles
    build_profiles(data, make_summaries(payload, places))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--query', help='Find eligible directory listings by name or source/normalized category')
    parser.add_argument('--export-csv', type=Path, help='Export all source records, including holds and out-of-scope rows')
    args = parser.parse_args()
    build()
    payload = json.loads(DIRECTORY.read_text())
    if args.query:
        print(json.dumps(search_directory(payload['records'], args.query), ensure_ascii=False, indent=2))
    if args.export_csv:
        rows = [{k: ' | '.join(map(str, v)) if isinstance(v, list) else v for k, v in r.items()} for r in payload['records']]
        fields = list(dict.fromkeys(k for r in rows for k in r))
        with args.export_csv.open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    if not args.query:
        print(f'Destination research built from {len(payload["records"])} source records.')


if __name__ == '__main__':
    main()
