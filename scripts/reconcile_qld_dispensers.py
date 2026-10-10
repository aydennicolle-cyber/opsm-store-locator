"""Compare a captured public dispenser directory with the census, without admission.

Every match is a review candidate. Shared phones, similar names and postal localities
do not establish identity, trading status, optical-retail eligibility or tenancy.
"""
import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STOP = {'the', 'and', 'optical', 'optometrist', 'optometrists', 'optometry',
        'eyecare', 'eye', 'care', 'services', 'service', 'by', 'at'}


def normalize(value):
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode()
    return ' '.join(re.findall(r'[a-z0-9]+', value.lower().replace('&', ' and ')))


def phone_key(value):
    digits = re.sub(r'\D', '', value)
    if digits.startswith('61') and len(digits) == 11:
        digits = '0' + digits[2:]
    return digits if len(digits) == 10 else ''


def locality_key(value, postcode):
    # Retain original source strings; remove a repeated trailing postcode only in
    # the matching key, not the archived row.
    return normalize(re.sub(r'\s*' + re.escape(postcode) + r'\s*$', '', value)) if postcode else normalize(value)


def name_tokens(value):
    return set(normalize(value).split()) - STOP


def source_hash(raw):
    return hashlib.sha256(json.dumps(raw, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode()).hexdigest()


def reconcile(snapshot, stores):
    records = []
    for lead in snapshot['records']:
        raw = lead['raw']
        assert source_hash(raw) == lead['source_record_hash']
        # The original QLD HTML table omits state. Other public directories
        # retain it per row, including providers across a scheme's border.
        state = raw.get('state', 'QLD')
        locality = locality_key(raw['suburb'], raw['postcode'])
        phone = phone_key(raw['phone'])
        tokens = name_tokens(raw['name'])
        candidates = []
        for store in stores:
            if store['country'] != 'Australia':
                continue
            same_phone = bool(phone and phone == phone_key(store.get('phone', '')))
            same_locality = bool(locality and locality == normalize(store.get('suburb', '')))
            same_postcode = bool(raw['postcode'] and raw['postcode'] == store.get('postcode'))
            other_tokens = name_tokens(store['name'])
            # Ignore single generic terms; common locality tokens alone are not
            # sufficient to make a name match.
            distinctive = tokens - set(locality.split())
            other_distinctive = other_tokens - set(locality.split())
            overlap = distinctive & other_distinctive
            name_overlap = bool(overlap and len(overlap) / max(1, min(len(distinctive), len(other_distinctive))) >= 0.5)
            exact_name = normalize(raw['name']) == normalize(store['name'])
            signals = []
            if same_phone: signals.append('same_phone')
            if exact_name: signals.append('same_name')
            elif name_overlap: signals.append('name_token_overlap')
            if same_locality: signals.append('same_locality')
            if same_postcode: signals.append('same_postcode')
            same_state_exact_name = exact_name and bool(distinctive) and bool(state) and store.get('state') == state
            # A directory may append its branch locality to a brand while an
            # incomplete census record has only the brand and state. Surface
            # that record for review without assigning any branch identity.
            incomplete_branch_name = (
                bool(distinctive) and distinctive == other_distinctive
                and bool(state) and store.get('state') == state
                and not store.get('suburb') and not store.get('postcode')
            )
            if incomplete_branch_name:
                signals.append('same_distinctive_name_incomplete_location')
            if not (same_phone or same_state_exact_name or incomplete_branch_name or (exact_name or name_overlap) and (same_locality or same_postcode)):
                continue
            candidates.append(dict(store_id=store['store_id'], name=store['name'],
                                   address=store['full_address'], phone=store.get('phone', ''),
                                   status=store['status'], signals=signals))
        candidates.sort(key=lambda r: ('same_phone' not in r['signals'],
                                      'same_locality' not in r['signals'], r['store_id']))
        supported = [c for c in candidates if 'same_phone' in c['signals']
                     and ('same_name' in c['signals'] or 'name_token_overlap' in c['signals'])
                     and ('same_locality' in c['signals'] or 'same_postcode' in c['signals'])]
        triage = ('single_supported_candidate' if len(candidates) == 1 and len(supported) == 1
                  else 'candidate_review' if candidates else 'no_candidate_found')
        flags = []
        address = raw['address'].lower()
        if not address.strip(): flags.append('missing_source_street_address')
        if re.search(r'https?://|\bpo box\b|\bp\.?o\.? box\b', address):
            flags.append('non_premises_address_requires_review')
        if re.search(r'hospital|health centre|health service|medical centre|surgery|aboriginal|visiting|mobile',
                     (raw['name'] + ' ' + address).lower()):
            flags.append('retail_or_visiting_service_eligibility_requires_review')
        records.append(dict(source_id=lead['source_id'], source_record_hash=lead['source_record_hash'],
                            raw=raw, triage=triage, eligibility_flags=flags,
                            candidates=candidates, promotion_status='Unpromoted discovery lead'))
    return dict(source=snapshot['source'], scope='Directory-to-census discovery triage only',
                census_store_count=len(stores), source_records=len(records),
                triage_counts=dict(Counter(r['triage'] for r in records)),
                eligibility_flag_counts=dict(Counter(f for r in records for f in r['eligibility_flags'])),
                limitations=[
                    'Scheme participants are not a complete optical retailer census; scheme geography may include cross-border providers.',
                    'Candidate matches are not accepted canonical identities; review premises and operator evidence.',
                    'No candidate found does not prove a missing retailer: aliases, incomplete census contacts, closures and non-retail services can cause this result.',
                    'No rows are automatically admitted or counted as manual-review failures; no store status, coordinates or place memberships are inferred.'
                ], records=records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, default=ROOT/'data/discovery/qld_health_dispensers.json')
    parser.add_argument('--stores', type=Path, default=ROOT/'data/optical_stores.csv')
    parser.add_argument('--output', type=Path, default=ROOT/'data/discovery/qld_health_dispenser_reconciliation.json')
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text())
    with args.stores.open(newline='') as stream:
        stores = list(csv.DictReader(stream))
    result = reconcile(snapshot, stores)
    result['canonical_sha256'] = hashlib.sha256(args.stores.read_bytes()).hexdigest()
    result['source_snapshot_sha256'] = hashlib.sha256(args.snapshot.read_bytes()).hexdigest()
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps({k:result[k] for k in ('source_records', 'triage_counts', 'eligibility_flag_counts')}))


if __name__ == '__main__':
    main()
