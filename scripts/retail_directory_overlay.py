"""Apply attributed directory captures without reading commercial selections.

Used by the authenticated companion. No captured dataset is written by this module.
Complete means publisher-directory extraction, never verified trading or occupancy.
"""
import copy
from collections import defaultdict
try:
    from .build_retail_environments import key
    from . import public_directory_schema as schema
except ImportError:
    from build_retail_environments import key
    import public_directory_schema as schema


def apply_captures(public, captures):
    output = copy.deepcopy(public)
    places = {p['place_id']: p for p in output['places']}
    catalogue = {f['id']: f for f in output['features']}
    seen = set()
    for raw_capture in captures:
        capture = schema.capture(raw_capture)
        if capture['place_id'] in seen or capture['place_id'] not in places:
            raise ValueError('Duplicate or unknown canonical capture place')
        seen.add(capture['place_id'])
        p = places[capture['place_id']]
        actual_centre = schema.canonical_centre(p)
        centre_scope = actual_centre and capture['format_scope'] == 'canonical centre'
        records = capture['records']
        total = capture.get('source_total')
        complete = capture.get('directory_complete', False)
        source_count = capture.get('source_record_count', len(records))
        anonymous_count = capture.get('anonymous_record_count', 0)
        features = defaultdict(list)
        observations = []
        for r in records:
            if r.get('scope_status') != 'included' or r.get('listing_status') != 'listed':
                continue
            fids = []
            # Keep optical listing names, but do not let the focal optical store
            # manufacture a general health/fashion co-tenant observation.
            categories = [] if r.get('role') == 'Optical' else r['categories']
            source_brand = r.get('source_brand')
            brand_features = [('brand:' + key(source_brand), source_brand, 'Retailer')] if source_brand and key(source_brand) != key(r['name']) else []
            for fid, label, kind in [('brand:' + key(r['name']), r['name'], 'Retailer'),
                                      *brand_features,
                                      *[('category:' + key(c), c, 'Category') for c in categories]]:
                catalogue[fid] = {'id': fid, 'label': label, 'kind': kind}
                fids.append(fid)
                features[fid].append(r['source_id'])
            observation = schema.record(r)
            observation['features'] = sorted(set(fids))
            observations.append(observation)
        # Optical census membership is independent of the wider tenant directory.
        for fid, refs in p['features'].items():
            if fid.startswith('operator:'):
                features[fid] = refs
        absent = {}
        for review in capture.get('absence_reviews', []):
            fid = review['feature_id']
            if not complete or not centre_scope:
                raise ValueError('Scoped absence requires an audited complete centre directory')
            if fid in features:
                raise ValueError('Contradictory absence review')
            absent[fid] = [schema.absence_review(review)]
            catalogue[fid] = {'id': fid, 'label': review['label'], 'kind': review['kind']}
        p['features'] = dict(features)
        p['absent_features'] = absent
        p['observations'] = observations
        p['scope'] = capture['scope']
        p['coverage'] = {
            'status': ('Complete directory capture' if centre_scope else 'Complete publisher capture; partial place coverage') if complete else 'Partial directory / scope coverage',
            'absence_eligible': complete and centre_scope,
            'complete': False, 'directory_complete': complete,
            'captured_listings': source_count, 'source_total': total,
            'anonymous_records': anonymous_count,
            'usable_listings': len(observations), 'observations': len(observations),
            'distinct_names': len({key(r['name']) for r in observations}),
            'held_scope_records': [r['source_id'] for r in records if r.get('scope_status') != 'included'],
            'non_present_listings': [{'name': r['name'], 'status': r['listing_status']} for r in records if r.get('listing_status') != 'listed'],
            'observed_dates': sorted({r['observed_at'] for r in records}),
            'format_scope': capture['format_scope'],
            'directory_note': capture['limitations'], 'source_urls': capture['source_urls'],
            'capture_method': capture['capture_method'], 'trading_verified': False,
            'ownership_coverage': 'Unknown except explicit source statements; no chain-name heuristic',
        }
        p['directory_records'] = [schema.record(r) for r in records]
        p['absence_reviews'] = [schema.absence_review(r) for r in capture.get('absence_reviews', [])]
        cats = {c for r in observations if r.get('role') != 'Optical' for c in r['categories']}
        p['shopping_purpose'] = sorted(cats & {'Supermarkets', 'Grocery and fresh food', 'Food and dining', 'Services', 'Health and wellbeing', 'Entertainment', 'Fashion and accessories', 'Department stores'})
        p['positioning'] = sorted(cats & {'Value', 'Mainstream', 'Contemporary fashion', 'Premium fashion', 'Luxury'})
        p['summary'] = f"{p['name']} is a {p['format'].lower()}. The captured sources document {len(observations)} in-scope listings; current trading is not independently verified."
        p['limitations'] = [capture['limitations'], 'Current co-tenants may differ from the unknown reporting-period mix.',
                             'Listing counts are not distinct occupied tenancies, floor-area shares or customer catchments.',
                             'Absence applies only to the reviewed feature and captured directory scope.']
    output['features'] = sorted(catalogue.values(), key=lambda f: (f['kind'], f['label'].casefold()))
    return output
