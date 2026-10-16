"""Independently verify all original Cosmic Basketball rows and literal odds cells."""
import collections,hashlib,json,re
from pathlib import Path
from pypdf import PdfReader
from official_odds_layout import physical_odds_pdf
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-26-topps-cosmic-chrome-basketball'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
compact=lambda s:re.sub(r'\s+','',s)
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_cosmic_basketball_2025.py'
heads={compact(r[0]) for r in d['rows']}|{'BASE','INSERT','AUTOGRAPH'}
for pn,page in enumerate(PdfReader(path).pages,1):
 notes={compact(n[1]) for n in d['sourceDocumentNotes'] if n[0]==str(pn)}
 actual=[compact(line) for line in page.extract_text().splitlines() if compact(line) and compact(line) not in heads|notes]
 expected=[compact(r[1]+r[2]+r[4]+r[5]) for r in d['rows'] if r[3]==str(pn)]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b])
assert len(d['rows'])==777 and len({tuple(r[:2]) for r in d['rows']})==777
assert len({r[0] for r in d['rows']})==19 and d['originalSubjectRows']==d['rows']
assert sum(r[5]=='Rookie' for r in d['rows'])==278
base=[r for r in d['rows'] if r[0] in {'BASE CARDS','BASE CARDS II'}]
assert len(base)==200 and {str(i) for i in range(1,201)}-{r[1] for r in base}=={'48'}
assert [(r[0],r[2],r[4]) for r in base if r[1]=='101']==[('BASE CARDS','Nikola Jović','Miami Heat'),('BASE CARDS II','Darius Garland','Cleveland Cavaliers')]
assert next(r for r in base if r[1]=='24')[2]=='Bennedict mathurin'
assert next(r for r in base if r[1]=='157')[2]=='Lebron James'
assert next(r for r in d['rows'] if r[1]=='GG-28')[4]=='New Jersey Nets'
assert d['rows'][-1]==['COSMIC CHROME AUTOGRAPH VARIATION II','CCAV-SGA','Shai Gilgeous-Alexander','16','Oklahoma City Thunder','']
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
odds,formats,raw,issues=physical_odds_pdf(op)
assert odds==d['officialOddsTable'] and formats==d['formats']==['Hobby'] and not issues
assert [(o['name'],o['values'],o['page']) for o in odds]==[(o['name'],o['values'],o['page']) for o in d['odds']]
assert len(odds)==126 and d['oddsUnitsPublished'] is False and d['formatNamesPublished'] is True
assert next(o for o in d['odds'] if o['name']=='Base')['values']=={'Hobby':'3:1'}
assert all(o['familyAliases']==['BASE CARDS II'] for o in d['odds'] if o['family']=='BASE CARDS')
assert next(o for o in d['odds'] if o['name']=='Cosmic Chrome Autograph Variation II Refractor')['family']=='COSMIC CHROME AUTOGRAPH VARIATION II'
assert len(d['parallelSpecifications'])==51
singularity=[s for s in d['parallelSpecifications'] if s['family']=='SINGULARITY SIGNATURES']
assert [s['numbering'] for s in singularity]==['/50','/25','/10','/5','1/1']
assert not any(s['family'] in {'SPACE WALK','ALIEN AUTOGRAPHS','FIRST FLIGHT SIGNATURES REFRACTOR','COSMIC CHROME AUTOGRAPH VARIATION II'} for s in d['parallelSpecifications'])
for spec in d['publishedSpecifications']+d['parallelSpecifications']:
 assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
record=next(s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert record['year']=='2025-26' and record['releaseDate']=='2026-04-29'
assert record['verifiedRelease']['statement'].endswith('arriving April 29, 2026.')
print('Verified 777 original Cosmic Basketball rows / 19 families, 278 exact Rookie flags, duplicate printed 101 / missing 48, every physical Hobby odds cell, 51 scoped guide limits and April 29 release evidence.')
