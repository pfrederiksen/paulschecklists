"""Verify original MLB All-Star NOW cells and exact base-only parallel scope."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pdfplumber
import import_official_catalog as generic
from import_topps_now_mlb_allstar_2026 import SLUG,URL,PAGE,EVIDENCE,BASE,AUTO,COLORS

root=Path(__file__).resolve().parents[1]
path=root/'data/catalog-sources/downloads'/(SLUG+'.pdf')
data=json.loads((root/'data/imports'/(SLUG+'.json')).read_text())
assert data['sha256']==hashlib.sha256(path.read_bytes()).hexdigest() and data['source']==URL
assert data['headers']==['Checklist section','Card number','Player','Team','Pos.','RC','Source page']
assert data['originalPrintedHeaders']==['Card #','Player','Team','Pos.','']
assert Counter(r[0] for r in data['rows'])=={BASE:18,AUTO:17}
assert len(data['rows'])==len({r[1] for r in data['rows']})==35
with pdfplumber.open(path) as doc:
    assert len(doc.pages)==1
    words=doc.pages[0].extract_words()
    anchors=[w for w in words if w['x0']<110 and re.fullmatch('ASG-[A-Z]+',w['text'])]
    physical=[]
    for anchor in anchors:
        line=sorted([w for w in words if abs(w['top']-anchor['top'])<.1],key=lambda w:w['x0'])
        physical.append([' '.join(w['text'] for w in line if lo<=w['x0']<hi)
                         for lo,hi in [(50,118),(118,233),(233,350),(350,382),(382,420)]])
    assert physical==[r[1:6] for r in data['rows']]
by_code={r[1]:r for r in data['rows']}
assert {r[1] for r in data['rows'] if r[5]=='RC'}=={'ASG-CS','ASG-KM','ASG-CB','ASG-JM','ASG-CSA','ASG-KMA','ASG-CBA','ASG-JMA'}
assert by_code['ASG-NK'][5]==by_code['ASG-NKA'][5]==''
assert by_code['ASG-SO'][4]=='P/DH' and by_code['ASG-SOA'][4]=='DH'
assert by_code['ASG-NK'][3]=='Athletics™' and by_code['ASG-BHA'][3]=='Philadelphia Phillies®'
assert 'ASG-YAA' not in by_code and by_code['ASG-YA'][2]=='Yordan Alvarez'
assert not data.get('odds') and not data.get('formats') and not data.get('serialColumn')
proof=json.loads((root/EVIDENCE).read_text());ph=hashlib.sha256((root/EVIDENCE).read_bytes()).hexdigest()
assert data['sourceProducts'][0]['sha256']==ph and data['sourceProducts'][0]['url']==PAGE
assert proof['title'].endswith('19 Card Set - PR: 16306')
base=next(s for s in data['publishedSpecifications'] if s['name']==BASE)
assert [r[:2] for r in base['rows']]==[[n,v] for n,v in COLORS]+[['All-Star Game LogoFractor','Unnumbered']]
auto=next(s for s in data['publishedSpecifications'] if s['name']==AUTO)
assert auto['headers'][0]=='Published statement' and '/10 or lower' in auto['rows'][0][0]
assert 'Upper bound only' in auto['rows'][0][1]
context=next(s for s in data['publishedSpecifications'] if s['name'].startswith('Set-wide'))
assert context['rows'][0][1]=='16306' and 'bundle' in context['rows'][0][2]
fields={r[0]:r[1] for r in context['rows'][2:]}
assert fields['Available From']=='Jul 9, 2026' and fields['Available Until']=='Jul 16, 2026'
registry=json.loads((root/'data/parallel-specifications.json').read_text())
entries=registry['sets'][SLUG]
assert len(entries)==7 and all(e['family']==BASE and e['evidenceSha256']==ph and e['source']==PAGE for e in entries)
assert [(e['name'],e['numbering']) for e in entries]==[(r[0],r[1]) for r in base['rows']]
assert not any(e['family']==AUTO for e in entries),'No base-color numbering may propagate to autographs'
record=next(s for s in json.loads((root/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert record['releaseDate'] is None and record['releaseStatus']=='Unverified'
assert generic.run(record.copy())==record
assert not any(p['source']==PAGE for p in json.loads((root/'data/topps-now-observations.json').read_text()))
assert not json.loads((root/'data/topps-now-archive-index.json').read_text())['coverageComplete']
print('Verified all 35 MLB All-Star NOW physical rows, eight literal RC marks, original teams/positions, six exact base foil limits, unnumbered LogoFractor, qualified autograph upper bound and bundle-only PR16306/sale dates.')
