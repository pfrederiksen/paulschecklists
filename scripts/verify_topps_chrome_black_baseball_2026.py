"""Independently compare Chrome Black Baseball fields, ratios and guide scopes."""
import collections
import hashlib
import json
import logging
import re
from pathlib import Path
from pypdf import PdfReader

logging.getLogger('pypdf').setLevel(logging.ERROR)
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-chrome-black-baseball'
data=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text())
path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
assert hashlib.sha256(path.read_bytes()).hexdigest()==data['sha256']
assert data['dedicatedParser']=='scripts/import_topps_chrome_black_baseball_2026.py'
assert data['headers']==['Checklist section','Card number','Name','Team','Rookie','Source page']
assert data['originalSubjectRows']==data['rows']
assert len(data['rows'])==556 and len({r[0] for r in data['rows']})==11
norm=lambda s:re.sub(r'\s+','',s)
families={r[0] for r in data['rows']};family=None;source=[]
reader=PdfReader(path);assert len(reader.pages)==11
for pn,page in enumerate(reader.pages,1):
    for line in page.extract_text(extraction_mode='layout').splitlines():
        line=line.strip()
        if not line:continue
        if line in families:family=line;continue
        if line in {'BASE','INSERT','AUTOGRAPH'}:continue
        if pn==1 and family is None:continue
        m=re.fullmatch(r'(\S+)\s+(.+)',line);assert m,(pn,line)
        number,rest=m.groups();cells=[number,*re.split(r'\s{2,}',rest)]
        assert len(cells) in {3,4},(pn,line,cells)
        cells+=['']*(4-len(cells))
        source.append([norm(family),*map(norm,cells),str(pn)])
assert source==[[norm(c) for c in row] for row in data['rows']],'Every original field must retain its own physical row and column'
assert len({tuple(r[:2]) for r in data['rows']})==542
assert sum(r[4]=='Rookie' for r in data['rows'])==203
assert {int(r[1]) for r in data['rows'] if r[0]=='BASE CARDS'}==set(range(1,201))
assert len([r for r in data['rows'] if r[0]=='BASE ROOKIE DESIGN VARIATION'])==30
assert len([r for r in data['rows'] if r[0]=='DAMASCUS'])==30
assert len([r for r in data['rows'] if r[0]=='PAINT IT'])==19
assert next(r for r in data['rows'] if r[:2]==['BASE CARDS','18'])[3]=='Baltimore Orioles®'
assert next(r for r in data['rows'] if r[:2]==['BASE CARDS','29'])[4]==''
assert next(r for r in data['rows'] if r[:2]==['BASE CARDS','79'])[3]=='Washington Nationals®'
assert [r[3] for r in data['rows'] if r[1]=='PDPA-WW']==['Pittsburgh Pirates®','Athletics™']
assert [r[2] for r in data['rows'] if r[1]=='PDPA-WW']==['Jack Wilson','Jacob Wilson']
pairs=collections.Counter(r[1] for r in data['rows'] if r[0]=='PITCH BLACK PAIRINGS DUAL AUTOGRAPHS');assert len(pairs)==14 and set(pairs.values())=={2}
assert len(data['odds'])==68 and data['formats']==['Hobby']
assert data['formatNamesPublished'] is True and data['oddsUnitsPublished'] is False
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==data['oddsSha256']
source_odds=[]
for pn,page in enumerate(PdfReader(op).pages,1):
    for line in page.extract_text(extraction_mode='layout').splitlines():
        m=re.fullmatch(r'\s*(.+?)\s+([\d,.]+(?::[\d,.]+)+|-)\s*',line)
        if m:source_odds.append((pn,norm(m[1]),None if m[2]=='-' else m[2]))
assert source_odds==[(o['page'],norm(o['name']),o['values']['Hobby']) for o in data['odds']]
assert all(o['family'] in families for o in data['odds'])
registry=json.loads((ROOT/'data/parallel-specifications.json').read_text());specs=registry['sets'][SLUG];assert len(specs)==30
assert len([s for s in specs if s['family']=='BASE CARDS'])==21
assert [(s['name'],s['numbering']) for s in specs if not s.get('oddsName')]==[('Blue Mini Diamond','/150'),('Green Mini Diamond Refractor','/99')]
assert next(s for s in specs if s.get('oddsName')=='Base Cards Orange Refractor')['numbering']=='/25'
for spec in specs:
    assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
    if spec.get('oddsName'):assert any(o['name']==spec['oddsName'] and o['family']==spec['family'] for o in data['odds'])
assert not any(s['family'] in ['BASE ROOKIE DESIGN VARIATION','AUTOGRAPHS','PITCH BLACK PAIRINGS DUAL AUTOGRAPHS','SUPER FUTURES AUTOGRAPHS','NOCTURNAL'] for s in specs)
assert any(c['slug']==SLUG and '31' in c['gap'] and '19' in c['gap'] for c in registry['conflicts'])
record=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG)
assert record['releaseDate']=='2026-04-29' and record['releaseStatus']=='Released'
assert record['checklistUrl']==data['source'] and record['oddsUrl']==data['oddsSource']
print('Verified all 556 physical subject rows / 542 family-card identities, 203 literal Rookie flags, 68 Hobby ratios and 30 exact guide limits including two specification-only parallels. Guide count gaps retained.')
