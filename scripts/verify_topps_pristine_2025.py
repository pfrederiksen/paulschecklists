"""Independently compare all original Pristine subjects and odds with pypdf."""
import collections, hashlib, json, re
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-topps-pristine-baseball'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text())
path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_pristine_2025.py'
assert d['headers']==['Checklist section','Card number','Name','Source page','Team','Rookie']
compact=lambda s:re.sub(r'\s+','',s)
families={r[0] for r in d['rows']};family=None;actual=[]
for pn,page in enumerate(PdfReader(path).pages,1):
 for line in page.extract_text(extraction_mode='layout').splitlines():
  line=line.strip()
  if not line or line in {'BASE','INSERT','AUTOGRAPH','AUTOGRAPH RELIC'}:continue
  if line in families:family=line;continue
  m=re.fullmatch(r'(\S+)\s+(.+)',line);assert m,(pn,line)
  number,rest=m.groups();cells=re.split(r'\s{2,}',rest)
  assert len(cells) in {2,3},(pn,line,cells)
  cells+=['']*(3-len(cells))
  actual.append([family,number,cells[0],str(pn),cells[1],cells[2]])
assert [[compact(c) for c in r] for r in actual]==[[compact(c) for c in r] for r in d['rows']],'Original physical fields must retain their row and column'
assert len(d['rows'])==814 and len({tuple(r[:2]) for r in d['rows']})==808 and len(families)==18
assert d['rows']==d['originalSubjectRows'] and d['headers']==d['originalSubjectHeaders']
assert {r[1] for r in d['rows'] if r[0]=='BASE CARDS'}=={str(i) for i in range(1,301)}
assert sum(r[5]=='Rookie' for r in d['rows'])==224
duals=[r for r in d['rows'] if r[0]=='PRISTINE PAIR DUAL AUTOGRAPHS']
assert len(duals)==12 and set(collections.Counter(r[1] for r in duals).values())=={2}
assert [r[2] for r in duals if r[1]=='PPDA-JW']==['Dylan Crews','James Wood']
assert [r[4] for r in duals if r[1]=='PPDA-ED']==['Cincinnati Reds®','Kansas City Royals®']
assert next(r for r in d['rows'] if r[:2]==['BASE CARDS','18'])[4]=='Seattle Mariners™'
assert next(r for r in d['rows'] if r[1]=='ASGPP-JS')[4]=='New York Yankees®'
assert d['rows'][-1]==['ROOKIE JUMBO AUTOGRAPH RELICS','RJAR-SS','Spencer Schwellenbach','16','Atlanta Braves™','Rookie']
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
source_odds=[]
for pn,page in enumerate(PdfReader(op).pages,1):
 lines=page.extract_text(extraction_mode='layout').splitlines()
 assert any(re.fullmatch(r'\s*Cards\s+FGC006155 Hobby\s*',line) for line in lines)
 for line in lines:
  m=re.fullmatch(r'\s*(.+?)\s+([\d,]+(?::[\d,]+)+)\s*',line)
  if m:source_odds.append((pn,compact(m[1]),m[2]))
assert source_odds==[(o['page'],compact(o['name']),o['values']['FGC006155 Hobby']) for o in d['officialOddsTable']]
assert len(source_odds)==89 and d['formats']==['FGC006155 Hobby']
assert d['formatNamesPublished'] is True and d['oddsUnitsPublished'] is False
assert [(o['name'],o['values'],o['page']) for o in d['odds']]==[(o['name'],o['values'],o['page']) for o in d['officialOddsTable']]
assert all(o['family'] in families for o in d['odds'])
green=next(o for o in d['odds'] if o['name']=='Pristine Autographs Green Pristine Parallel')
assert green['values']=={'FGC006155 Hobby':'01:16:00'} and not green.get('numbering')
registry=json.loads((ROOT/'data/parallel-specifications.json').read_text());specs=registry['sets'][SLUG]
assert len(specs)==6 and {s['family'] for s in specs}=={'BASE CARDS','PEARLESCENT','AMPED','PROWLERS','MONOGRAM','ALL STAR GAME PRISTINE PIECES AUTOGRAPH RELIC'}
assert all(s['numbering']=='1/1' for s in specs)
for s in specs:
 assert hashlib.sha256((ROOT/s['evidenceFile']).read_bytes()).hexdigest()==s['evidenceSha256']
 assert any(o['name']==s['oddsName'] and o['family']==s['family'] for o in d['odds'])
assert not any(s['family']=='PRISTINE PIECES AUTOGRAPH RELIC' for s in specs)
assert not any(s['family']=='BASE CARDS' and 'Superfractor' in s['name'] for s in specs)
proof=json.loads((ROOT/specs[0]['evidenceFile']).read_text())
assert proof['productLinksMatchGlobalBytes'] and len(proof['boxContents'])==7
for spec in d['publishedSpecifications']:assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
r=next(s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert r['releaseDate']=='2026-02-04' and r['year']=='2025'
assert any(c['slug']==SLUG and 'tri-pack' in c['gap'] for c in registry['conflicts'])
print('Verified every physical subject field: 814 rows / 808 identities / 18 families, 224 Rookie marks, six complete duals, all 89 literal odds and six exact product-specific 1/1 joins; other numbering remains unverified.')
