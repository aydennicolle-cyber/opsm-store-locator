"""Compare directory evidence with accepted census links without inventing outlets.

Directory presence can establish an operator feature, but cannot manufacture a
network store ID, point, trading status or accepted census membership.
"""
from collections import Counter
import re
import csv
from pathlib import Path
from build_retail_environments import key
from public_directory_schema import identity_review

ALIASES = {
    'bright eyes': 'BrightEyes', 'brighteyes': 'BrightEyes',
    'medispecs': 'Medispecs', 'eye concepts': 'Eye Concepts', 'eyeview': 'Eyeview', 'city optics': 'City Optics',
    'owndays': 'OWNDAYS', 'city specs': 'City Specs', 'custom eyes': 'Custom Eyes',
    'icontact optometrists': 'iContact Optometrists', 'zoom optics': 'Zoom Optics',
    'lifestyle optical': 'Lifestyle Optical', 'eyeselect': 'EyeSelect',
    'laubman pank': 'Laubman & Pank', 'holdfastbay': 'Holdfast Bay', 'holdfast bay': 'Holdfast Bay',
    'options optometrists': 'Options Optometrists', 'total eyecare': 'Total Eyecare',
    'alfred nott': 'Alfred Nott', 'eyes2port': 'Eyes 2 Port', 'eyes 2 port': 'Eyes 2 Port',
    'optimax optometrists': 'Optimax Optometrists', 'sunglass style': 'Sunglass Style',
    'specsavers': 'Specsavers', 'opsm': 'OPSM', 'oscar wylee': 'Oscar Wylee',
    'bailey nelson': 'Bailey Nelson', 'sunglass hut': 'Sunglass Hut',
    'laubman and pank': 'Laubman & Pank', 'bupa optical': 'Bupa Optical',
    'eyeq optometrists': 'EyeQ Optometrists', 'optical superstore': 'Optical Superstore',
    'the optical superstore': 'Optical Superstore', 'optical warehouse': 'Optical Warehouse',
    'george and matilda': 'George & Matilda', 'dresden vision': 'Dresden Vision',
    '1001 optometry': '1001 Optometry', 'the optical co': 'The Optical Company',
    'the optical company': 'The Optical Company', 'eyecare plus': 'Eyecare Plus',
}


def operator_name(name):
    normalized = key(name)
    for alias in sorted(ALIASES, key=len, reverse=True):
        if normalized == alias or normalized.startswith(alias + ' '):
            return ALIASES[alias]
    return name  # A named business, not a claim about independent ownership.


