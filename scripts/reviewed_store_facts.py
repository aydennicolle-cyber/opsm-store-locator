"""Apply dated public store facts while preserving canonical IDs and source dates."""
import csv
import json
import re
from datetime import date
from pathlib import Path
from reviewed_independents import public_url
from store_rules import meaningful_address

FIELDS = {'retailer', 'affiliations', 'name', 'full_address', 'state', 'suburb', 'postcode', 'phone', 'official_url', 'website_url', 'directory_url', 'services', 'business_type'}

# Explicit dated review may remove a misclassified customer-facing URL, but
# never erase source history, identity, status or premises through this route.
CLEARABLE_URL_FIELDS = {'official_url', 'website_url', 'directory_url'}

def apply_public_facts(stores, path):
    if not path.exists():
        return
    by_id = {s['store_id']: s for s in stores}
    known_retailers = {s.get('retailer') for s in stores} - {None, ''}
    registry = json.loads((Path(__file__).resolve().parents[1] / 'data' / 'retailer_registry.json').read_text())
    known_affiliations = {item['affiliation_id'] for item in registry['affiliations']}
    seen = set()
    with path.open(newline='', encoding='utf-8-sig') as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        key = row['store_id']
        if key not in by_id or key in seen:
            raise ValueError(f'Unknown or repeated public fact correction: {key}')
        seen.add(key)
        if not row.get('reason') or not public_url(row.get('evidence_url', '')) or date.fromisoformat(row['verified_at']) > date.today():
            raise ValueError(f'Public fact correction lacks evidence/date: {key}')
        changes = {k: row[k] for k in FIELDS if row.get(k)}
        if 'retailer' in changes and changes['retailer'] not in known_retailers:
            raise ValueError(f'Unknown reviewed retailer: {key}')
        if 'affiliations' in changes:
            reviewed = {value.strip() for value in changes['affiliations'].split('|') if value.strip()}
            if not reviewed or not reviewed <= known_affiliations:
                raise ValueError(f'Unknown reviewed affiliation: {key}')
            # This is evidence for additional membership/ownership. It cannot
            # silently remove an affiliation carried by an original source.
            existing = set(filter(None, by_id[key].get('affiliations', '').split('|')))
            changes['affiliations'] = '|'.join(sorted(existing | reviewed))
        clear_fields = {value.strip() for value in row.get('clear_fields', '').split('|') if value.strip()}
        if clear_fields - CLEARABLE_URL_FIELDS:
            raise ValueError(f'Unsupported reviewed field removal: {key}')
        if clear_fields & changes.keys():
            raise ValueError(f'Conflicting reviewed URL replacement/removal: {key}')
        if not changes and not clear_fields:
            raise ValueError(f'Empty public fact correction: {key}')
        if 'full_address' in changes and not meaningful_address(changes):
            raise ValueError(f'Unusable corrected address: {key}')
        if any(not public_url(changes[k]) for k in ('official_url', 'website_url', 'directory_url') if k in changes):
            raise ValueError(f'Invalid public URL in fact correction: {key}')
        # Accept published local, international, mobile and service numbers, but
        # reject prose/URLs or incomplete masked numbers instead of emitting an
        # unusable call link. This is syntax validation, not ownership proof.
        if 'phone' in changes and (not re.fullmatch(r'\+?[\d\s().-]+', changes['phone'])
                                   or re.search(r'\.{2,}', changes['phone'])
                                   or not 6 <= len(re.sub(r'\D', '', changes['phone'])) <= 15):
            raise ValueError(f'Invalid public phone in fact correction: {key}')
        changes.update({field: '' for field in clear_fields})
        by_id[key].update(changes, public_facts_verified_at=row['verified_at'], public_facts_evidence_url=row['evidence_url'], public_facts_reason=row['reason'])
        # This is a facts review, not a refresh of every fact or the raw source.
