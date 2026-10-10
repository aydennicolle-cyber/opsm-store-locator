"""Validate explicit local source-row decisions without changing public identities."""
import csv
import hashlib
import json
from datetime import date
from stage_independent_candidates import public_url

DECISIONS = {'Linked existing', 'Accepted new', 'Duplicate source listing', 'Excluded', 'Needs review'}
LINKED = {'Linked existing', 'Accepted new'}


def canonical_hash(store):
    identity = {key: str(store.get(key, '')) for key in ('store_id', 'retailer', 'country', 'name', 'full_address', 'latitude', 'longitude')}
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()


def apply_record_reviews(records, stores, path):
    if not path.exists():
        return
    source = {r['source_id']: r for r in records}
    canonical = {r['store_id']: r for r in stores}
    seen = set()
    with path.open(newline='', encoding='utf-8-sig') as handle:
        decisions = list(csv.DictReader(handle))
    for decision in decisions:
        key = decision['source_id']
        if key in seen or key not in source:
            raise ValueError(f'Unknown or repeated source review: {key}')
        seen.add(key)
        row = source[key]
        outcome = decision['decision']
        if outcome not in DECISIONS or not decision.get('reason') or not public_url(decision.get('evidence_url', '')):
            raise ValueError(f'Incomplete public evidence for source review: {key}')
        try:
            reviewed = date.fromisoformat(decision['checked_at'])
        except (ValueError, KeyError) as exc:
            raise ValueError(f'Invalid source review date: {key}') from exc
        if reviewed > date.today():
            raise ValueError(f'Future source review date: {key}')
        if decision['source_record_hash'] != row['source_record_hash']:
            raise ValueError(f'Source changed; review the decision again: {key}')
        target_id = decision.get('canonical_store_id', '')
        if outcome in LINKED and not target_id:
            raise ValueError(f'Canonical identity required: {key}')
        if target_id:
            target = canonical.get(target_id)
            if not target or canonical_hash(target) != decision.get('canonical_record_hash'):
                raise ValueError(f'Canonical identity changed; review again: {key}')
            if target['country'] != {'AU': 'Australia', 'NZ': 'New Zealand'}[row['country']]:
                raise ValueError(f'Cross-country source identity: {key}')
        if outcome in {'Excluded', 'Needs review'} and target_id:
            raise ValueError(f'Unresolved/excluded record cannot assert a canonical identity: {key}')
        related = decision.get('related_source_id', '')
        if outcome == 'Duplicate source listing' and (related not in source or related == key):
            raise ValueError(f'Duplicate needs another source row: {key}')
        row.update(outcome=outcome, canonical_store_id=target_id, related_source_id=related,
                   evidence_url=decision['evidence_url'], reason=decision['reason'], checked_at=decision['checked_at'],
                   possible_store_ids='')
