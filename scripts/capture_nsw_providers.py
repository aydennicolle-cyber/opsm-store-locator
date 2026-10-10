"""Capture the public NSW Spectacles Program PDF as unpromoted discovery.

The PDF is supplied explicitly so a retrieval failure cannot overwrite the last
snapshot. Grid headers and every row are checked; no silent table truncation.
This does not establish current trading, a canonical identity or retail tenancy.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from reconcile_qld_dispensers import source_hash

HEADERS = ['Business name', 'Address 1', 'Address 2', 'Suburb', 'State',
           'Post Code', 'Telephone number (general)']


def text(value):
    return ' '.join((value or '').split())


def capture_tables(pages):
    records = []
    occurrences = Counter()
    for page_number, tables in enumerate(pages, 1):
        if len(tables) != 1 or not tables[0]:
            raise ValueError(f'Page {page_number}: expected one nonempty provider table')
        table = tables[0]
        if [text(v) for v in table[0]] != HEADERS:
            raise ValueError(f'Page {page_number}: unexpected provider table columns')
        if len(table) < 2:
            raise ValueError(f'Page {page_number}: no provider rows extracted')
        for row_number, cells in enumerate(table[1:], 1):
            if len(cells) != len(HEADERS):
                raise ValueError(f'Page {page_number}, row {row_number}: incomplete columns')
            name, address1, address2, suburb, state, postcode, phone = map(text, cells)
            if not name or state not in {'NSW', 'ACT', 'QLD', 'VIC', 'SA', 'WA', 'TAS', 'NT'}:
                raise ValueError(f'Page {page_number}, row {row_number}: invalid identity/state')
            if postcode and (not postcode.isdigit() or len(postcode) != 4):
                raise ValueError(f'Page {page_number}, row {row_number}: invalid postcode')
            raw = dict(name=name, address=', '.join(v for v in [address1, address2] if v),
                       suburb=suburb, state=state, postcode=postcode, phone=phone,
                       address_1=address1, address_2=address2, original_cells=cells)
            digest = source_hash(raw)
            occurrences[digest] += 1
            records.append(dict(source_id=f'nsw-spectacles-provider:{digest}:{occurrences[digest]}',
                                source_record_hash=digest, source_page=page_number,
                                source_page_row=row_number, source_row_number=len(records)+1,
                                raw=raw))
    if not records:
        raise ValueError('No provider pages captured')
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', type=Path, required=True)
    parser.add_argument('--source-url', required=True)
    parser.add_argument('--upstream-url', required=True)
    parser.add_argument('--checked-at', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    import pdfplumber  # Only capture requires PDF tooling; matching uses stdlib.
    with pdfplumber.open(args.pdf) as pdf:
        pages = [page.extract_tables() for page in pdf.pages]
        metadata = dict(pdf.metadata)
    records = capture_tables(pages)
    snapshot = dict(source=dict(
        source_id='nsw-spectacles-program-provider-pdf', title='NSW Spectacles Program — List of Providers',
        url=args.source_url, upstream_url=args.upstream_url, checked_at=args.checked_at,
        raw_pdf_sha256=hashlib.sha256(args.pdf.read_bytes()).hexdigest(),
        raw_pdf_bytes=args.pdf.stat().st_size, pdf_page_count=len(pages), pdf_metadata=metadata,
        source_last_updated='',
        date_limitation='PDF metadata creation/modification is retained, not treated as each provider verification date or an explicit publication date.',
        capture_method='Extract every gridded table page; validate the seven column headers and each provider row; preserve original cell text, page/row positions and content hashes.',
        source_identifier_basis='No provider IDs published. Content-derived IDs preserve each captured row; repeated identical rows have occurrence suffixes and are not silently deduplicated.',
        coverage_limitation='Participating optometrists/dispensers only; includes cross-border and potentially visiting/clinical services. No automatic store admission or current-status inference.'
    ), records=records)
    args.output.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps(dict(records=len(records), pages=len(pages), states=dict(Counter(r['raw']['state'] for r in records)))))


if __name__ == '__main__':
    main()
