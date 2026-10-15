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
assert hashlib.sha256(path.read_bytes()).hexdigest()==data['sha256']=='9835a0cde6f0ec32a63aceb419f78d1e182ba63139a5db6b59d526e6ad1c6dcf'
assert data['dedicatedParser']=='scripts/import_topps_vault_disney_2026.py'
assert data['originalSubjectRows']==data['rows']
assert len(data['rows'])==510 and len({r[0] for r in data['rows']})==22
numbered=[r for r in data['rows'] if r[1]];artists=[r for r in data['rows'] if not r[1]]
assert len(numbered)==428 and len({tuple(r[:2]) for r in numbered})==383
assert len(artists)==82 and collections.Counter(r[0] for r in artists)=={'PREMIERE SKETCH CARDS':55,'OVERSIZED PREMIERE SKETCH CARDS':27}
norm=lambda s:re.sub(r'\s+','',s)
families={r[0] for r in data['rows']};family=None;source=[]
for pn,page in enumerate(PdfReader(path).pages,1):
    if pn>=11:continue
    groups=collections.defaultdict(list)
    def visit(t,cm,tm,font,size):
        if t.strip():groups[round(tm[5]+cm[5],2)].append((tm[4]+cm[4],t))
    page.extract_text(visitor_text=visit)
    for y,chunks in sorted(groups.items(),reverse=True):
        line=' '.join(''.join(t for _,t in chunks).split())
        if pn==1 and y>700:continue
        if line in families:family=line;continue
        if line in {'RELIC','AUTOGRAPH','AUTOGRAPH RELIC','SKETCH'}:continue
        assert family,(pn,line)
        if family=='PREMIERE SKETCH CARDS':number='';first=line;second=''
        else:
            number=''.join(t for x,t in chunks if x<100).strip()
            first=''.join(t for x,t in chunks if 100<=x<200).strip()
            second=''.join(t for x,t in chunks if x>=200).strip()
        source.append([family,number,str(pn),first,second])
assert [[norm(c) for c in r] for r in source]==[[norm(c) for c in [r[0],r[1],r[3],r[4],r[5]]] for r in data['rows'] if int(r[3])<=10]
# Independently check every baseline's complete glyph content, preserving draw
# order where physical cells overlap. Page 11 has no overlapping columns.
with pdfplumber.open(path) as pdf:
    for pn,page in enumerate(pdf.pages,1):
        if pn==12:continue
        groups=collections.defaultdict(list)
        for c in page.chars:groups[round(c['matrix'][5],2)].append(c)
        lines=[]
        for y,chars in sorted(groups.items(),reverse=True):
            line=''.join(c['text'] for c in chars)
            if pn==1 and y>700:continue
            if norm(line) in {norm(f) for f in families|{'RELIC','AUTOGRAPH','AUTOGRAPH RELIC','SKETCH','BOXTOPPER'}}:continue
            lines.append(norm(line))
        actual=[norm(r[1]+r[4]+r[5]) for r in data['rows'] if r[3]==str(pn)]
        assert lines==actual,('Full physical glyph comparison',pn)
        if pn==11:
            vo=[r for r in data['rows'] if r[0]=='VAULT ORIGINALS']
            for r,(y,chars) in zip(vo,[(y,c) for y,c in sorted(groups.items(),reverse=True) if 441<=y<=688]):
                assert norm(''.join(c['text'] for c in chars if 100<=c['x0']<250))==norm(r[4])
                assert norm(''.join(c['text'] for c in chars if c['x0']>=250))==norm(r[5])
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
assert data['odds']==[] and data['formats']==[] and data['oddsUnitsPublished'] is False
assert 'Team' not in data['headers'] and 'Rookie' not in data['headers'] and 'serialColumn' not in data
proof_path=ROOT/'data/parallel-audit-sources/vault-disney-2026-20261015.json';proof=json.loads(proof_path.read_text())
for spec in data['publishedSpecifications']:assert hashlib.sha256(proof_path.read_bytes()).hexdigest()==spec['evidenceSha256']
examples=next(s for s in data['publishedSpecifications'] if s['name']=='Card-specific guide examples')
assert examples['rows']==proof['cardExamples'] and all('parallel' in r[-1] for r in examples['rows'])
specs=data['parallelSpecifications'];assert len(specs)==1
assert specs[0]['family']=='IMMORTAL AUTOGRAPHS' and specs[0]['name']=='SuperFractor' and specs[0]['numbering']=='1/1'
record=next(s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert record['releaseStatus']=='Upcoming' and record['releaseDate']=='2026-10-21'
assert record['checklistUrl']==data['source'] and record['rowCount']==510 and record['sections']==22
assert 'oddsUrl' not in record and record['odds']==0
print('Verified 428 numbered subject rows / 383 identities, 82 artists, all original cells and clipped actor glyphs, 22 sections, exact guide scope and unavailable pack odds.')
