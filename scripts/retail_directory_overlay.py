"""Apply attributed directory captures without reading commercial selections.

Used by the authenticated companion. No captured dataset is written by this module.
Complete means publisher-directory extraction, never verified trading or occupancy.
"""
import copy
from collections import defaultdict
try:
    from .build_retail_environments import key
except ImportError:
    from build_retail_environments import key


def apply_captures(public, captures):
    output = copy.deepcopy(public)
    places = {p['place_id']: p for p in output['places']}
    catalogue = {f['id']: f for f in output['features']}
    for capture in captures:
        p = places[capture['place_id']]
        records = capture['records']
        ids = [r['source_id'] for r in records]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate source record identity')
        total = capture.get('source_total')
        complete = capture.get('directory_complete', False)
        source_count = capture.get('source_record_count', len(records))
        anonymous_count = capture.get('anonymous_record_count', 0)
        if not isinstance(anonymous_count, int) or anonymous_count < 0 or source_count != len(records) + anonymous_count:
            raise ValueError('Captured source records must reconcile to named and anonymous records')
        if complete and (total is None or total != source_count):
            raise ValueError('Complete extraction must reconcile to source total')
        features = defaultdict(list)
        observations = []
        for r in records:
            if not all(r.get(k) for k in ('source_id', 'name', 'source_url', 'observed_at', 'scope_basis')):
                raise ValueError('Missing source attribution')
            if r.get('scope_status') != 'included' or r.get('listing_status') != 'listed':
                continue
            fids = []
            # Keep optical listing names, but do not let the focal optical store
            # manufacture a general health/fashion co-tenant observation.
            categories = [] if r.get('role') == 'Optical' else r['categories']
            for fid, label, kind in [('brand:' + key(r['name']), r['name'], 'Retailer'),
                                      *[('category:' + key(c), c, 'Category') for c in categories]]:
                catalogue[fid] = {'id': fid, 'label': label, 'kind': kind}
                fids.append(fid)
                features[fid].append(r['source_id'])
            observations.append({**r, 'features': sorted(set(fids))})
        # Optical census membership is independent of the wider tenant directory.
        for fid, refs in p['features'].items():
            if fid.startswith('operator:'):
                features[fid] = refs
        absent = {}
        for review in capture.get('absence_reviews', []):
            fid = review['feature_id']
            if not complete or capture.get('format_scope') != 'canonical centre':
                raise ValueError('Scoped absence requires an audited complete centre directory')
            if not review.get('basis') or not review.get('source_url') or not review.get('observed_at'):
                raise ValueError('Absence must have a review receipt')
            if fid in features:
                raise ValueError('Contradictory absence review')
            absent[fid] = [review]
            catalogue[fid] = {'id': fid, 'label': review['label'], 'kind': review['kind']}
        p['features'] = dict(features)
        p['absent_features'] = absent
        p['observations'] = observations
        p['scope'] = capture['scope']
        p['coverage'] = {
            'status': 'Complete directory capture' if complete else 'Partial directory / scope coverage',
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
        p['directory_records'] = records
        p['absence_reviews'] = capture.get('absence_reviews', [])
        cats = {c for r in observations if r.get('role') != 'Optical' for c in r['categories']}
        p['shopping_purpose'] = sorted(cats & {'Supermarkets', 'Grocery and fresh food', 'Food and dining', 'Services', 'Health and wellbeing', 'Entertainment', 'Fashion and accessories', 'Department stores'})
        p['positioning'] = sorted(cats & {'Value', 'Mainstream', 'Contemporary fashion', 'Premium fashion', 'Luxury'})
        p['summary'] = f"{p['name']} is a {p['format'].lower()}. The captured directory documents {len(observations)} in-scope listings; current trading is not independently verified."
        p['limitations'] = [capture['limitations'], 'Current co-tenants may differ from the unknown reporting-period mix.',
                             'Listing counts are not distinct occupied tenancies, floor-area shares or customer catchments.',
                             'Absence applies only to the reviewed feature and captured directory scope.']
    output['features'] = sorted(catalogue.values(), key=lambda f: (f['kind'], f['label'].casefold()))
    return output
