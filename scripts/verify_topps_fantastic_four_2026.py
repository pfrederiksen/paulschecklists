"""Independently account for every subject glyph, extra cell and odds cell."""
import collections
import hashlib
import json
import logging
import re
from pathlib import Path

import pdfplumber
from pypdf import PdfReader

logging.getLogger('pypdf').setLevel(logging.ERROR)
ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2026-topps-finest-fantastic-four'
data=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text())
path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
assert hashlib.sha256(path.read_bytes()).hexdigest()==data['sha256']
assert data['dedicatedParser']=='scripts/import_topps_fantastic_four_2026.py'
assert len(data['rows'])==704 and len({r[0] for r in data['rows']})==30
assert data['originalSubjectRows']==data['rows']
assert data['headers']==['Checklist section','Card number','Name','Published additional text','Source page']
norm=lambda s:re.sub(r'\s+','',s)
headers={r[0] for r in data['rows']}|{'SKETCH CARDS'}
source=collections.defaultdict(str);expected=collections.defaultdict(str)
extra=collections.defaultdict(list);expected_extra=collections.defaultdict(list)
family=None
reader=PdfReader(path);assert len(reader.pages)==17
for pn,page in enumerate(reader.pages,1):
    groups=[]
    def visit(text,cm,tm,font,size):
        if not text.strip():return
        x=tm[4]*cm[0]+cm[4];y=tm[5]*cm[3]+cm[5]
        objects=next((o for baseline,o in groups if abs(y-baseline)<.6),None)
        if objects is None:objects=[];groups.append((y,objects))
        objects.append((x,text.strip()))
    page.extract_text(visitor_text=visit)
    for y,objects in sorted(groups,reverse=True):
        compact=norm(' '.join(t for x,t in sorted(objects)))
        heading=next((h for h in headers if norm(h)==compact),None)
        if heading:family=heading;continue
        if compact in {'BASE','INSERT','RELIC','AUTOGRAPH','SKETCH'} or pn==1 and y>740:continue
        assert family,(pn,compact)
        source[(pn,family)]+=compact
        cell=norm(' '.join(t for x,t in sorted(objects) if x>=350))
        if cell:extra[(pn,family)].append(cell)
for family,number,name,additional,pn in data['rows']:
    key=(int(pn),family);expected[key]+=norm(number+name+additional)
    if additional:expected_extra[key].append(norm(additional))
artists=data['originalArtistRosters']['SKETCH CARDS']
for name,pn in artists:expected[(int(pn),'SKETCH CARDS')]+=norm(name)
assert source==expected,'Every printed subject/artist character must be retained in its page and family'
assert extra==expected_extra and sum(map(len,extra.values()))==68
assert len(artists)==116 and ['IQ','16'] in artists and ['John-Paul Howard','17'] in artists
assert artists[-1]==['ジェイソン (Jason)','17']
base=[r for r in data['rows'] if r[0].startswith('BASE CARDS ')]
assert len(base)==100
counts=collections.Counter(int(r[1]) for r in base)
assert set(counts)==set(range(1,101))-{36,42} and counts[34]==counts[41]==2
assert next(r for r in base if r[2]=='Flux')[1]=='19'
assert next(r for r in base if r[2]=='Titania')[1]=='46'
for prefix,family in [('BL','1960s BLACKLIGHT BASE VARIATION'),('NZ','NEGATIVE ZONE BASE VARIATION'),('TF','TRIBUTE TO FINEST ‘96')]:
    rows=[r for r in data['rows'] if r[0]==family]
    assert len(rows)==100 and {r[1] for r in rows}=={f'{prefix}-{i:03d}' for i in range(1,101)}
assert next(r for r in data['rows'] if r[1]=='FA-JB')[2:4]==['Michael Bailey Smith','Powerplant Worker #2']
assert next(r for r in data['rows'] if r[1]=='TO-01')[2:4]==['Doctor Doom','Adi Granov']
assert next(r for r in data['rows'] if r[1]=='CE-10')[2:4]==['Silver Surfer','Thor #193']
quad=[r for r in data['rows'] if r[0]=='QUAD AUTOGRAPHS BOOK CARD']
assert collections.Counter(r[1] for r in quad)=={'QA-ARJM':4,'QA-PKMQ':4}
assert 'FS-10' not in {r[1] for r in data['rows'] if r[0]=='FANTASTIC SCIENCE AUTOGRAPHS'}
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==data['oddsSha256']
assert len(data['odds'])==158 and data['formats']==['Hobby']
assert data['formatNamesPublished'] is True and data['oddsUnitsPublished'] is False
reader=PdfReader(op);physical=[]
with pdfplumber.open(op) as pdf:
    for pn,page in enumerate(pdf.pages,1):
        objects=[]
        def visit(text,cm,tm,font,size):
            if text.strip():objects.append((tm[4]*cm[0]+cm[4],page.height-(tm[5]*cm[3]+cm[5]),text.strip()))
        reader.pages[pn-1].extract_text(visitor_text=visit)
        rows=page.find_tables()[0].rows[3 if pn==1 else 1:]
        for row in rows:
            values=[]
            for ci,box in enumerate(row.cells):
                if ci==0:
                    values.append(' '.join(t for x,y,t in objects if box[0]<=x<box[2] and box[1]<=y<box[3]))
                else:
                    # pypdf reports a zero text matrix for some reused short
                    # ratios. Original glyph centers independently verify every
                    # literal numeric cell without its cached text matrix.
                    values.append(''.join(c['text'] for c in page.chars if box[0]<=(c['x0']+c['x1'])/2<box[2] and box[1]<=(c['top']+c['bottom'])/2<box[3]))
            physical.append((pn,*map(norm,values)))
assert physical==[(o['page'],norm(o['name']),norm(o['values']['Hobby'])) for o in data['odds']]
assert next(o for o in data['odds'] if o['name']=="World's Greatest Comic Magazines Orange Refractor")['values']=={'Hobby':'1:1,515'}
assert next(o for o in data['odds'] if o['name']=='Fantastic Science Autographs')['family']=='FANTASTIC SCIENCE AUTOGRAPHS'
registry=json.loads((ROOT/'data/parallel-specifications.json').read_text())['sets'][SLUG]
assert len(registry)==2 and {s['numbering'] for s in registry}=={'/96','1/1'}
for spec in registry:assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
assert not any(h in data['headers'] for h in ['Team','Rookie'])
record=next(s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert record['releaseDate'] is None
print('Verified 704 subject rows, 68 separate additional cells, 116 artists, original repeated/missing numbers, all 158 complete physical odds cells and exact /96 / 1/1 scope.')
