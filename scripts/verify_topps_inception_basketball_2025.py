"""Independently compare every original Inception subject and odds cell line."""
import collections,hashlib,json,re
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-26-topps-inception-basketball'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text())
path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');compact=lambda s:re.sub(r'\s+','',s)
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_inception_basketball_2025.py'
assert d['headers']==['Checklist section','Card number','Name','Source page','Team','Rookie']
heads={compact(r[0]) for r in d['rows']}|{'BASE','AUTOGRAPH','AUTOGRAPHRELIC','RELIC','INSERT'}|{compact(n[1]) for n in d['sourceDocumentNotes']}
for pn,page in enumerate(PdfReader(path).pages,1):
 actual=[compact(line) for line in page.extract_text().splitlines() if compact(line) and compact(line) not in heads]
 expected=[compact(r[1]+r[2]+r[4]+r[5]) for r in d['rows'] if r[3]==str(pn)]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b],len(actual),len(expected))
assert len(d['rows'])==488 and len({tuple(r[:2]) for r in d['rows']})==458 and len({r[0] for r in d['rows']})==17
assert d['rows']==d['originalSubjectRows'] and sum(r[5]=='Rookie' for r in d['rows'])==268
assert {r[1] for r in d['rows'] if r[0]=='BASE CARDS'}=={str(i) for i in range(1,101)}
assert [r[2] for r in d['rows'] if r[0]=='ROOKIE RELIC BOOKLET AUTOGRAPHS' and r[1]=='RB-KL']==['Kasparas Jakučionis','Liam McNeeley']
assert next(r for r in d['rows'] if r[1]=='RA-YH')[4]=='Portland Trailblazers'
assert next(r for r in d['rows'] if r[1]=='RF-KL')[4]=='Miami Heat'
assert d['rows'][-1]==['SPLASHDOWN','S-20','Tre Johnson III','11','Washington Wizards','Rookie']
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
for pn,page in enumerate(PdfReader(op).pages,1):
 actual=[compact(re.sub(r'(?<!\w)-(?!\w)','',line)) for line in page.extract_text().splitlines() if re.search(r'\d+:[\d,]+(?:\s+-)?\s*$',line)]
 expected=[compact(o['name']+''.join(o['values'][f] or '' for f in ['Hobby','FDI'])) for o in d['officialOddsTable'] if o['page']==pn]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b],len(actual),len(expected))
assert len(d['odds'])==91 and d['formats']==['Hobby','FDI'] and d['oddsUnitsPublished'] is False
assert [(o['name'],o['values'],o['page']) for o in d['odds']]==[(o['name'],o['values'],o['page']) for o in d['officialOddsTable']]
assert next(o for o in d['odds'] if o['name']=='Rookie Autographs Red Electricity')['values']=={'Hobby':None,'FDI':'1:3'}
assert len(d['parallelSpecifications'])==10 and sum(bool(s.get('oddsName')) for s in d['parallelSpecifications'])==9
by=lambda name:next(s for s in d['parallelSpecifications'] if s.get('oddsName')==name)
assert by('Base Purple')['numbering']=='/150'
assert by('Rookie Autographs Red Electricity')['numbering']=='/16'
assert by('Rookie Jumbo Relic Autographs Blue')['numbering']=='/25'
assert not any(s.get('oddsName') in ['Base Gold Electricity','Base Inception','Dawn of Greatness Autographs Blue','Rookie Autographs Horizontal Variations Red Electricity'] for s in d['parallelSpecifications'])
assert next(s for s in d['parallelSpecifications'] if s['name']=='Holo Gold')['numbering']=='/50'
for spec in d['parallelSpecifications']+d['publishedSpecifications']:assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
card=next(s for s in d['publishedSpecifications'] if s['name']=='DAWN OF GREATNESS AUTOGRAPHS');assert card['rows'][0][:4]==['DG-CC','Cedric Coward','Blue','/25']
assert next(s for s in d['publishedSpecifications'] if s['name']=='BASE CARDS')['rows'][0][1]=='Limited to one-of-one'
r=next(s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert r['year']=='2025-26' and r['releaseDate'] is None
print('Verified every Inception Basketball source line: 488 subjects / 458 identities, 268 Rookie marks, 91 Hobby/FDI odds, ten exact specifications and strict card/family/print-limit scope.')
