#!/usr/bin/env python3
"""Public evidence adapter for exploratory retail-environment comparisons.

No cohort selections, commercial inputs or scoring weights belong here.
Unlisted features stay unknown, including in captured directories.
"""
import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

try:
    from .place_metric_evidence import merge_place_metrics
    from .environment_coverage import label_coverage
except ImportError:
    from place_metric_evidence import merge_place_metrics
    from environment_coverage import label_coverage

ROOT = Path(__file__).resolve().parents[1]


def key(value):
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', ' ', value.lower().replace('&', ' and ')).strip()


CATEGORIES = {
    'Supermarket anchor': ['Supermarkets', 'Grocery and fresh food'],
    'Premium grocery': ['Grocery and fresh food'],
    'Activewear': ['Fashion and accessories'],
    'Contemporary fashion': ['Fashion and accessories'],
    'Premium fashion': ['Fashion and accessories'],
    'Youth fashion': ['Fashion and accessories'],
    'Luxury': ['Fashion and accessories'],
    'Hospitality': ['Food and dining'],
    'Design and lifestyle': ['Home and lifestyle'],
    'Department-store anchor': ['Department stores'],
}


def place_address(place, profile):
    """Expose supported display addresses without promoting a tenant unit."""
    address = profile.get('display_address') or place.get('address', '')
    source = profile.get('extent_evidence', {}) if profile.get('display_address') else place.get('address_evidence', {})
    held = bool(re.search(r'\b(shop|tenancy|unit|kiosk|level)\b', address, re.I))
    locality = place.get('locality') or place.get('suburb')
    if (held or not address) and place.get('location_setting') == 'High Street' and place.get('name') and locality:
        # A named corridor is not represented by one tenant's building address.
        # Reuse accepted identity fields without manufacturing address verification.
        reference = ', '.join(dict.fromkeys(str(v).strip() for v in
                              (place['name'], locality, place.get('state')) if v))
        basis = ('Named-street reference from the existing canonical street and locality; '
                 'not a building address, surveyed boundary or verified entrance. '
                 'Original business addresses remain on store records.')
        return {
            'address': reference,
            'address_note': basis,
            'address_evidence': {
                'source_url': place.get('source_url') or '',
                'source_date': None,
                'record_date': place.get('source_date') or '',
                'checked_at': '',
                'basis': basis,
            },
        }
    return {
        'address': '' if held else address,
        'address_note': 'Place address not independently sourced; tenant-unit address withheld.' if held else '',
        'address_evidence': ({
            'source_url': source.get('source_url') or place.get('source_url') or '',
            'source_date': source.get('source_date'),
            'record_date': source.get('record_date', '') if source else place.get('source_date') or '',
            'checked_at': source.get('checked_at') or '',
            'basis': source.get('basis') or ('Supported destination-profile address' if source else 'Existing place record; address-specific verification not recorded'),
        } if address and not held else {}),
    }


