"""Independently compare every Definitive subject, original team and odds literal."""
import collections,copy,hashlib,json,re,sys
from pathlib import Path
from pypdf import PdfReader
import pdfplumber
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-26-topps-definitive-basketball'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());p=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');compact=lambda s:re.sub(r'\s+','',s)
assert hashlib.sha256(p.read_bytes()).hexdigest()==d['sha256']
heads={compact(r[0]) for r in d['rows']}|{'AUTOGRAPHRELIC','AUTOGRAPH','RELIC'}
for pn,page in enumerate(PdfReader(p).pages,1):
 actual=[compact(l) for l in page.extract_text().splitlines() if compact(l) and compact(l) not in heads and not l.startswith(('Checklist-Checklists','at the time of production'))]
 expected=[compact(r[1]+r[2]+r[4]+r[5]) for r in d['rows'] if r[3]==str(pn)]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b])
assert len(d['rows'])==1024 and len({r[0] for r in d['rows']})==27 and len({tuple(r[:2]) for r in d['rows']})==979
assert sum(r[5]=='Rookie' for r in d['rows'])==298 and d['originalSubjectRows']==d['rows']
assert d['rows'][0]==['DEFINITIVE AUTOGRAPH RELICS','DAR-AIV','Allen Iverson','1','Philadelphia 76ers','']
assert d['rows'][-1]==['DEFINITIVE NAMEPLATE II','DNP-VE9','VJ Edgecombe','15','Philadelphia 76ers','Rookie']
assert [r[2] for r in d['rows'] if r[:2]==['TRIPLE AUTOGRAPHS','TRP-JTC']]==['Tyrese Haliburton','Cade Cunningham','Jalen Brunson']
assert [r[4] for r in d['rows'] if r[:2]==['TRIPLE AUTOGRAPHS','TRP-JTC']]==['Indiana Pacers','Detroit Pistons','New York Knicks']
assert sum(r[0]=='DEFINITIVE NAMEPLATE I' for r in d['rows'])==100 and sum(r[0]=='DEFINITIVE NAMEPLATE II' for r in d['rows'])==84
op=p.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
assert d['formats']==['HOBBY','FDI'] and d['formatNamesPublished'] and d['oddsUnitsPublished'] is False
with pdfplumber.open(op) as pdf:
 original=[]
 for pn,page in enumerate(pdf.pages,1):
  tables=page.find_tables();assert len(tables)==1;cells=tables[0].extract();assert cells[0]==['Card','HOBBY','FDI']
  for row in cells[1:]:original.append((pn,[' '.join((v or '').split()) for v in row]))
 expected=[(o['page'],[o['name'],o['values']['HOBBY'] or '-',o['values']['FDI'] or '-']) for o in d['officialOddsTable']]
 assert original==expected
assert len(d['odds'])==141 and not d['oddsIssues']
assert [(o['name'],o['values'],o['page']) for o in d['odds']]==[(o['name'],o['values'],o['page']) for o in d['officialOddsTable']]
assert {o['family'] for o in d['odds']}=={r[0] for r in d['rows']}
assert next(o for o in d['odds'] if o['name']=='DEFINITIVE NAMEPLATE TWO')['family']=='DEFINITIVE NAMEPLATE II'
assert next(o for o in d['odds'] if o['name']=='DEFINITIVE ROOKIE PATCH AUTOGRAPHS FIRST DAY ISSUE')['values']=={'HOBBY':None,'FDI':'1:1'}
assert next(o for o in d['odds'] if o['name']=='TRIPLE ROOKIE AUTOGRAPHS GOLD')['values']=={'HOBBY':'1:1,266','FDI':None}
assert len(d['parallelSpecifications'])==7 and all(s['numbering']=='1/1' for s in d['parallelSpecifications'])
assert not any('BLUE' in s['oddsName'] or s['family']=='TRIPLE AUTOGRAPHS' for s in d['parallelSpecifications'])
examples=[t for t in d['publishedSpecifications'] if 'Card-specific numbering' in t['headers']]
assert len(examples)==8 and any(t['name']=='DEFINING IMAGES AUTOGRAPHS' and t['rows']==[['DIA-CF','Cooper Flagg','Blue','/2','Guide example applies to this named subject and parallel only.']] for t in examples)
for t in d['publishedSpecifications']:assert hashlib.sha256((ROOT/t['evidenceFile']).read_bytes()).hexdigest()==t['evidenceSha256']
r=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG);assert r['releaseDate'] is None and r['year']=='2025-26'
sys.path.insert(0,str(ROOT/'scripts'));from import_official_catalog import run
assert run(copy.deepcopy(r))==r
print('Verified every Definitive source row: 1,024 subjects / 979 identities / 27 families, 298 Rookie marks, all 141 two-column odds and seven exact 1/1 joins; examples remain card-specific.')
