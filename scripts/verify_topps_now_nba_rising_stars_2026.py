"""Verify every NBA Rising Stars NOW PDF cell and base-only specification join."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pdfplumber
import import_official_catalog as generic
from import_topps_now_nba_rising_stars_2026 import SLUG,URL,PAGE,EVIDENCE,BASE,AUTO,COLORS

root=Path(__file__).resolve().parents[1]
path=root/'data/catalog-sources/downloads'/(SLUG+'.pdf')
data=json.loads((root/'data/imports'/(SLUG+'.json')).read_text())
assert data['sha256']==hashlib.sha256(path.read_bytes()).hexdigest() and data['source']==URL
assert data['headers']==['Checklist section','Card number','Player','Position','Status','Team','Source page']
assert data['originalPrintedHeaders']==['Card No.','Player','Position','Status','Team']
assert Counter(r[0] for r in data['rows'])=={BASE:21,AUTO:16}
assert len(data['rows'])==len({r[1] for r in data['rows']})==37
physical=[]
with pdfplumber.open(path) as doc:
    assert len(doc.pages)==2
    for pn,page in enumerate(doc.pages,1):
        words=page.extract_words()
        anchors=[w for w in words if w['x0']<120 and re.fullmatch(r'\d+(?:-A)?',w['text']) and (pn>1 or w['top']>100)]
        for anchor in anchors:
            line=sorted([w for w in words if abs(w['top']-anchor['top'])<.35],key=lambda w:w['x0'])
            physical.append([*[' '.join(w['text'] for w in line if lo<=w['x0']<hi)
                               for lo,hi in [(50,120),(120,270),(270,340),(340,390),(390,490)]],str(pn)])
assert physical==[r[1:] for r in data['rows']]
by_code={r[1]:r for r in data['rows']}
assert [r[1] for r in data['rows'] if r[0]==BASE]==[str(n) for n in range(1,22)]
assert [r[1] for r in data['rows'] if r[0]==AUTO]==[str(n)+'-A' for n in [1,2,4,5,6,7,8,9,10,13,14,15,17,18,20,21]]
assert data['rows'][-1]==[AUTO,'21-A','Kyshawn George','F','','Team Vince','2']
assert by_code['18'][2]=='Egor Dёmin' and by_code['18-A'][2]=='Egor Dёmin'
assert by_code['11'][2]=='Tre Johnson III' and '3-A' not in by_code and '11-A' not in by_code
assert Counter(r[5] for r in data['rows'])=={'Team Melo':12,'Team T-Mac':13,'Team Vince':12}
assert data['rookieColumn']==4 and Counter(r[4] for r in data['rows'])=={'RC':17,'':20}
assert by_code['2'][4]==by_code['21-A'][4]=='' and by_code['1'][4]==by_code['1-A'][4]=='RC'
assert not data.get('odds') and not data.get('formats') and not data.get('serialColumn')
proof=json.loads((root/EVIDENCE).read_text());ph=hashlib.sha256((root/EVIDENCE).read_bytes()).hexdigest()
assert data['sourceProducts'][0]['sha256']==ph and data['sourceProducts'][0]['url']==PAGE
assert proof['title'].endswith('22 Card Set - PR: 7287')
base=next(s for s in data['publishedSpecifications'] if s['name']==BASE)
expected=[['Rising Stars Parallel','Not stated'],*[[n,v] for n,v in COLORS]]
assert [r[:2] for r in base['rows']]==expected
assert 'explicitly unnumbered status' in base['rows'][0][2]
assert all('Unnumbered' not in str(row) for row in base['rows'])
auto=next(s for s in data['publishedSpecifications'] if s['name']==AUTO)
assert auto['headers'][0]=='Published statement' and '/5 or lower' in auto['rows'][0][0]
assert 'Upper bound only' in auto['rows'][0][1]
context=next(s for s in data['publishedSpecifications'] if s['name'].startswith('Set-wide'))
assert context['rows'][0][1]=='7287' and 'bundle' in context['rows'][0][2]
fields={r[0]:r[1] for r in context['rows'][2:]}
assert fields['Available From']=='Feb 9, 2026' and fields['Available Until']=='Feb 16, 2026'
entries=json.loads((root/'data/parallel-specifications.json').read_text())['sets'][SLUG]
assert len(entries)==6 and all(e['family']==BASE and e['evidenceSha256']==ph and e['source']==PAGE for e in entries)
assert [[e['name'],e['numbering']] for e in entries]==expected
assert not any(e['family']==AUTO for e in entries)
record=next(s for s in json.loads((root/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert record['releaseDate'] is None and record['releaseStatus']=='Unverified'
assert generic.run(record.copy())==record
assert not any(p['source']==PAGE for p in json.loads((root/'data/topps-now-observations.json').read_text()))
assert not json.loads((root/'data/topps-now-archive-index.json').read_text())['coverageComplete']
print('Verified all 37 NBA Rising Stars NOW physical rows, final-page Kyshawn George 21-A, literal Status/17 RC marks, original Rising Stars teams/positions/Egor Dёmin spelling, five base foil limits, unstated Rising Stars Parallel numbering, qualified autograph bound and bundle-only print run/sale dates.')
