"""Compare every subject field and odds cell against independent PDF layout."""
import collections
import hashlib
import json
import logging
import re
from pathlib import Path
from pypdf import PdfReader

logging.getLogger('pypdf').setLevel(logging.ERROR)
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-pristine-baseball'
data=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text())
path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
assert hashlib.sha256(path.read_bytes()).hexdigest()==data['sha256']
assert data['dedicatedParser']=='scripts/import_topps_pristine_2026.py'
assert data['headers']==['Checklist section','Card number','Name','Team','Rookie','Source page']
assert data['originalSubjectRows']==data['rows']
assert len(data['rows'])==729 and len({r[0] for r in data['rows']})==18
norm=lambda s:re.sub(r'\s+','',s)
families={r[0] for r in data['rows']};family=None;source=[]
reader=PdfReader(path);assert len(reader.pages)==15
for pn,page in enumerate(reader.pages,1):
    for line in page.extract_text(extraction_mode='layout').splitlines():
        line=line.strip()
        if not line:continue
        if line in families:family=line;continue
        if line in {'BASE','INSERT','AUTOGRAPH','AUTOGRAPH RELIC'}:continue
        if pn==1 and family is None:continue
        m=re.fullmatch(r'(\S+)\s+(.+)',line);assert m,(pn,line)
        number,rest=m.groups();cells=re.split(r'\s{2,}',rest)
        assert len(cells) in {2,3},(pn,line,cells)
        cells+=['']*(3-len(cells))
        source.append([norm(family),norm(number),*map(norm,cells),str(pn)])
assert source==[[norm(c) for c in row] for row in data['rows']],'Every original field must retain its own row and column'
assert len({tuple(r[:2]) for r in data['rows']})==705
assert {int(r[1]) for r in data['rows'] if r[0]=='BASE CARDS I'}==set(range(1,201))
assert sum(r[4]=='Rookie' for r in data['rows'])==224 and all(r[3] for r in data['rows'])
rush=[r for r in data['rows'] if r[0]=='RUSHMORE'];assert collections.Counter(r[1] for r in rush)=={f'R-{i}':4 for i in range(1,6)}
assert [r[2] for r in rush if r[1]=='R-1']==['Babe Ruth','Derek Jeter','Mickey Mantle','Lou Gehrig']
assert [r[2] for r in data['rows'] if r[1]=='PDA-SC']==['Paul Skenes','Bubba Chandler']
assert all(r[4]=='Rookie' for r in data['rows'] if r[1] in ['PDA-SC','PDA-WC']),'Preserve apparently erroneous published marks'
assert next(r for r in data['rows'] if r[1]=='RJRA-HF')[3]=='Seattle Mariners™'
assert next(r for r in data['rows'] if r[:2]==['BASE CARDS I','89'])[3]=='Washington Nationals®'
assert next(r for r in data['rows'] if r[:2]==['BASE CARDS I','194'])[3]=='Texas Rangers®'
assert next(r for r in data['rows'] if r[1]=='PA-JG')[3]=='Boston Red Sox®'
assert len(data['odds'])==95 and data['formats']==['Encased Pack','Non-Encased Pack']
assert data['formatNamesPublished'] is True and data['oddsUnitsPublished'] is True
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==data['oddsSha256']
source_odds=[]
for pn,page in enumerate(PdfReader(op).pages,1):
    lines=page.extract_text(extraction_mode='layout').splitlines()
    assert any(re.fullmatch(r'\s*Cards\s+Encased Pack\s+Non-Encased Pack\s*',line) for line in lines)
    for line in lines:
        m=re.fullmatch(r'\s*(.+?)\s+([\d,.]+(?::[\d,.]+)+|-)\s+([\d,.]+(?::[\d,.]+)+|-)\s*',line)
        if m:source_odds.append((pn,norm(m[1]),*[None if m[i]=='-' else m[i] for i in [2,3]]))
assert source_odds==[(o['page'],norm(o['name']),*[o['values'][f] for f in data['formats']]) for o in data['odds']]
aqua=next(o for o in data['odds'] if o['name']=='Base Cards Aqua Refractor')
assert aqua['values']=={'Encased Pack':None,'Non-Encased Pack':'01:09:00'}
assert all(o.get('family') in families for o in data['odds'])
registry=json.loads((ROOT/'data/parallel-specifications.json').read_text());specs=registry['sets'][SLUG]
assert len(specs)==18
base={s['name']:s['numbering'] for s in specs if s['family']=='BASE CARDS I'}
assert base=={'Aqua':'/199','Green':'/150','Purple':'/99','Blue':'/75','Gold':'/50','Orange':'/25','Pink':'/15','Primaries':'/10','Red':'/5','SuperFractor':'1/1'}
assert sum(s['numbering']=='1/1' for s in specs)==8
assert not any(s['family'] in ['POPULAR DEMAND AUTOGRAPH RELIC','PRISTINE PIECES AUTOGRAPH RELIC','ROOKIE JUMBO RELIC AUTOGRAPHS'] for s in specs)
for spec in specs:
    assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
    assert any(o['name']==spec['oddsName'] and o['family']==spec['family'] for o in data['odds'])
assert any(c['slug']==SLUG and '/99' in c['family'] for c in registry['conflicts'])
record=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG)
assert record['releaseDate'] is None and record['sourcePage']=='https://www.topps.com/pages/topps-pristine-baseball'
assert record['checklistUrl']==data['source'] and record['oddsUrl']==data['oddsSource']
inventory=json.loads((ROOT/'data/topps-official-odds.json').read_text());assert any(o['url']==data['oddsSource'] and o['sha256']==data['oddsSha256'] for o in inventory)
print('Verified 729 original subject rows, 705 card identities, all 200 base numbers, 224 literal Rookie flags, 95 two-format odds categories, literal 01:09:00 and 18 exact guide joins.')
