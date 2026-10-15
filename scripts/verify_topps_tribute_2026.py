"""Independently verify Tribute source text objects and physical cell fields."""
import hashlib
import json
import logging
import re
from pathlib import Path
from pypdf import PdfReader

logging.getLogger('pypdf').setLevel(logging.ERROR)
ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2026-topps-tribute-baseball'
data=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text())
path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
assert hashlib.sha256(path.read_bytes()).hexdigest()==data['sha256']
assert data['dedicatedParser']=='scripts/import_topps_tribute_2026.py'
assert data['headers']==['Checklist section','Card number','Name','Team','Rookie','Source page']
assert len(data['rows'])==786 and len({r[0] for r in data['rows']})==22
assert data['originalSubjectRows']==data['rows']
norm=lambda s:re.sub(r'\s+','',s)
headers={r[0] for r in data['rows']}
source=[];family=None
reader=PdfReader(path);assert len(reader.pages)==16
for pn,page in enumerate(reader.pages,1):
    for line in page.extract_text(extraction_mode='layout').splitlines():
        line=line.strip()
        if not line:continue
        if line in headers:family=line;continue
        if line in {'BASE','INSERT','AUTOGRAPH','AUTOGRAPH RELIC','RELIC'}:continue
        if pn==1 and family is None:continue
        match=re.fullmatch(r'(\S+)\s+(.+)',line);assert match,(pn,line)
        number,rest=match.groups()
        cells=re.split(r'\s{2,}',rest)
        assert len(cells)<=3,(pn,line,cells)
        cells+=['']*(3-len(cells))
        source.append([norm(family),norm(number),*map(norm,cells),str(pn)])
assert source==[[norm(c) for c in row] for row in data['rows']],'Every original text object must remain in its physical row/column'
base=[r for r in data['rows'] if r[0]=='BASE CARDS']
assert len(base)==100 and {int(r[1]) for r in base}==set(range(1,101))
assert len({tuple(r[:2]) for r in data['rows']})==723
assert sum(r[4]=='Rookie' for r in data['rows'])==104
blank=[r for r in data['rows'] if not r[3]]
assert len(blank)==15 and {r[2] for r in blank}=={'Joe Buck','Michael Kay','Joe Davis','Dave Sims','Don Orsillo'}
assert all(r[0]=='CALLING THE SHOT DUAL AUTOGRAPHS' for r in blank)
assert [r[2:4] for r in data['rows'] if r[1]=='DR-TM']==[['Eddie Murray','Cleveland'],['Jim Thome','Cleveland']]
assert next(r for r in data['rows'] if r[1]=='TTR-Jd')[2]=='Jacob deGrom'
assert next(r for r in data['rows'] if r[1]=='PPA-SO')[3]=='Angels®'
assert next(r for r in data['rows'] if r[1]=='PPA-SHO')[3]=='Los Angeles Dodgers®'
for family in ['TRIBUTE CAREER ACHIEVEMENT AWARD CONTINUITY BARRY BONDS','TRIBUTE CAREER ACHIEVEMENT AWARD CONTINUITY BARRY BONDS AUTO']:
    assert len([r for r in data['rows'] if r[0]==family])==20
assert [r[2] for r in data['rows'] if r[1]=='TTDA-BG']==['Ken Griffey Jr.','Barry Bonds']
assert len(data['odds'])==143 and data['formats']==['Hobby']
assert data['formatNamesPublished'] is True and data['oddsUnitsPublished'] is False
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==data['oddsSha256']
# pypdf's layout pass independently rebuilds the original text matrices;
# it does not use the importer's pdfplumber row boxes or object-origin joins.
literal=[]
reader=PdfReader(op)
for pn,page in enumerate(reader.pages,1):
    lines=page.extract_text(extraction_mode='layout').splitlines()
    assert any(re.fullmatch(r'\s*Card\s+Hobby\s*',line) for line in lines)
    for line in lines:
        match=re.fullmatch(r'\s*(.+?)\s+([\d,.]+(?::[\d,.]+)+)\s*',line)
        if match:literal.append((pn,norm(match[1]),norm(match[2])))
assert literal==[(o['page'],norm(o['name']),norm(o['values']['Hobby'])) for o in data['odds']]
unjoined=[o for o in data['odds'] if not o.get('family')]
assert len(unjoined)==3 and all(o['name'].startswith('2026 Tribute Career Achievement Award Continuity') for o in unjoined)
assert next(o for o in data['odds'] if o['name']=='Calling the Shots Dual Autographs')['family']=='CALLING THE SHOT DUAL AUTOGRAPHS'
registry=json.loads((ROOT/'data/parallel-specifications.json').read_text())
specs=registry['sets'][SLUG]
assert len(specs)==2 and {(s['family'],s['oddsName'],s['numbering']) for s in specs}=={('BASE CARDS','Base Cards Blue','/150'),('BASE CARDS','Base Cards Black','1/1')}
for spec in specs:assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
assert any(c['slug']==SLUG and 'Career Achievement' in c['family'] for c in registry['conflicts'])
record=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG)
assert record['releaseDate']=='2026-07-29' and record['releaseStatus']=='Released'
assert hashlib.sha256((ROOT/record['releaseDateEvidence']['file']).read_bytes()).hexdigest()==record['releaseDateEvidence']['sha256']
assert data['publishedSpecifications'][0]['rows']==[['Hobby packs per box','6'],['Cards per pack','3'],['Autographs or autograph relics per box','3'],['Relic cards per box','3']]
print('Verified all 786 physical subject rows, 723 card identities, 104 literal Rookie marks, 15 blank teams, original team spellings, 143 odds cells and exact base-only /150 / 1/1 scope.')
