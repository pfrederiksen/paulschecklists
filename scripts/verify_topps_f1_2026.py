"""Check ruled F1 source cells, seven-column odds grid and exact format scopes."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
from pypdf import PdfReader
from official_odds_layout import physical_odds_pdf
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-chrome-formula-1'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_f1_2026.py' and d['importKind']=='topps-grid-pdf'
assert len(d['rows'])==604 and len({r[0] for r in d['rows']})==33 and sum(not r[2] for r in d['rows'])==12
# Independently inspect literal cells, preserving the source's original six-column order.
with pdfplumber.open(path) as pdf:
 expected=[]
 for pn,page in enumerate(pdf.pages,1):
  for table in page.extract_tables():
   for r in table:
    if r[0]=='Card Number':continue
    r=[v or '' for v in r];expected.append([r[3],*r,str(pn)])
 assert expected==d['rows']==d['originalSubjectRows']
assert {r[1] for r in d['rows'] if r[0].startswith('BASE CARDS - ')}=={str(i) for i in range(1,201)}
assert next(r for r in d['rows'] if r[1]=='150')[2]==''
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
o,f,raw,issues=physical_odds_pdf(op)
assert o==d['officialOddsTable'] and f==d['formats']==['HOBBY','FDI','SAPPHIRE','VALUE','MEGA','HONGBAO','LOGOFRACTOR'] and len(o)==174 and not issues
assert [(x['name'],x['values'],x['page']) for x in o]==[(x['name'],x['values'],x['page']) for x in d['odds']]
assert d['oddsUnitsPublished'] is False and all(x['values'][fmt] is None for fmt in ['SAPPHIRE','HONGBAO','LOGOFRACTOR'] for x in o)
full=next(x for x in d['odds'] if x['name']=='BASE FULL GRID REFRACTOR PARALLEL');assert len(full['familyAliases'])==11 and full['family']=='BASE CARDS - F1® DRIVERS'
superfractor=next(x for x in d['odds'] if x['name']=='BASE SUPERFRACTOR PARALLEL');assert len(superfractor['familyAliases'])==11
assert {x['family'] for x in d['odds']}|set(superfractor['familyAliases'])=={r[0] for r in d['rows']}
assert next(x for x in o if x['name']=='VUELTA 1 SUPERFRACTOR PARALLEL')['values']['HOBBY']=='1:51,909'
assert len(d['parallelSpecifications'])==5
for spec in d['parallelSpecifications']:assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
assert not any(x.get('numbering') for x in d['odds'] if x['name']=='BASE PURPLE REFRACTOR PARALLEL')
r=next(s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert r['releaseStatus']=='Released' and r['releaseDate']=='2026-10-15' and r['verifiedRelease']['statement']=='Street date: October 15, 2026'
print('Verified 604 ruled F1 checklist rows / 12 blank names, all 174 odds categories / seven original columns, blank variant values, explicit family aliases, five scoped numbering joins and separate official variant dates.')
