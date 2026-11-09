"""Capture the public AU/NZ locator; fail closed on incomplete directory traversal.

Stores only whitelisted public business fields, never page analytics/configuration.
"""
import concurrent.futures
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, quote
from urllib.request import urlopen, Request

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://stores.sunglasshut.com/'
FIELDS = ('id', 'uid', 'slug', 'name', 'address', 'geocodedCoordinate',
          'yextDisplayCoordinate', 'mainPhone', 'services', 'hours', 'closed',
          'c_geomodifier', 'c_dServicesSection')

def document(html):
    match = re.search(r'pageProps: JSON.parse\(decodeURIComponent\("(.*?)"\)\)', html, re.S)
    if not match:
        raise ValueError('Locator document missing')
    return json.loads(unquote(match[1]))['document']

def leaves(node):
    children = node.get('dm_directoryChildren', [])
    if not children:
        return [node['slug']]
    return [slug for child in children for slug in leaves(child)]

def fetch(slug):
    if not slug.startswith(('au/', 'nz/')) and slug not in ('au', 'nz'):
        raise ValueError('Outside approved directory scope')
    url = BASE + quote(slug, safe='/&-')
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0 public-directory-reconciliation'}), timeout=40) as response:
                raw = response.read()
            return document(raw.decode()), hashlib.sha256(raw).hexdigest()
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))

def main():
    stamp = datetime.now(timezone.utc).isoformat()
    result = {'fetched_at': stamp, 'source_urls': [BASE+'au', BASE+'nz'], 'countries': {}, 'stores': []}
    for country in ('au', 'nz'):
        root, digest = fetch(country)
        paths = sorted(set(leaves(root)))
        expected = int(root['dm_baseEntityCount'])
        if len(paths) != expected:
            raise ValueError(f'{country}: directory count {expected} != paths {len(paths)}')
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            for path, (doc, sha) in zip(paths, pool.map(fetch, paths)):
                if not doc.get('address') or not doc.get('id'):
                    raise ValueError(f'Not a location: {path}')
                result['stores'].append({**{k: doc[k] for k in FIELDS if k in doc}, 'source_url': BASE+path, 'page_sha256': sha})
        result['countries'][country] = {'directory_count': expected, 'captured_count': len(paths), 'directory_sha256': digest}
        print(country, len(paths), flush=True)
    ids = [s['id'] for s in result['stores']]
    if len(ids) != len(set(ids)):
        raise ValueError('Repeated raw source IDs require reconciliation')
    dest = ROOT / 'retailers/sunglass-hut'
    dest.mkdir(exist_ok=True)
    (dest / 'source_snapshot.json').write_text(json.dumps(result, indent=2)+'\n')

if __name__ == '__main__':
    main()
