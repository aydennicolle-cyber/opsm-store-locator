"""Dated, evidence-bound unresolved outcomes; never create place membership."""
import csv
import hashlib
import json
from datetime import date
from pathlib import Path
if __package__:
    from .reviewed_independents import public_url
else:
    from reviewed_independents import public_url

PATH = Path(__file__).resolve().parents[1] / 'data' / 'unresolved_place_reviews.csv'
IDENTITY_FIELDS = ('store_id', 'retailer', 'name', 'full_address', 'suburb', 'state',
                   'country', 'postcode', 'latitude', 'longitude', 'status',
                   'location_type', 'venue_id', 'official_url', 'source_url')


def fingerprint(store):
    values = {key: str(store.get(key, '')) for key in IDENTITY_FIELDS}
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def load_reviews(stores, path=PATH, *, include_stale=False):
    if not path.exists():
        return {}
    by_id = {store['store_id']: store for store in stores}
    active, seen = {}, set()
    with path.open(newline='') as stream:
        for row in csv.DictReader(stream):
            sid = row['store_id']
            if sid in seen or sid not in by_id:
                raise ValueError(f'Unknown or repeated unresolved-place review: {sid}')
            seen.add(sid)
            if (not public_url(row.get('evidence_url', '')) or not row.get('reason')
                    or date.fromisoformat(row['reviewed_at']) > date.today()
                    or len(row.get('store_fingerprint', '')) != 64):
                raise ValueError(f'Incomplete unresolved-place evidence: {sid}')
            # Material changes reopen investigation; retained review remains history.
            if include_stale or row['store_fingerprint'] == fingerprint(by_id[sid]):
                active[sid] = row
    return active


def review_reason(row):
    return (f"Reviewed {row['reviewed_at']}; place membership remains unresolved. "
            f"{row['reason']} Excluded from place-specific analysis.")
