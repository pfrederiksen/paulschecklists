"""Independently compare all Midnight subject columns and literal odds cells."""
import collections
import hashlib
import json
import logging
import re
from pathlib import Path
from pypdf import PdfReader

logging.getLogger('pypdf').setLevel(logging.ERROR)
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-26-topps-midnight-basketball'
data=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text())
path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
assert hashlib.sha256(path.read_bytes()).hexdigest()==data['sha256']
assert data['dedicatedParser']=='scripts/import_topps_midnight_basketball.py'
assert data['headers']==['Checklist section','Card number','Name','Team','Rookie','Source page']
assert data['originalSubjectRows']==data['rows']
assert len(data['rows'])==593 and len({r[0] for r in data['rows']})==22
norm=lambda s:re.sub(r'\s+','',s)
families={r[0] for r in data['rows']};family=None;source=[]
reader=PdfReader(path);assert len(reader.pages)==13
for pn,page in enumerate(reader.pages,1):
    for line in page.extract_text(extraction_mode='layout').splitlines():
        line=line.strip()
        if not line:continue
        if line in families:family=line;continue
        if line in {'BASE','INSERT','AUTOGRAPH','AUTOGRAPH RELIC'}:continue
        cells=re.split(r'\s{2,}',line)
        assert len(cells) in {3,4},(pn,line,cells)
        cells+=['']*(4-len(cells))
        source.append([norm(family),*map(norm,cells),str(pn)])
assert source==[[norm(c) for c in row] for row in data['rows']],'Every original field must retain its own physical row and column'
assert len({tuple(r[:2]) for r in data['rows']})==593
assert {int(r[1]) for r in data['rows'] if r[0]=='BASE CARDS'}==set(range(1,101))
assert sum(r[4]=='Rookie' for r in data['rows'])==246
base=[r for r in data['rows'] if r[0]=='BASE CARDS']
assert {int(r[1]) for r in base if r[4]=='Rookie'}==set(range(61,101))
assert next(r for r in data['rows'] if r[1]=='DMA-BH')[3]=='Minnesota Tmberwolves'
assert next(r for r in data['rows'] if r[1]=='DD-2')[2]=='Karl Anthony-Towns'
assert next(r for r in data['rows'] if r[1]=='SM-RJE')[3]=='New Jersey Nets'
assert next(r for r in data['rows'] if r[1]=='DM-RA')[3]=='Seattle Supersonics'
assert next(r for r in data['rows'] if r[:2]==['BASE CARDS','50'])[3]=='New Orleans Pelicans'
assert next(r for r in data['rows'] if r[1]=='MS-CM')[3]=='Washington Wizards'
assert next(r for r in data['rows'] if r[:2]==['BASE CARDS','90'])[2]=='Yanic Konan-Niederhäuser'
assert len([r for r in data['rows'] if r[0]=='STROKE OF MIDNIGHT AUTOGRAPHS II'])==2
assert len(data['odds'])==219 and data['formats']==['Published odds (format not named)']
assert data['formatNamesPublished'] is False and data['oddsUnitsPublished'] is False
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==data['oddsSha256']
source_odds=[]
for pn,page in enumerate(PdfReader(op).pages,1):
    for line in page.extract_text(extraction_mode='layout').splitlines():
        if not line.strip():continue
        m=re.fullmatch(r'\s*(.+?)\s+([\d,.]+(?::[\d,.]+)+|-)\s*',line)
        assert m,(pn,line)
        source_odds.append((pn,norm(m[1]),None if m[2]=='-' else m[2]))
assert source_odds==[(o['page'],norm(o['name']),o['values'][data['formats'][0]]) for o in data['odds']]
assert all(o['family'] in families for o in data['odds'])
assert all(o['family']=='NIGHT SHADE' for o in data['odds'] if o['name'].startswith('Nightshade'))
assert next(o for o in data['odds'] if o['name']=='Twilight')['family']=='TWILIGHT'
assert next(o for o in data['odds'] if o['name']=='Base Twilight')['family']=='BASE CARDS'
registry=json.loads((ROOT/'data/parallel-specifications.json').read_text())
assert not registry['sets'].get(SLUG),'Do not infer serial limits from unnamed ratios, colors or other products'
conflicts=[c for c in registry['conflicts'] if c['slug']==SLUG];assert conflicts
for spec in conflicts:
    assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
record=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG)
assert record['releaseDate']=='2026-01-29' and record['releaseStatus']=='Released' and record['year']=='2025-26'
assert record['checklistUrl']==data['source'] and record['oddsUrl']==data['oddsSource']
print('Verified all 593 physical subject rows / 22 sections, 100 base numbers, 246 literal Rookie flags and 219 unnamed odds values. Historical teams, spelling alias and numbering gaps retained.')