def build(data=ROOT / 'data'):
    read = lambda f: json.loads((data / f).read_text())
    places = read('retail_places.json')['places']
    properties = read('property_intelligence.json')['property_summaries']
    profiles = {r['place_id']: r for r in read('destination_profiles.json')['profiles']}
    directory = read('destination_directory.json')['records']
    tenants = read('place_tenants.json')['memberships']
    additions = read('retail_environment_evidence.json')
    stores = {r['store_id']: r for r in csv.DictReader((data / 'optical_stores.csv').open())}
    certs = {r['store_id']: r for r in csv.DictReader((data / 'store_certification.csv').open())}
    memberships = list(csv.DictReader((data / 'store_place_memberships.csv').open()))
    facts = defaultdict(list)
    held = defaultdict(list)
    optical = defaultdict(dict)
    catalogue = {}

    def add(pid, name, categories, source_id, url, observed, basis, source_date=None, address=''):
        if not name or not url or not observed:
            raise ValueError(f'Unattributed retail evidence: {source_id}')
        ids = [('brand:' + key(name), name, 'Retailer')]
        for cat in categories:
            if cat == 'Unclassified directory listing':
                continue
            ids.extend(('category:' + key(c), c, 'Category') for c in {cat, *CATEGORIES.get(cat, [])})
        for fid, label, kind in ids:
            catalogue[fid] = {'id': fid, 'label': label, 'kind': kind}
        facts[pid].append({'name': name, 'features': sorted(set(x[0] for x in ids)),
                           'source_id': source_id, 'source_url': url, 'observed_at': observed,
                           'source_date': source_date, 'scope_basis': basis, 'address': address})

    place_by_id = {p['place_id']: p for p in places}
    for r in tenants:
        if r['category'] == 'Optical' or r.get('status') != 'Active':
            continue
        p = place_by_id[r['place_id']]
        # Precinct branding alone cannot prove a named-street boundary.
        if p['location_setting'] == 'High Street' and 'Street' not in r.get('selection_basis', '').replace('street', 'Street'):
            held[p['place_id']].append(r['membership_id'])
            continue
        if p['location_setting'] == 'High Street' and r.get('source_type') == 'Official precinct directory':
            held[p['place_id']].append(r['membership_id'])
            continue
        add(r['place_id'], r['tenant_name'], [r['category']], r['membership_id'], r['source_url'], r['verified_at'], r['selection_basis'], r.get('source_date'))
    for r in directory:
        if r['scope_status'] != 'In declared research scope' or r['listing_status'] != 'Directory listed; trading not independently checked' or r['role'] == 'Optical':
            continue
        add(r['place_id'], r['display_name'], r['categories'], r['record_id'], r['source_url'], r['observed_at'], r['scope_basis'], r.get('source_effective_date'), r.get('source_address', ''))
    for r in additions['observations']:
        if r['place_id'] not in place_by_id:
            raise ValueError('Evidence refers to unknown canonical place')
        add(r['place_id'], r['name'], r['categories'], r['source_id'], r['source_url'], r['observed_at'], r['scope_basis'], r.get('source_date'), r.get('address', ''))
    for r in memberships:
        sid = r['store_id']
        s, c = stores.get(sid), certs.get(sid, {})
        if not s or r['review_status'] != 'Accepted' or c.get('usable_for_network') != 'true' or s['status'] == 'Closed':
            continue
        optical[r['place_id']][sid] = {'store_id': sid, 'name': s['name'], 'operator': s['name'] if s['retailer'] == 'Independent / Other optical' else s['retailer'],
            'retailer': s['retailer'], 'source_url': r['evidence_url'], 'observed_at': r['verified_at'], 'stale': c.get('current_source') != 'true'}
    output = []
    for p in places:
        pid = p['place_id']; prop = properties.get(pid, {}); profile = profiles.get(pid, {})
        rows = facts[pid]; outlets = list(optical[pid].values())
        feature_map = defaultdict(list)
        for r in rows:
            for fid in r['features']:
                feature_map[fid].append(r['source_id'])
        for outlet in outlets:
            fid = 'operator:' + key(outlet['operator'])
            catalogue[fid] = {'id': fid, 'label': outlet['operator'], 'kind': 'Optical operator'}
            feature_map[fid].append('optical:' + outlet['store_id'])
        corridor = p['location_setting'] == 'High Street'
        scope = (f"Named-street study: {p['name']}, {p.get('locality') or p.get('suburb') or p.get('state')}. Only explicit street/frontage addresses or accepted optical memberships; side streets and wider precinct listings excluded. No radius or walking catchment implied."
                 if corridor else 'Accepted canonical centre membership / official centre directory. Nearby stores are excluded; map point is not a property boundary.')
        measures = merge_place_metrics(p, prop)
        area = measures.get('gla_sqm')
        positioning = sorted({c for r in rows for c in ('Value', 'Mainstream', 'Contemporary fashion', 'Premium fashion', 'Luxury') if 'category:' + key(c) in r['features']})
        purposes = sorted({c for r in rows for c in ('Supermarkets', 'Department stores', 'Fashion and accessories', 'Food and dining', 'Services', 'Entertainment', 'Health and wellbeing') if 'category:' + key(c) in r['features']})
        output.append({
            'place_id': pid, 'name': p['name'], 'aliases': p.get('aliases', []), 'country': p['country'], 'state': p.get('state', ''),
            'locality': p.get('locality') or p.get('suburb') or '', 'format': p['location_setting'],
            'place_type': p['place_type'],
            'latitude': p['latitude'], 'longitude': p['longitude'], 'scope': scope,
            **({'identity_sources': p['sources'], 'identity_reviewed_at': p['reviewed_at'],
                'coordinate_source_url': p.get('coordinate_source_url')} if p.get('sources') else {}),
            **place_address(p, profile),
            'coordinate_method': p.get('coordinate_method', ''),
            'coordinate_confidence': p.get('coordinate_confidence', ''),
            'coordinate_reason': p.get('coordinate_reason', ''),
            'coordinate_source_url': p.get('coordinate_source_url', ''),
            'coordinate_verified_at': p.get('coordinate_verified_at', ''),
            'coordinate_reference_store_id': p.get('coordinate_reference_store_id', ''),
            'features': dict(feature_map), 'absent_features': {}, 'observations': rows,
            'coverage': {'status': 'Partial' if rows else 'Not yet sourced', 'observations': len(rows), 'distinct_names': len({key(r['name']) for r in rows}),
                         'held_scope_records': held[pid], 'complete': False, 'observed_dates': sorted({r['observed_at'] for r in rows})},
            'optical': outlets, 'bn_presence': 'present' if any(r['retailer'] == 'Bailey Nelson' for r in outlets) else 'not_recorded',
            'other_optical_presence': 'present' if any(r['retailer'] != 'Bailey Nelson' for r in outlets) else 'not_recorded',
            'scale': {'class': prop.get('centre_class', 'Unknown'), 'evidence': prop.get('centre_class_evidence', {}), 'gla_sqm': area, 'tenancy_count': measures.get('tenancy_count')},
            'metrics': {'annual_visits': measures.get('annual_visits'), 'trade_area_population': measures.get('trade_area_population'),
                        'source_url': p.get('source_url'), 'record_date': p.get('source_date'), 'reference_period': None},
            'metric_evidence': measures['metric_evidence'], 'metric_observations': measures['metric_observations'],
            'metric_conflicts': measures['metric_conflicts'],
            'shopping_purpose': purposes, 'positioning': positioning, 'local_importance': 'Not yet established relative to nearby alternatives',
            'confidence': 'Partial public evidence; no commercial-success confidence inferred',
            'market': prop.get('market', {}), 'access': profile.get('access', []), 'property_facts': profile.get('property_facts', []),
            'owner_names': prop.get('owner_names', []), 'manager_names': prop.get('manager_names', []),
            'summary': profile.get('decision_use') or (f"{p['name']} is a {p['location_setting'].lower()} in {p.get('locality') or p.get('state') or p['country']}. " + (f"Recorded retail evidence includes {', '.join(purposes[:3]).lower()}." if purposes else 'Its wider retail mix is not yet sourced.')),
            'limitations': ['Unlisted does not mean absent. Research is selective and may favour fashion/beauty.', 'Current observations do not establish historical retail mix.', 'Counts are recorded listings, not occupied-tenancy or floor-area shares.', *profile.get('limitations', [])],
        })
    payload = {'metadata': {'schema_version': 1, 'scope_rule': 'Named street within canonical locality for high streets; canonical property for centres.',
                'build_is_not_source_refresh': True, 'coverage_is_not_match_strength': True, 'absence_policy': 'Only explicit reviewed absence evidence; directory omissions remain unknown.'},
               'features': sorted(catalogue.values(), key=lambda r: (r['kind'], r['label'].casefold())), 'places': output}
    from public_directory_evidence import apply as apply_public_directories
    payload = apply_public_directories(payload, data)
    payload = label_coverage(payload)
    (data / 'retail_environments.json').write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n')
    return payload


if __name__ == '__main__':
    result = build()
    print(f"Built environments for {len(result['places'])} canonical places; no commercial cohorts loaded.")
