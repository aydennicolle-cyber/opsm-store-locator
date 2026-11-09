"""Prepare an exact public-safe news batch in a separate local review site; never publish."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
try:
    from .build_location_news import merge_events
    from .location_news_schema import document
    from .package_public_site import package, validate_bundle
    from .scan_public_privacy import scan_structured, scan_browser_requests
    from .public_directory_schema import decode_json
except ImportError:
    from build_location_news import merge_events
    from location_news_schema import document
    from package_public_site import package, validate_bundle
    from scan_public_privacy import scan_structured, scan_browser_requests
    from public_directory_schema import decode_json

ROOT = Path(__file__).resolve().parents[1]


def prepare(source, output, root=ROOT):
    source, output, root = Path(source).resolve(), Path(output).resolve(), Path(root).resolve()
    if output.is_relative_to(root) or source.is_relative_to(root):
        raise ValueError('Unapproved research batches and review sites must stay outside the public repository')
    data = root / 'data'
    places = {x['place_id'] for x in json.loads((data / 'retail_places.json').read_text())['places']}
    stores = {x['store_id'] for x in csv.DictReader((data / 'optical_stores.csv').open())}
    candidate = document(decode_json(source.read_text()), places, stores)
    current = document(decode_json((data / 'location_news.json').read_text()), places, stores)
    merged = document(dict(schema_version=1, document_type='location_news',
                           events=merge_events(current['events'] + candidate['events']),
                           checks=list({json.dumps(x, sort_keys=True):x for x in current['checks'] + candidate['checks']}.values())), places, stores)
    content = (json.dumps(merged, ensure_ascii=False, indent=2) + '\n').encode()
    batch_hash = hashlib.sha256(content).hexdigest()
    package(root, output / 'site', revision='local-news-review-' + batch_hash[:12])
    (output / 'site/data/location_news.json').write_bytes(content)
    validate_bundle(output / 'site')
    scan_structured(output / 'site', packaged=True); scan_browser_requests(output / 'site')
    manifest = dict(batch_sha256=batch_hash, event_count=len(merged['events']),
                    revision_count=sum(len(e['versions']) for e in merged['events']),
                    source_input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    approval_status='pending_exact_batch_approval', published=False)
    (output / 'review-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True, type=Path); p.add_argument('--output', required=True, type=Path)
    args = p.parse_args(); print(json.dumps(prepare(args.input, args.output), indent=2))
