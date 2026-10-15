"""Independently compare every Marvel Comics Sapphire PDF row and odds literal."""
import collections
import hashlib
import json
import logging
import re
from pathlib import Path
from pypdf import PdfReader
logging.getLogger('pypdf').setLevel(logging.ERROR)

ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-chrome-marvel-comics-sapphire-edition'
data=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text())
path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
assert hashlib.sha256(path.read_bytes()).hexdigest()==data['sha256']
assert data['dedicatedParser']=='scripts/import_topps_marvel_sapphire_2026.py'
assert data['headers']==['Checklist section','Card number','Name','Source page']
assert data['originalSubjectRows']==data['rows']
families={r[0] for r in data['rows']};family=None;source=[]
for pn,page in enumerate(PdfReader(path).pages,1):
    for line in page.extract_text(extraction_mode='layout').splitlines():
        line=' '.join(line.split())
        if not line or line.startswith(('Checklists provided','production,')) or line in {'BASE','INSERT'}:continue
        if line in families:family=line;continue
        m=re.fullmatch(r'(\d+|[A-Z]+-[A-Z0-9]+)\s+(.+)',line)
        assert m,(pn,line);source.append([family,*m.groups(),str(pn)])
norm=lambda s:re.sub(r'\s+','',s)
assert [[norm(c) for c in r] for r in source]==[[norm(c) for c in r] for r in data['rows']],'Every original source field must match independent PDF layout extraction'
assert len(source)==262 and len(families)==8 and len({tuple(r[:2]) for r in source})==242
assert sum('(DEBUT)' in r[2] for r in source)==17
assert not any(h in data['headers'] for h in ['Rookie','Team'])
for f,numbers in [('CHARACTERS I',range(1,101)),('CHARACTERS II',range(101,201))]:
    assert {int(r[1]) for r in source if r[0]==f}==set(numbers)
for prefix,multiplicity,count in [('MFD-',2,6),('MFT-',3,4),('MFQ-',4,2)]:
    counts=collections.Counter(r[1] for r in source if r[1].startswith(prefix))
    assert len(counts)==count and set(counts.values())=={multiplicity}
assert {r[2] for r in source if r[1]=='MFQ-DNSG'}=={'Doctor Doom','Silver Surfer','Galactus','Namor'}
assert next(r for r in source if r[1]=='HG-01')[2]=='Carnage'
assert next(r for r in source if r[1]=='IS-01')[2]=='Emma Frost'
assert data['formats']==['Sapphire'] and data['formatNamesPublished'] is True and data['oddsUnitsPublished'] is False
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==data['oddsSha256']
source_odds=[]
for pn,page in enumerate(PdfReader(op).pages,1):
    for line in page.extract_text(extraction_mode='layout').splitlines():
        m=re.fullmatch(r'\s*(.+?)\s+([\d,.]+(?::[\d,.]+)+)\s*',line)
        if m:source_odds.append((pn,' '.join(m[1].split()),m[2]))
assert len(source_odds)==23
assert source_odds==[(o['page'],o['name'],o['values']['Sapphire']) for o in data['odds']]
base=[o for o in data['odds'] if o['name'].startswith('Base - Characters ')]
assert len(base)==8 and all(o['family']=='CHARACTERS I' and o['familyAliases']==['CHARACTERS II'] for o in base)
assert all(o['family'] in families for o in data['odds'])
registry=json.loads((ROOT/'data/parallel-specifications.json').read_text());assert not registry['sets'].get(SLUG)
for c in [c for c in registry['conflicts'] if c['slug']==SLUG]:
    assert hashlib.sha256((ROOT/c['evidenceFile']).read_bytes()).hexdigest()==c['evidenceSha256']
record=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG)
assert record['releaseDate'] is None and record['releaseStatus']=='Unverified'
print('Verified 262 subject rows / 242 identities, 17 DEBUT annotations, all repeated facsimile subjects and 23 literal odds; both base sections share eight categories. Numbering and release-date gaps retained.')
