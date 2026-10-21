"""Check every UConn PDF row independently against original draw-order text."""
import collections
import csv
import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SLUG = 'panini-2025-panini-uconn-box-set-basketball'
data = json.loads((ROOT/f'data/imports/{SLUG}.json').read_text())
record = next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG)
proof = data['sourceObservation']
assert hashlib.sha256((ROOT/proof['file']).read_bytes()).hexdigest()==proof['sha256']
observed = json.loads((ROOT/proof['file']).read_text())


def original_rows(path):
    rows, family, pending = [], None, ''
    for page_number, page in enumerate(PdfReader(path).pages, 1):
        for printed in page.extract_text().splitlines():
            line = re.sub(r'\s+', ' ', pending+printed).strip()
            pending = ''
            if line=='\uf0a3':
                pending = line+' '
                continue
            if line.startswith('\uf0a3'):
                match = re.fullmatch(r'\uf0a3\s*(\S+)\s+(.+?)(?:\s+(SSP|SP))?',line)
                assert match, line
                rows.append([family,match[1],match[2],match[3] or '',str(page_number)])
            elif line in observed.get('headings',data['printedHeadings']):
                family = line
    assert not pending
    return rows


for source in [observed['primary'],observed['alternate']]:
    raw = (ROOT/source['file']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==source['sha256'] and len(raw)==source['bytes']
    rows = original_rows(ROOT/source['file'])
    assert len(rows)==source['rows']
    if source is observed['primary']:
        assert rows==data['rows'], 'Physical-column extraction must match every original draw-order card and mark'
    else:
        assert not (collections.Counter(tuple(r[:4]) for r in rows)-collections.Counter(tuple(r[:4]) for r in data['rows']))
assert len(data['rows'])==record['rowCount']==169 and record['sections']==14
assert collections.Counter(r[3] for r in data['rows'])=={'':117,'SP':34,'SSP':18}
assert len([r for r in data['rows'] if r[0]=='PRIVATE SIGNINGS'])==49
assert [r[3] for r in data['rows'] if r[0]=='PRIVATE SIGNINGS' and r[1]=='AK']==['','SP']
assert {r[2] for r in data['rows'] if r[0]=='PRIVATE SIGNINGS' and r[1]=='AS'}=={'Adama Sanogo','Ashlynn Shade'}
assert {r[2] for r in data['rows'] if r[0]=='PRIVATE SIGNINGS' and r[1]=='SD'}=={'Souleymane Diaby','Stefanie Dolson'}
assert ['CAMPUS LEGENDS','DH','Dan Hurley','SP','1'] in data['rows']
assert data['rows'][-1]==['PRIVATE SIGNINGS','TN','Tristen Newton','','2']
assert 'PINNACLE MASCOT' in data['printedHeadings'] and not any(r[0]=='PINNACLE MASCOT' for r in data['rows'])
assert not data.get('odds') and not data.get('formats')
assert all(spec['headers']==['Field','Value','Scope / qualifier','Official source'] for spec in data.get('publishedSpecifications',[]))
assert data.get('metricColumn') is None and record['releaseDate'] is None and not record['parallelData']
csv_proof = data['headerOnlyCsvEvidence']
assert hashlib.sha256((ROOT/csv_proof['file']).read_bytes()).hexdigest()==csv_proof['sha256']
assert list(csv.reader((ROOT/csv_proof['sourceExport']).read_text().splitlines()))==[['SPORT','YEAR','BRAND','PROGRAM','CARD SET','ATHLETE','TEAM','POSITION','CARD NUMBER','SEQUENCE']]
assert data['guideReview']==record['guideReview']
guide=data['guideReview'];assert hashlib.sha256((ROOT/guide['file']).read_bytes()).hexdigest()==guide['sha256']
for slug,season in [('panini-2025-panini-prizm-black-24-25-basketball','2024-25'),('panini-2025-panini-2025-26-euroleague-contenders-basketball','2025-26'),('panini-2025-panini-donruss-25-26-basketball','2025-26')]:
    r=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==slug)
    d=json.loads((ROOT/r['tableData']).read_text())
    assert r['year']==d['productYear']==season and r['sourceYear']==d['sourceYear']=='2025'
    assert r['title'].startswith(season+' Panini ') and r['releaseDate'] is None
    assert all(row[5]=='2025' for row in d['rows'])
print('Verified all 169 UConn entries against independent PDF draw-order text, 108 matching alternate rows, repeated codes, SP/SSP marks, empty heading and header-only CSV; explicit program seasons remain separate from source year and release date.')
