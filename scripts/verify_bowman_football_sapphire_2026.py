"""Independent full text-flow and source-field checks for Bowman Sapphire."""
import collections
import hashlib
import json
import re
from pathlib import Path
from pypdf import PdfReader
import pdfplumber

ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-bowman-football-sapphire-edition'
data=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text())
path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
assert hashlib.sha256(path.read_bytes()).hexdigest()==data['sha256']=='077084b320f86c7a3af9117ae3ab865125264b1edcbc9e63bc6c8f46554ea4da'
assert data['dedicatedParser']=='scripts/import_bowman_football_sapphire_2026.py'
assert data['originalSubjectRows']==data['rows'] and data['headers']==['Checklist section','Card number','Name','Team','Rookie','Source page']
assert len(data['rows'])==608 and len({r[0] for r in data['rows']})==11
assert sum(r[4]=='Rookie' for r in data['rows'])==146
norm=lambda x:re.sub(r'\s+','',x)
families={r[0] for r in data['rows']}
pdf=PdfReader(path);assert len(pdf.pages)==13
for pn,page in enumerate(pdf.pages,1):
    lines=[line.strip() for line in page.extract_text().splitlines() if line.strip()]
    lines=[line for line in lines if not line.startswith(('Checklists provided by Topps','product at the time of production')) and line not in families|{'BASE','INSERT','AUTOGRAPH'}]
    expected=[norm(''.join(r[1:5])) for r in data['rows'] if r[5]==str(pn)]
    assert [norm(line) for line in lines]==expected,('Full original text flow',pn)
# Independently compare fixed physical column rectangles with the draw-order
# adapter. Repeated codes (including two SSA-JH subjects on page 13) are counted.
with pdfplumber.open(path) as physical:
    for pn,page in enumerate(physical.pages,1):
        baselines=collections.defaultdict(list)
        for c in page.chars:baselines[round(c['matrix'][5],2)].append(c)
        cells=[]
        for chars in baselines.values():
            number=''.join(c['text'] for c in chars if c['x0']<130).strip()
            if not re.fullmatch(r'\d+|[A-Z0-9]+-[A-Z0-9]+',number):continue
            cells.append(tuple(' '.join(''.join(c['text'] for c in chars if a<=c['x0']<b).split()) for a,b in [(0,130),(130,294),(294,446),(446,page.width)]))
        assert collections.Counter(cells)==collections.Counter(tuple(r[1:5]) for r in data['rows'] if r[5]==str(pn)),('Physical columns',pn)
for family,count in [('CHROME PROSPECTS I',201),('CHROME NFL BASE',100),('CHROME ROOKIE BASE',100)]:
    rows=[r for r in data['rows'] if r[0]==family]
    assert len(rows)==count and len({r[1] for r in rows})==count
assert {r[1] for r in data['rows'] if r[0]=='CHROME PROSPECTS I'}=={f'BCP-{i}' for i in range(1,202)}
assert next(r for r in data['rows'] if r[1]=='BCP-1')[2:5]==['Cutter Boley','Arizona State®','']
assert next(r for r in data['rows'] if r[1]=='BCP-201')[2:5]==['Arch Manning','Texas','']
assert next(r for r in data['rows'] if r[1]=='SSA-CT')[2:5]==['Carnell Tate','Tennessee Titans','Rookie']
assert data['rows'][-1][1:5]==['SSA-WJ','Waymond Jordan','USC','']
assert all(r[2] and r[3] and r[4] in {'','Rookie'} for r in data['rows'])
assert data['odds']==[] and data['formats']==[] and not data['formatNamesPublished'] and not data['oddsUnitsPublished']
assert not data.get('parallelSpecifications') and not data.get('categoryNumbering')
record=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG)
assert record['releaseStatus']=='Upcoming' and record['releaseDate'] is None
assert record['rowCount']==608 and record['sections']==11 and record['checklistUrl']==data['source']
assert record['importKind']=='topps-grid-pdf'
print('Verified all 608 physical subjects, 11 families, 201 prospect codes, 146 literal Rookie marks, original teams and unavailable odds/serial fields.')
