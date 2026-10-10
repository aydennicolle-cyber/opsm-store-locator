#!/usr/bin/env python3
"""Add published population baselines to a matching ABS market snapshot."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from build_market_intelligence import ABS_FILES, SA2_OUTPUT, workbook_rows, population_change


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--population-workbook', type=Path, required=True)
    args = parser.parse_args()
    population = workbook_rows(args.population_workbook, {2021, 2025}, {'population': (3, 'Estimated resident population (no.)')})
    payload = json.loads(SA2_OUTPUT.read_text())
    mismatch = []
    for f in payload['features']:
        props=f['properties'];record=population.get(props['sa2_code'], {})
        current=record.get(2025, {}).get('population')
        baseline=record.get(2021, {}).get('population')
        if props.get('population_2025') != current:
            mismatch.append(props['sa2_code'])
        props['population_2021']=baseline
        props['population_growth_2021_2025_number']=population_change(current, baseline)
    if mismatch:
        raise ValueError(f'Existing 2025 populations differ from workbook: {mismatch}. Review source vintage before replacing values.')
    meta=payload['metadata']
    meta['field_definitions'].update(population_2021='ABS estimated resident population baseline, 2021', population_growth_2021_2025_number='2025 population minus published 2021 population; missing when either is unavailable. Negative values mean population declined.')
    meta['population_baseline_source']=dict(source_url=ABS_FILES['population'],sha256=hashlib.sha256(args.population_workbook.read_bytes()).hexdigest(),checked_at=datetime.now(timezone.utc).isoformat(),worksheet='Table 1',header_row=7,year_column='C',population_column='D')
    meta['boundary_display_note']='Display geometries are generalised at 0.01 degrees and can have gaps/overlaps. Coordinate-bound authoritative matches in market_point_links.json take precedence for reviewed points; unreviewed map joins are approximate.'
    SA2_OUTPUT.write_text(json.dumps(payload,separators=(',',':'))+'\n')
    print('Added published 2021 baselines and absolute growth; all existing 2025 values match the workbook.')


if __name__=='__main__':main()
