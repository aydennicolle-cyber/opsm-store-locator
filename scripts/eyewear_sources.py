"""Refresh evidenced Oakley facts while retaining existing canonical identities."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def refresh_oakley_canonical(stores, remaps):
    by_id = {row['store_id']: row for row in stores}
    with (ROOT / 'retailers/oakley/stores.csv').open() as handle:
        for row in csv.DictReader(handle):
            source = 'oakley-' + row['id']
            if source not in remaps:
                continue
            store = by_id[remaps[source]]
            # Keep reviewed coordinates and accepted place identity intact.
            for field in ('name', 'full_address', 'phone', 'official_url', 'website_url',
                          'services', 'business_type', 'status', 'source_url', 'fetched_at'):
                store[field] = row[field]
            store.update(retailer='Oakley', status_verified_at=row['verified_at'],
                         status_evidence_url=row['status_evidence_url'],
                         status_reason=row['evidence_notes'])
