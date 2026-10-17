"""Independently verify all original Finest Basketball subjects and odds literals."""
import hashlib,json,re
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-26-topps-finest-basketball'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');compact=lambda s:re.sub(r'\s+','',s)
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_finest_basketball_2025.py'
assert d['headers']==['Checklist section','Card number','Name','Source page','Team']
heads={compact(r[0]) for r in d['rows']}|{'BASE','INSERT','AUTOGRAPH'}
for pn,page in enumerate(PdfReader(path).pages,1):
 actual=[compact(line) for line in page.extract_text().splitlines() if compact(line) and compact(line) not in heads]
 expected=[compact(r[1]+r[2]+r[4]) for r in d['rows'] if r[3]==str(pn)]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b])
assert len(d['rows'])==len({tuple(r[:2]) for r in d['rows']})==764 and len({r[0] for r in d['rows']})==17
assert d['rows']==d['originalSubjectRows'] and 'Rookie' not in d['headers']
assert {r[1] for r in d['rows'] if r[0] in {'BASE COMMON','BASE UNCOMMON','BASE RARE'}}=={str(i) for i in range(1,301)}
assert next(r for r in d['rows'] if r[1]=='145')[2]=='Cade Cunnigham'
assert next(r for r in d['rows'] if r[1]=='191')[4]=='Philadelpia 76ers'
assert next(r for r in d['rows'] if r[1]=='200')[4]=='Seattle Supersonics'
assert next(r for r in d['rows'] if r[1]=='117')[2]=='Hugo Gonza\u0301lez'
assert next(r for r in d['rows'] if r[1]=='MA-YH')[4]=='Portland Trailblazers'
assert d['rows'][-1]==['COLOSSAL SHOTS AUTOGRAPHS','CS-YK','Yanic Konan-Niederhäuser','16','Los Angeles Clippers']
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
for pn,page in enumerate(PdfReader(op).pages,1):
 actual=[compact(line) for line in page.extract_text().splitlines() if compact(line) and compact(line)!='SubsetHobbyBreaker']
 expected=[compact(o['name']+''.join(o['values'][f] or '' for f in ['Hobby','Breaker'])) for o in d['officialOddsTable'] if o['page']==pn]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b])
assert len(d['odds'])==217 and d['formats']==['Hobby','Breaker'] and d['oddsUnitsPublished'] is False
assert [(o['name'],o['values'],o['page']) for o in d['officialOddsTable']]==[(o['name'],o['values'],o['page']) for o in d['odds']]
assert d['odds'][0]['values']=={'Hobby':'5:1','Breaker':None}
assert next(o for o in d['odds'] if o['name']=='Base Common Geometric')['values']=={'Hobby':None,'Breaker':'2:1'}
assert not d['parallelSpecifications'] and not any(o.get('numbering') for o in d['odds'])
for spec in d['publishedSpecifications']:assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
flag=next(s for s in d['publishedSpecifications'] if s['name']=='Unjoined Cooper Flagg pull-report example')
assert flag['rows'][0][:3]==['Cooper Flagg','Black Geometric','1/1'] and 'no printed number or tier' in flag['rows'][0][3]
rc=next(s for s in d['publishedSpecifications'] if s['name']=='BASE COMMON');assert rc['rows'][0][:2]==['1','Cooper Flagg']
r=next(s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert r['year']=='2025-26' and r['releaseDate']=='2026-02-26'
print('Verified every original Finest Basketball subject and odds line: 764 cards / 17 sections, original team spellings and combining accents, 217 Hobby/Breaker categories, literal 5:1 and 2:1, no invented rookie flags or cross-tier numbering.')
