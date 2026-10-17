"""Compare Finest Football's physical subject rows and scoped guide statements."""
import hashlib,json,re
from pathlib import Path
from pypdf import PdfReader
from official_odds_layout import physical_odds_pdf
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-topps-finest-football'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');compact=lambda s:re.sub(r'\s+','',s)
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_finest_football_2025.py'
heads={compact(r[0]) for r in d['rows']}|{'BASE','INSERT','AUTOGRAPH'}
for pn,page in enumerate(PdfReader(path).pages,1):
 notes={compact(n[1]) for n in d['sourceDocumentNotes'] if n[0]==str(pn)}
 actual=[compact(line) for line in page.extract_text().splitlines() if compact(line) and compact(line) not in heads|notes]
 expected=[compact(r[1]+r[2]+r[4]+r[5]) for r in d['rows'] if r[3]==str(pn)]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b])
assert len(d['rows'])==len({tuple(r[:2]) for r in d['rows']})==788 and len({r[0] for r in d['rows']})==24
assert sum(r[5]=='Rookie' for r in d['rows'])==212
assert {r[1] for r in d['rows'] if r[0].startswith('BASE CARDS ')}=={str(i) for i in range(1,301)}
assert len([r for r in d['rows'] if r[0]=='92 FINEST'])==44
assert not any(r[1]=='92' and r[2]=='FINEST' for r in d['rows'])
assert next(r for r in d['rows'] if r[0]=='BASE CARDS UNCOMMON' and r[1]=='195')[4]=='Indianapolis Colts'
assert d['rows'][-1]==['FINEST FANS AUTOGRAPHS','FAN-SC','Stephen Curry','17','Carolina Panthers','']
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
o,f,raw,issues=physical_odds_pdf(op)
assert o==d['officialOddsTable'] and f==d['formats']==['Hobby','Breaker Delight'] and len(o)==228 and not issues
assert [(x['name'],x['values'],x['page']) for x in o]==[(x['name'],x['values'],x['page']) for x in d['odds']]
assert o[0]['values']=={'Hobby':'6:1','Breaker Delight':None} and d['oddsUnitsPublished'] is False
assert not d['parallelSpecifications'] and not any(x.get('numbering') for x in d['odds'])
examples=[x for x in d['publishedSpecifications'] if 'Card number' in x['headers']]
assert sum(len(s['rows']) for s in examples)==5
assert next(s for s in examples if s['name']=='FINEST FANS AUTOGRAPHS')['rows'][0][:4]==['FAN-SC','Stephen Curry','Gold Auto','/50']
assert next(s for s in examples if s['name']=='FLASHBACK AUTOGRAPHS')['rows'][0][:4]==['FBA-BN','Bo Nix','Parallel not named','Limited to 25 copies']
for spec in d['publishedSpecifications']:assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
r=next(s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert r['year']=='2025' and r['releaseDate']=='2026-05-15' and r['verifiedRelease']['statement'].endswith('dropped on May 15')
print('Verified 788 original Finest Football subjects / 24 sections / 212 Rookie marks, numeric-leading 92 FINEST heading, all 228 literal odds categories, five card-specific examples and May 15, 2026 official release.')
