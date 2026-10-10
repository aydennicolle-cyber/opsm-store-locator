#!/usr/bin/env python3
"""Public professional-directory leads. Practitioner rows are not store counts."""
import argparse,csv,json,re,urllib.parse,urllib.request
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DIRECTORY='https://www.optometry.org.au/find-an-optometrist/'
ENDPOINT='https://www.optometry.org.au/wp-admin/admin-ajax.php'

def normal(value):return ' '.join(re.sub(r'[^a-z0-9]+',' ',value.lower()).split())

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',type=Path,required=True);parser.add_argument('--reuse',action='store_true');args=parser.parse_args()
 out=args.output_dir.resolve();out.relative_to((ROOT/'output').resolve());out.mkdir(parents=True,exist_ok=True)
 def fetch(state):
  path=out/f'{state}.json'
  if args.reuse and path.exists():return state,json.loads(path.read_text())
  data=urllib.parse.urlencode(dict(action='fao_get_results',state=state)).encode()
  req=urllib.request.Request(ENDPOINT,data=data,headers={'User-Agent':'Mozilla/5.0','Referer':DIRECTORY})
  with urllib.request.urlopen(req,timeout=60) as response:payload=json.load(response)
  if not isinstance(payload,list):raise ValueError(f'Unexpected directory response for {state}')
  path.write_text(json.dumps(payload,indent=2)+'\n');return state,payload
 practices={};counts={}
 with ThreadPoolExecutor(max_workers=2) as pool:
  for state,rows in pool.map(fetch,['ACT','NSW','NT','QLD','SA','TAS','VIC','WA']):
   counts[state]=len(rows)
   for row in rows:
    key=(normal(row.get('company','')),normal(row.get('address','')))
    if not all(key):continue
    if key not in practices:practices[key]=dict(country='AU',state=state,name=row['company'],address=row['address'],latitude=row.get('latitude',''),longitude=row.get('longtitude',''),website=row.get('website',''),phone=row.get('phone',''),source_url=DIRECTORY,practitioner_source_ids=[])
    practices[key]['practitioner_source_ids'].append(str(row.get('cardcode','')))
 summary=dict(collected_at=datetime.now(timezone.utc).isoformat(),raw_practitioner_rows=sum(counts.values()),state_results=counts,practice_address_groups=len(practices),states_returning_50=[k for k,v in counts.items() if v==50],limitation='State results frequently return exactly 50 rows; treat as potentially capped, never a complete state census. Repeated practitioner rows grouped by practice name/address are still discovery candidates. Website, physical retail, coordinates and current trading require independent review.')
 (out/'directory-leads.json').write_text(json.dumps(dict(summary=summary,records=list(practices.values())),indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
