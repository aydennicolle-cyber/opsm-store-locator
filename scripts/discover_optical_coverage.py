#!/usr/bin/env python3
"""Broader AU/NZ OSM discovery, retained as review leads rather than live stores."""
import argparse
import csv
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from fetch_independent_optometrists import overpass, address

ROOT=Path(__file__).resolve().parents[1]


def coverage_query(country):
    return f'''[out:json][timeout:180];
    area["ISO3166-1"="{country}"][admin_level="2"]->.searchArea;
    (
      nwr["shop"="optician"](area.searchArea);
      nwr["healthcare"="optometrist"](area.searchArea);
      nwr["healthcare:speciality"~"optometr|ophthalm",i](area.searchArea);
      nwr["name"~"optomet|optician|eyewear|optical|sunglass",i](area.searchArea);
    );out center tags;'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'output/coverage-discovery')
    parser.add_argument('--reuse',action='store_true')
    args=parser.parse_args();out=args.output_dir.resolve()
    out.relative_to((ROOT/'output').resolve());out.mkdir(parents=True,exist_ok=True)
    def fetch(country):
        path=out/f'osm-{country}.json'
        if args.reuse and path.exists():return country,json.loads(path.read_text())
        payload=overpass(coverage_query(country));path.write_text(json.dumps(payload)+'\n')
        return country,payload
    rows=[];counts={}
    with ThreadPoolExecutor(max_workers=2) as pool:
        for country,payload in pool.map(fetch,['AU','NZ']):
            counts[country]=len(payload.get('elements',[]))
            for item in payload.get('elements',[]):
                tags=item.get('tags',{});point=item.get('center',item)
                rows.append(dict(id=f"osm-{country.lower()}-{item['type']}-{item['id']}",country=country,name=tags.get('name') or tags.get('brand',''),address=address(tags,'Australia' if country=='AU' else 'New Zealand'),suburb=tags.get('addr:suburb') or tags.get('addr:city') or tags.get('addr:town',''),state=tags.get('addr:state',''),postcode=tags.get('addr:postcode',''),lat=point.get('lat',''),lng=point.get('lon',''),verified_optometry='unreviewed',source_url=f"https://www.openstreetmap.org/{item['type']}/{item['id']}",website=tags.get('website') or tags.get('contact:website',''),phone=tags.get('phone') or tags.get('contact:phone',''),tags=json.dumps(tags,ensure_ascii=False,sort_keys=True)))
    rows.sort(key=lambda r:r['id'])
    with (out/'discovery.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    summary=dict(collected_at=datetime.now(timezone.utc).isoformat(),by_country=counts,total=len(rows),method='Optician shop tags, optometrist healthcare tags, eye-care specialty tags and optical-name variants. No centre/high-street, rating, website, postcode or opening-hours filter. Leads only; not a complete census.')
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
