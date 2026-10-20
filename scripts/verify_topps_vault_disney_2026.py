"""Independently compare original PDF text objects, glyphs and shared import fields."""
import collections
import hashlib
import json
import re
from pathlib import Path
import pdfplumber
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-vault-disney'
data=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text())
path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
assert hashlib.sha256(path.read_bytes()).hexdigest()==data['sha256']=='079af2711e9a6150f2bb4dc9ec8cab0210c2c1a8cb0601533bef7050fac6a3c8'
assert data['dedicatedParser']=='scripts/import_topps_vault_disney_2026.py'
assert data['originalSubjectRows']==data['rows']
assert len(data['rows'])==511 and len({r[0] for r in data['rows']})==22
numbered=[r for r in data['rows'] if r[1]];artists=[r for r in data['rows'] if not r[1]]
assert len(numbered)==429 and len({tuple(r[:2]) for r in numbered})==384
assert len(artists)==82 and collections.Counter(r[0] for r in artists)=={'PREMIERE SKETCH CARDS':55,'OVERSIZED PREMIERE SKETCH CARDS':27}
norm=lambda s:re.sub(r'\s+','',s)
families={r[0] for r in data['rows']}
# The revised PDF resets the text matrix inside TJ strings, so pypdf's
# visitor coordinates for continuation cells are zero. Its complete text
# flow independently retains all printed cells and repeated signer lines.
for pn,page in enumerate(PdfReader(path).pages,1):
    lines=[line.strip() for line in page.extract_text().splitlines() if line.strip()]
    if pn==1:
        lines=lines[:lines.index('Checklists provided by Topps reflect the intended configuration of that')]
    lines=[line for line in lines if line not in families|{'RELIC','AUTOGRAPH','AUTOGRAPH RELIC','SKETCH','BOXTOPPER'}]
    actual=[norm(r[1]+r[4]+r[5]) for r in data['rows'] if r[3]==str(pn)]
    assert [norm(line) for line in lines]==actual,('Independent full text-flow',pn)
# Independently check every baseline's complete glyph content, preserving draw
# order where physical cells overlap. Page 11 has no overlapping columns.
with pdfplumber.open(path) as pdf:
    for pn,page in enumerate(pdf.pages,1):
        groups=collections.defaultdict(list)
        for c in page.chars:groups[round(c['matrix'][5],2)].append(c)
        lines=[]
        for y,chars in sorted(groups.items(),reverse=True):
            line=''.join(c['text'] for c in chars)
            if pn==1 and y>730:continue
            if norm(line) in {norm(f) for f in families|{'RELIC','AUTOGRAPH','AUTOGRAPH RELIC','SKETCH','BOXTOPPER'}}:continue
            lines.append(norm(line))
        actual=[norm(r[1]+r[4]+r[5]) for r in data['rows'] if r[3]==str(pn)]
        assert lines==actual,('Full physical glyph comparison',pn)
assert next(r for r in data['rows'] if r[1]=='RB-CDB')[6:8]==['Christopher Daniel Barnes','Prince Eric']
assert next(r for r in data['rows'] if r[1]=='RB-IB')[7]=='Pocanhontas'
assert next(r for r in data['rows'] if r[1]=='IA-IN')[6:8]==['Ian Mckellen','Cogsworth']
assert {r[1] for r in data['rows'] if r[0]=='DISNEY DIAMONDS'}=={f'DD-{i}' for i in range(1,101)}
for family,count,multiplicity in [('DISNEY DUALS',19,2),('DISNEY TRIPLES',11,3),('VAULT AUTOGRAPH RELIC DUALS',2,2),('VAULT AUTOGRAPH RELIC TRIPLES',1,3)]:
    counts=collections.Counter(r[1] for r in data['rows'] if r[0]==family)
    assert len(counts)==count and set(counts.values())=={multiplicity}
assert next(r for r in artists if r[9]=='Jiaxin "YinShan" Sun')
assert sum(r[9]=='JohnruzelJimenez' for r in artists)==2
assert all(not r[1] and not r[6] and not r[7] and r[9] for r in artists)
assert all(r[9]=='Julie Vu' and r[7]==r[4] and r[5]==r[9] for r in data['rows'] if r[0]=='VAULT ORIGINALS')
assert len(data['odds'])==76 and data['formats']==['PACK#1','PACK#2','BOX TOPPER'] and data['oddsUnitsPublished'] is False
op=ROOT/'data/catalog-sources/downloads'/(SLUG+'-odds.pdf')
assert hashlib.sha256(op.read_bytes()).hexdigest()==data['oddsSha256']=='feced3f01b19b3afceaac26a46afac2df7f6fb5a814f961b2c5474c327116b88'
# Independent full text-flow comparison includes every name, null and literal ratio.
original=[]
for pn,page in enumerate(PdfReader(op).pages,1):
    lines=[line.strip() for line in page.extract_text().splitlines() if line.strip()]
    start=lines.index('Card PACK#1 PACK#2 BOX TOPPER')
    original.extend((pn,norm(line)) for line in lines[start+1:])
actual=[(o['page'],norm(o['name']+' '+ ' '.join(o['values'][f] or '-' for f in data['formats']))) for o in data['odds']]
assert original==actual
assert sum(v=='1:XX' for o in data['odds'] for v in o['values'].values())==2
assert next(o for o in data['odds'] if o['name']=='VAULT ORIGINALS')['values']=={'PACK#1':None,'PACK#2':None,'BOX TOPPER':'1:1'}
assert next(o for o in data['odds'] if o['name']=='IMMORTAL AUTOGRAPHS SUPERFRACTOR PARALLEL')['values']['PACK#2']=='1:1,247'
assert next(r for r in numbered if r[1]=='IA-TZ')[6:8]==['Tom Holland','Ian Lightfoot']
# The revision adds exactly one subject and removes no previously printed fields.
previous=ROOT/'data/catalog-sources/downloads'/(SLUG+'-pre-20261020.pdf')
assert hashlib.sha256(previous.read_bytes()).hexdigest()=='9835a0cde6f0ec32a63aceb419f78d1e182ba63139a5db6b59d526e6ad1c6dcf'

assert 'Team' not in data['headers'] and 'Rookie' not in data['headers'] and 'serialColumn' not in data
proof_path=ROOT/'data/parallel-audit-sources/vault-disney-2026-20261015.json';proof=json.loads(proof_path.read_text())
for spec in data['publishedSpecifications']:assert hashlib.sha256(proof_path.read_bytes()).hexdigest()==spec['evidenceSha256']
examples=next(s for s in data['publishedSpecifications'] if s['name']=='Card-specific guide examples')
assert examples['rows']==proof['cardExamples'] and all('parallel' in r[-1] for r in examples['rows'])
specs=data['parallelSpecifications'];assert len(specs)==1
assert specs[0]['family']=='IMMORTAL AUTOGRAPHS' and specs[0]['name']=='SuperFractor' and specs[0]['numbering']=='1/1'
record=next(s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert record['releaseStatus']=='Upcoming' and record['releaseDate']=='2026-10-21'
assert record['checklistUrl']==data['source'] and record['rowCount']==511 and record['sections']==22
assert record['oddsUrl']==data['oddsSource'] and record['odds']==76 and record['formats']==3
print('Verified 429 numbered subjects / 384 identities, 82 artists, original cells, new IA-TZ and all 76 three-column literal odds, including two 1:XX placeholders.')
