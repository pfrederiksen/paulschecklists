"""Independently compare every Cosmic Football subject and original odds cell."""
import collections,hashlib,json,re
from pathlib import Path
from pypdf import PdfReader
from official_odds_layout import physical_odds_pdf
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-topps-cosmic-chrome-football'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
compact=lambda s:re.sub(r'\s+','',s)
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_cosmic_football_2025.py'
heads={compact(r[0]) for r in d['rows']}|{'BASE','INSERT','AUTOGRAPH'}
for pn,page in enumerate(PdfReader(path).pages,1):
    notes={compact(n[1]) for n in d['sourceDocumentNotes'] if n[0]==str(pn)}
    actual=[compact(line) for line in page.extract_text().splitlines() if compact(line) and compact(line) not in heads|notes]
    expected=[compact(r[1]+r[2]+r[4]+r[5]) for r in d['rows'] if r[3]==str(pn)]
    assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b])
assert len(d['rows'])==878 and len({tuple(r[:2]) for r in d['rows']})==863
assert len({r[0] for r in d['rows']})==18 and d['originalSubjectRows']==d['rows']
assert sum(r[5]=='Rookie' for r in d['rows'])==373
base=[r for r in d['rows'] if r[0] in {'BASE CARDS','ROOKIES'}]
assert len(base)==200 and {r[1] for r in base}=={str(i) for i in range(1,201)}
assert next(r for r in base if r[1]=='37')[4]=='Green Bay Packers'
assert next(r for r in base if r[1]=='43')[4]=='Indianapolis Colts'
clusters=[r for r in d['rows'] if r[0]=='STAR CLUSTERS']
assert collections.Counter(r[1] for r in clusters)=={f'SC-{i}':2 for i in range(1,16)}
assert [(r[2],r[4],r[5]) for r in clusters if r[1]=='SC-1']==[('Cam Ward','Tennessee Titans','Rookie'),('Caleb Williams','Chicago Bears','')]
assert d['rows'][-1]==['FIRST FLIGHT SIGNATURES','FFS-WH','Will Howard','18','Pittsburgh Steelers','Rookie']
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
odds,formats,raw,issues=physical_odds_pdf(op)
assert odds==d['officialOddsTable'] and formats==d['formats']==['Hobby','Lunar'] and not issues
assert [(o['name'],o['values'],o['page']) for o in odds]==[(o['name'],o['values'],o['page']) for o in d['odds']]
assert len(odds)==113 and d['oddsUnitsPublished'] is False and d['formatNamesPublished'] is True
assert next(o for o in odds if o['name']=='Base')['values']=={'Hobby':'3:1','Lunar':'3:1'}
assert next(o for o in odds if o['name']=='Base Lunar Eclipse Refractor')['values']=={'Hobby':None,'Lunar':'1:3'}
assert next(o for o in odds if o['name']=='Supernova Superfractor')['values']['Hobby']=='1:47967'
assert len(d['parallelSpecifications'])==4
assert {s['family'] for s in d['parallelSpecifications']}=={'BASE CARDS','ROOKIES'}
assert {s['numbering'] for s in d['parallelSpecifications']}=={'/199','1/1'}
examples=next(s for s in d['publishedSpecifications'] if s['name']=='EQUINOX AUTOGRAPHS')
assert examples['headers']==['Card number','Name','Parallel / variation','Published statement','Qualification']
assert [r[:4] for r in examples['rows']]==[['EQA-TB','Tom Brady','Red Flare Refractor','Five-copy print limit'],['EQA-CWI','Caleb Williams','Orange Galactic Parallel','Numbered to 25']]
assert 'serial marking is not stated' in examples['rows'][0][4]
for spec in d['publishedSpecifications']+d['parallelSpecifications']:
    assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
record=next(s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert record['year']=='2025' and not record.get('releaseDate')
print('Verified all 878 physical Cosmic Football rows / 863 identities / 373 Rookie marks, both subjects of all 15 Star Clusters cards, every Hobby/Lunar odds cell and four strictly scoped base limits; autograph examples remain card-specific and release remains undated.')
