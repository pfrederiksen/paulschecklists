"""Independently check every NBL source line, original column and odds cell."""
import collections,hashlib,json,re
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-26-topps-nbl-basketball'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
compact=lambda s:re.sub(r'\s+','',s)
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
heads={compact(r[0]) for r in d['rows']}|{'BASE','INSERT','AUTOGRAPH','RELIC'}
for pn,page in enumerate(PdfReader(path).pages,1):
 actual=[compact(line) for line in page.extract_text().splitlines() if compact(line) and compact(line) not in heads and not line.startswith(('Checklists provided','of production,'))]
 expected=[compact(r[1]+r[2]+r[4]+r[5]) for r in d['rows'] if r[3]==str(pn)]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b])
assert len(d['rows'])==323 and len({r[0] for r in d['rows']})==12
assert len({tuple(r[:2]) for r in d['rows']})==323
assert d['originalSubjectRows']==d['rows']
assert {int(r[1]) for r in d['rows'] if r[0]=='BASE CARDS'}==set(range(1,101))
assert {r[1] for r in d['rows'] if r[5]=='Rookie'}=={'12','19','21','28','50','61','62','C-3','C-11','OA-18','NS-2','NS-3','NA-DD','NA-NKH','NA-RS','NR-AD','NR-DD','NR-RS'}
assert next(r for r in d['rows'] if r[1]=='ATG-WG')[2:]==['Warrick Giddey','6','Melbourne Tigers','']
assert next(r for r in d['rows'] if r[1]=='NA-PJC')[2]=='Parker Jackson-Cartwright'
assert d['rows'][-1]==['NBL RELICS','NR-ZC','Zylan Cheatham','8','Adelaide 36ers','']
assert d['formats']==['Hobby SKU'] and d['oddsUnitsPublished'] is False and d['formatNamesPublished'] is True
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
for pn,page in enumerate(PdfReader(op).pages,1):
 lines=[compact(line) for line in page.extract_text().splitlines()]
 actual=lines[lines.index('HobbySKU')+1:]
 expected=[compact(v) for o in d['odds'] if o['page']==pn for v in [o['name'],o['values']['Hobby SKU']]]
 assert actual==expected,(pn,actual,expected)
assert len(d['odds'])==48 and not d['oddsIssues'] and not d['parallelSpecifications']
assert [(o['name'],o['values'],o['page']) for o in d['odds']]==[(o['name'],o['values'],o['page']) for o in d['officialOddsTable']]
assert {o['family'] for o in d['odds']}=={r[0] for r in d['rows']}
assert next(o for o in d['odds'] if o['name']=='Base')['values']=={'Hobby SKU':'3:1'}
assert next(o for o in d['odds'] if o['name']=='Glass & Grit')['family']=='GLASS AND GRIT'
assert next(o for o in d['odds'] if o['name']=='All-Time Greats Autographs')['family']=='ALL TIME GREATS AUTOGRAPH'
for spec in d['publishedSpecifications']:assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
r=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG)
assert r['releaseDate'] is None and r['year']=='2025-26' and r['dedicatedParser']=='scripts/import_topps_nbl_2025.py'
assert d['publishedSpecifications'][0]['rows'][-1][1]=='2026-06-25'
print('Verified all 323 NBL physical rows / 12 sections, 18 exact Rookie marks, original teams and all 48 Hobby SKU literals. Store availability, ratio units and unverified numbering remain scoped.')