def reconcile(payload, captured_place_ids, evidence_reviews=None):
    catalogue = {f['id']: f for f in payload['features']}
    audit = []
    review_path = Path(__file__).resolve().parents[1] / 'data/directory_role_reviews.csv'
    with review_path.open() as f:
        role_reviews = {(r['place_id'], r['source_id']): r for r in csv.DictReader(f)}
    if evidence_reviews is None:
        with review_path.with_name('optical_evidence_reviews.csv').open() as f:
            evidence_reviews = list(csv.DictReader(f))
    for place in payload['places']:
        for observation in place['observations']:
            review = role_reviews.get((place['place_id'], observation['source_id']))
            if review:
                observation.setdefault('original_role', observation['role'])
                observation['role'] = review['role']
                observation['role_review'] = {'date': review['review_date'], 'basis': review['basis'], 'source_url': review['source_url']}
        # Explicit duplicate decisions suppress an extra observation, never a census store.
        decisions = [r for r in evidence_reviews if r['place_id'] == place['place_id']]
        duplicate_reviews = {r['source_id']: r for r in decisions if r['decision'] == 'duplicate'}
        if duplicate_reviews:
            for sid, decision in duplicate_reviews.items():
                canonical = [r for r in decisions if r['decision'] == 'pair' and r['store_id'] == decision['store_id'] and r['source_id'] != sid]
                if len(canonical) != 1 or not any(o['source_id'] == canonical[0]['source_id'] for o in place['observations']):
                    raise ValueError('Duplicate review requires one retained canonical listing: ' + sid)
                if not any(o['store_id'] == decision['store_id'] for o in place['optical']):
                    raise ValueError('Duplicate review requires an existing same-place outlet: ' + sid)
            place['observations'] = [o for o in place['observations'] if o['source_id'] not in duplicate_reviews]
            for record in place.get('directory_records', []):
                if record['source_id'] in duplicate_reviews:
                    record.setdefault('original_scope_status', record.get('scope_status'))
                    record['scope_status'] = 'suspected_duplicate'
                    record['identity_review'] = identity_review(duplicate_reviews[record['source_id']])
            for fid in list(place['features']):
                place['features'][fid] = [ref for ref in place['features'][fid] if ref not in duplicate_reviews and ref.removeprefix('directory:') not in duplicate_reviews]
                if not place['features'][fid]: del place['features'][fid]
            coverage = place.setdefault('coverage', {})
            coverage.update(usable_listings=len(place['observations']), observations=len(place['observations']),
                            distinct_names=len({key(o['name']) for o in place['observations']}),
                            duplicate_source_ids=sorted(duplicate_reviews))
            note = ' Subsequent identity review: suspected duplicate publisher records are retained in held source history but excluded from tenant and optical listing counts. This supersedes earlier unresolved-duplicate wording; original captured totals remain unchanged.'
            if note not in coverage.get('directory_note', ''): coverage['directory_note'] = coverage.get('directory_note', '') + note
        census = place['optical']
        has_directory = place['place_id'] in captured_place_ids
        listed = [r for r in place['observations'] if r.get('role') == 'Optical'] if has_directory else []
        cc = Counter(key(operator_name(r['operator'])) for r in census)
        dc = Counter(key(operator_name(r['name'])) for r in listed)
        paired = []
        decisions = [r for r in evidence_reviews if r['place_id'] == place['place_id']]
        explicit = {r['source_id']: r for r in decisions if r['decision'] == 'pair'}
        claimed = set()
        for row in listed:
            label = operator_name(row['name']); op = key(label)
            matches = [r for r in census if key(operator_name(r['operator'])) == op]
            # A documented practice name may coexist with a network operator label.
            if not matches and place['place_id'] == 'place-au-qld-sunshine-plaza' and row['source_id'] == 'e492c319-d19d-470d-aa23-89c135d613f2':
                matches = [r for r in census if r['store_id'] == 'george-matilda-17206']
            # Unique same-place operator pairing is for comparison only. Multiple
            # branches or kiosks remain unresolved rather than name-deduplicated.
            sid = matches[0]['store_id'] if len(matches) == 1 and dc[op] == 1 else None
            if sid is None and len(matches) > 1 and row.get('source_url'):
                url = row['source_url'].rstrip('/')
                exact = [m for m in matches if m.get('source_url', '').rstrip('/') == url]
                directory_exact = [d for d in listed if d.get('source_url', '').rstrip('/') == url]
                if len(exact) == len(directory_exact) == 1: sid = exact[0]['store_id']
            if sid is None and len(matches) > 1:
                level = re.search(r'\blevel\s+(\d+)\b', row['name'], re.I)
                if level:
                    subset = [m for m in matches if re.search(r'\blevel\s+' + level[1] + r'\b', m.get('name', ''), re.I)]
                    same_level_rows = [d for d in listed if key(operator_name(d['name'])) == op and re.search(r'\blevel\s+' + level[1] + r'\b', d['name'], re.I)]
                    if len(subset) == len(same_level_rows) == 1: sid = subset[0]['store_id']
            decision = explicit.get(row['source_id'])
            if decision:
                # Reviewed identity never establishes membership by itself.
                sid = decision['store_id'] if any(r['store_id'] == decision['store_id'] for r in census) else None
            if sid in claimed:
                raise ValueError('Multiple directory records claim one outlet: ' + sid)
            if sid: claimed.add(sid)
            paired.append({'source_id': row['source_id'], 'name': row['name'],
                           'operator': label, 'source_url': row['source_url'],
                           'observed_at': row['observed_at'], 'store_id': sid,
                           'identity_review': identity_review(decision) if decision and sid else None,
                           'resolution': 'Reviewed same-place branch identity' if decision and sid else 'Same-place operator corroboration' if sid else
                           'Multiple outlet identities need review' if matches else
                           'Directory presence; census identity or membership unresolved'})
            fid = 'operator:' + op
            catalogue[fid] = {'id': fid, 'label': label, 'kind': 'Optical operator'}
            refs = place['features'].setdefault(fid, [])
            ref = 'directory:' + row['source_id']
            if ref not in refs:
                refs.append(ref)
        paired_ids = {r['store_id'] for r in paired if r['store_id']}
        census_only = [r['store_id'] for r in census if r['store_id'] not in paired_ids] if has_directory else []
        issues = []
        coverage = place.get('coverage', {})
        partial = (not coverage.get('directory_complete', False)
                   or coverage.get('format_scope') == 'named street'
                   or place.get('format') == 'High Street')
        # A source-scope omission is explained by incomplete coverage. It is
        # distinct from an operator present in the source with ambiguous branches.
        source_omissions = {r['store_id'] for r in census
                            if not dc[key(operator_name(r['operator']))]}
        for row in paired:
            if row['store_id']: continue
            op = key(row['operator'])
            reason = ('Multiple directory/outlet identities; branch or duplicate check needed' if dc[op] > 1 or cc[op] > 1 else
                      'Sunglasses/eyewear listing without a matched census outlet; inventory scope and identity need review' if op in {'sunglass hut', 'sunglass style', 'brighteyes'} else
                      'Directory presence documented; stable outlet identity or accepted place assignment still required')
            issues.append({'side':'listed', 'record_id':row['source_id'], 'name':row['name'], 'reason':reason, 'source_url':row['source_url']})
        for row in census:
            if row['store_id'] not in census_only: continue
            reason = ('Partial inventory does not establish absence; retain accepted census outlet' if partial else
                      'Complete captured directory does not corroborate this outlet identity; check source dates, trading status and branch scope')
            issues.append({'side':'linked', 'record_id':row['store_id'], 'name':row.get('name',row['operator']), 'reason':reason, 'source_url':row.get('source_url','')})
        retained = {r['store_id']: r for r in decisions if r['decision'] == 'retain_census'}
        held = {r['store_id']: r for r in decisions if r['decision'] == 'hold'}
        held_listings = {r['source_id']: r for r in decisions if r['decision'] == 'hold' and r.get('source_id')}
        for issue in issues:
            decision = retained.get(issue['record_id']) if issue['side'] == 'linked' else None
            issue['resolved'] = bool(decision)
            if (not decision and partial and issue['side'] == 'linked'
                    and issue['record_id'] in source_omissions
                    and issue['record_id'] not in held):
                issue['resolved'] = True
                issue['explained_by_source_coverage'] = True
            if not decision and issue['side'] == 'linked':
                decision = held.get(issue['record_id'])
            if not decision and issue['side'] == 'listed':
                decision = held_listings.get(issue['record_id'])
            if decision:
                issue['reason'] = decision['basis']
                issue['source_url'] = decision['source_url']
                issue['review_date'] = decision['review_date']
        unresolved = sum(not r['resolved'] for r in issues)
        review = [r for r in paired if r['store_id'] is None]
        place['optical_reconciliation'] = {
            'census_linked_count': len(census),
            'directory_listed_count': len(listed) if has_directory else None,
            'directory_records': paired, 'census_not_in_directory': census_only,
            'review_count': len(review), 'unmatched_census_count': len(census_only), 'review_items': issues, 'matched_listing_count': sum(bool(r['store_id']) for r in paired),
            'unresolved_issue_count': unresolved, 'explained_difference_count': len(issues) - unresolved,
            'status': 'No captured directory comparison' if not has_directory else
                      'Review differences' if unresolved else 'Explained source differences' if issues else 'Corroborated operator evidence',
            'note': 'Counts overlap and must not be added. A missing directory listing is not closure; zero census links is not absence. Directory records without a stable matched outlet stay outside network totals.',
        }
        operators = {key(operator_name(r['operator'])) for r in census} | set(dc)
        place['bn_presence'] = 'present' if 'bailey nelson' in operators else 'not_recorded'
        place['other_optical_presence'] = 'present' if operators - {'bailey nelson'} else 'not_recorded'
        if has_directory:
            audit.append({'place_id': place['place_id'], 'name': place['name'], **place['optical_reconciliation']})
    payload['features'] = sorted(catalogue.values(), key=lambda f: (f['kind'], f['label'].casefold()))
    return audit
