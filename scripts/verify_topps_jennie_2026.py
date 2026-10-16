"""Independently compare every Jennie card and odds literal with original PDF text."""
import collections,hashlib,json,re
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-chrome-x-jennie'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
compact=lambda s:re.sub(r'\s+','',s)
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
heads={compact(r[0]) for r in d['rows']}
for pn,p in enumerate(PdfReader(path).pages,1):
 actual=[]
 for line in p.extract_text().splitlines():
  t=compact(line)
  if not t or t in heads or t.startswith(('Checklistsprovided','productatthetime','2026ToppsChromexJennie')):continue
  actual.append(t)
 assert actual==[compact(r[1]+r[2]) for r in d['rows'] if r[3]==str(pn)],(pn,actual)
assert len(d['rows'])==68 and len(set(tuple(r[:2]) for r in d['rows']))==68
assert len({r[0] for r in d['rows']})==10 and d['originalSubjectRows']==d['rows']
assert [r[1] for r in d['rows'] if r[0]=='BASE']==[str(n) for n in range(1,31)]
assert next(r for r in d['rows'] if r[1]=='RSSP')==['RUBY SUPER SHORT PRINT','RSSP','Jennie','3']
assert next(r for r in d['rows'] if r[1]=='RSSP-A')==['RUBY SSP AUTOGRAPH VARIATION','RSSP-A','Jennie','3']
assert d['headers']==['Checklist section','Card number','Subject','Source page'] and not d['unclassifiedLines']
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
actual=[]
for pn,p in enumerate(PdfReader(op).pages,1):
 for line in p.extract_text().splitlines():
  if compact(line)=='COMPONENTOdds(PerPack)':continue
  m=re.fullmatch(r'\s*(.+?)\s+(1:[\d,]+)\s*',line);assert m,(pn,line)
  actual.append((pn,m[1].strip(),m[2]))
assert actual==[(o['page'],o['name'],o['values']['Odds (Per Pack)']) for o in d['odds']]
assert len(actual)==58 and d['formatNamesPublished'] is False and d['oddsUnitsPublished'] is True
by={o['name']:o for o in d['odds']};assert by['MONOCHROME MEMENTOS SUPERFRACTOR PARALLEL']['values']=={'Odds (Per Pack)':'1:15,000'}
assert by['MONOCHROME MEMENTOS RED PARALLEL']['values']=={'Odds (Per Pack)':'1:3,062'}
assert by['RUBY SHORT PRINTS']['values']=={'Odds (Per Pack)':'1:31'}
assert by['RUBY SUPER SHORT PRINTS']['family']=='RUBY SUPER SHORT PRINT'
specs=d['parallelSpecifications'];assert len(specs)==51 and sum('oddsName' in s for s in specs)==50
numbering={(s['family'],s['name']):s['numbering'] for s in specs}
for key,value in [(('BASE','Teal Refractor'),'/299'),(('BASE','Orange Refractor'),'/25'),(('CHROMIUM CLOSE-UPS INSERT','Aqua Refractor'),'/199'),(('MONOCHROME MEMENTOS INSERT','Gold Refractor'),'/50'),(('CONCERT RELICS','Purple Foil'),'/75'),(('CONCERT AUTOGRAPH-RELICS','Black Refractor'),'/10')]:assert numbering[key]==value
assert not any(s['family'] in {'RUBY SHORT PRINTS','RUBY SUPER SHORT PRINT'} for s in specs)
assert not any(s.get('oddsName')=='AUTOGRAPH RELIC FOILFRACTOR PARALLEL' for s in specs)
assert next(s for s in specs if s['family']=='CONCERT AUTOGRAPH-RELICS' and s['name']=='Superfractor').get('oddsName') is None
assert by['AUTOGRAPH RELIC FOILFRACTOR PARALLEL']['values']=={'Odds (Per Pack)':'1:150,000'}
for s in specs:assert hashlib.sha256((ROOT/s['evidenceFile']).read_bytes()).hexdigest()==s['evidenceSha256']
r=next(s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert r['dedicatedParser']=='scripts/import_topps_jennie_2026.py' and r['rowCount']==68 and r['sections']==10 and r['odds']==58
assert r['releaseDate']=='2026-10-20' and r['releaseStatus']=='Upcoming'
print('Verified every Jennie physical subject and odds against independent PDF text: 68 cards / ten sections, 58 per-pack categories, 51 scoped specifications / 50 exact joins; autograph-relic name conflict remains explicit.')
