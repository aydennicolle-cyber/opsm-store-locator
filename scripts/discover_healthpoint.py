#!/usr/bin/env python3
"""Read provider-maintained NZ optometry directory pages into a local evidence queue."""
import csv
import html
import json
import re
import urllib.request
from urllib.parse import urljoin
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/coverage-expansion-20260912/healthpoint'


def plain(value):
    value=re.sub(r'<(?:script|style)\b.*?</(?:script|style)>',' ',value,flags=re.S|re.I)
    value=re.sub(r'<br\s*/?>',', ',value,flags=re.I)
    return ' '.join(html.unescape(re.sub(r'<[^>]+>',' ',value)).split())



class _ContactPanels(HTMLParser):
    """Collect provider contact panels, excluding practitioner and navigation cards."""
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.panels = []
        self.depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if not self.depth:
            classes = dict(attrs).get("class", "").split()
            if tag != "div" or "service-panel" not in classes:
                return
            self.depth = 1
            self.parts = [self.get_starttag_text()]
            return
        self.parts.append(self.get_starttag_text())
        if tag == "div":
            self.depth += 1

    def handle_startendtag(self, tag, attrs):
        if self.depth:
            self.parts.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        if not self.depth:
            return
        self.parts.append(f"</{tag}>")
        if tag == "div":
            self.depth -= 1
            if not self.depth:
                self.panels.append("".join(self.parts))
                self.parts = []

    def handle_data(self, data):
        if self.depth:
            self.parts.append(data)

    def handle_entityref(self, name):
        self.handle_data(f"&{name};")

    def handle_charref(self, name):
        self.handle_data(f"&#{name};")


def parse_locations(page, url):
    """Preserve each written branch and its own phone/point without accepting it."""
    parser = _ContactPanels()
    parser.feed(page)
    locations = []
    seen = set()
    for panel in parser.panels:
        heading = re.search(r"<h3\b[^>]*>(.*?)</h3>", panel, re.S | re.I)
        address = re.search(r'Street Address</h4>\s*<div[^>]*>(.*?)</div>', panel, re.S | re.I)
        label = plain(heading.group(1)) if heading else ""
        written_address = plain(address.group(1)) if address else label
        if not written_address:
            continue
        link = re.search(r'<a[^>]*href=[\"\']([^\"\']+/at/[^\"\']+)[\"\']', heading.group(1), re.I) if heading else None
        detail_url = urljoin(url, html.unescape(link.group(1))) if link else url
        phone = re.search(r'itemprop=[\"\']telephone[\"\'][^>]*>(.*?)</p>', panel, re.S | re.I)
        latitudes = re.findall(r'itemprop=[\"\']latitude[\"\'] content=[\"\']([^\"\']+)', panel)
        longitudes = re.findall(r'itemprop=[\"\']longitude[\"\'] content=[\"\']([^\"\']+)', panel)
        unique_point = len(latitudes) == len(longitudes) == 1
        key = (detail_url, written_address.casefold())
        if key in seen:
            continue
        seen.add(key)
        locations.append(dict(name=label, address=written_address,
                              address_basis="street_address" if address else "location_heading",
                              phone=plain(phone.group(1)) if phone else "",
                              latitude=latitudes[0] if unique_point else "",
                              longitude=longitudes[0] if unique_point else "",
                              source_url=detail_url, provider_source_url=url,
                              review_note="Discovery premises only; verify operator identity, retail activity and current trading before admission"))
    return locations


def parse_page(page,url):
    title=re.search(r'<title>(.*?)</title>',page,re.S|re.I)
    locations=parse_locations(page,url)
    addresses=re.findall(r'Street Address</h4>\s*<div[^>]*>(.*?)</div>',page,re.S|re.I)
    latitudes=re.findall(r'itemprop="latitude" content="([^"]+)"',page)
    longitudes=re.findall(r'itemprop="longitude" content="([^"]+)"',page)
    website=re.search(r'<a href="([^"]+)"[^>]*itemprop="url"',page)
    description=re.search(r'<section[^>]*class="[^"]*description[^"]*"[^>]*>(.*?)</section>',page,re.S|re.I)
    if not description:description=re.search(r'<div[^>]*class="[^"]*description[^"]*"[^>]*>(.*?)</section>',page,re.S|re.I)
    phone=re.search(r'itemprop="telephone"[^>]*>(.*?)</p>',page,re.S)
    updated=re.search(r'This page was last updated at (.*?)\.',page,re.S)
    return dict(id=url.rstrip('/').rsplit('/',1)[-1],name=plain(title.group(1)).split(' • ')[0] if title else '',country='NZ',address=plain(addresses[0]) if len(addresses)==1 else '',latitude=latitudes[0] if len(latitudes)==1 else '',longitude=longitudes[0] if len(longitudes)==1 else '',website=html.unescape(website.group(1)) if website else '',phone=plain(phone.group(1)) if phone else '',description=plain(description.group(1)) if description else '',source_url=url,source_updated=plain(updated.group(1)) if updated else '',provider_maintained='true' if 'This information is reviewed and edited by' in page else 'false',has_hours='true' if re.search(r'Open today|Open [A-Za-z]+|Mon.*?Fri|Monday',page,re.S) else 'false',premises_count=len(locations) if locations else len(addresses),locations=locations,review_note='Multiple/missing physical addresses or coordinates; inspect source before admission' if len(addresses)!=1 or len(latitudes)!=1 else 'Directory evidence available; compare identity and address with existing stores and practice website')


def main():
    links=json.loads((OUT/'links.json').read_text());pages=OUT/'pages';pages.mkdir(exist_ok=True)
    def run(path):
        url='https://www.healthpoint.co.nz'+path;file=pages/(path.rstrip('/').rsplit('/',1)[-1]+'.html')
        try:
            if file.exists():page=file.read_text()
            else:
                with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (public optical coverage research)'}),timeout=35) as r:page=r.read().decode('utf-8','replace')
                file.write_text(page)
            return parse_page(page,url)
        except Exception as e:return dict(id=path,source_url=url,review_note=f'Public directory could not be fetched: {type(e).__name__}')
    with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(run,links))
    (OUT/'records.json').write_text(json.dumps(rows,indent=2)+'\n')
    fields=sorted({k for r in rows for k in r})
    csv_data=[{k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows]
    with (OUT/'records.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(csv_data)
    print(json.dumps(dict(pages=len(rows),single_premises=sum(bool(r.get('address') and r.get('latitude')) for r in rows),with_website=sum(bool(r.get('website')) for r in rows))))


if __name__=='__main__':main()
