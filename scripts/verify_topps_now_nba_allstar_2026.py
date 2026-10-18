"""Verify every NBA All-Star NOW PDF cell and base-only specification join."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pdfplumber
import import_official_catalog as generic
from import_topps_now_nba_allstar_2026 import SLUG,URL,PAGE,EVIDENCE,BASE,AUTO,COLORS

root=Path(__file__).resolve().parents[1]
path=root/'data/catalog-sources/downloads'/(SLUG+'.pdf')
data=json.loads((root/'data/imports'/(SLUG+'.json')).read_text())
assert data['sha256']==hashlib.sha256(path.read_bytes()).hexdigest() and data['source']==URL
assert data['headers']==['Checklist section','Card number','Player','Position','Team','Source page']
assert data['originalPrintedHeaders']==['Card No.','Player','Position','Team']
assert Counter(r[0] for r in data['rows'])=={BASE:25,AUTO:12}
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
                               for lo,hi in [(50,120),(120,280),(280,325),(325,410)]],str(pn)])
assert physical==[r[1:] for r in data['rows']]
by_code={r[1]:r for r in data['rows']}
assert [r[1] for r in data['rows'] if r[0]==BASE]==[str(n) for n in range(1,26)]
assert [r[1] for r in data['rows'] if r[0]==AUTO]==[str(n)+'-A' for n in [5,6,7,9,11,12,13,14,16,17,20,21]]
assert data['rows'][-1]==[AUTO,'21-A','Chet Holmgren','C','USA Stars','2']
assert by_code['8'][2]=='Luka Dončić' and by_code['17-A'][2]=='Nikola Jokić'
assert by_code['11-A'][2]=='Shai Gilgeous-Alexander' and '1-A' not in by_code
assert Counter(r[4] for r in data['rows'])=={'World':14,'USA Stars':12,'USA Stripes':11}
assert not any(re.search('rookie|^rc$',h,re.I) for h in data['headers'])
assert not data.get('odds') and not data.get('formats') and not data.get('serialColumn')
proof=json.loads((root/EVIDENCE).read_text());ph=hashlib.sha256((root/EVIDENCE).read_bytes()).hexdigest()
assert data['sourceProducts'][0]['sha256']==ph and data['sourceProducts'][0]['url']==PAGE
assert proof['title'].endswith('26 Card Set - PR: 4967')
base=next(s for s in data['publishedSpecifications'] if s['name']==BASE)
expected=[['All-Star Parallel','Not stated'],*[[n,v] for n,v in COLORS]]
assert [r[:2] for r in base['rows']]==expected
assert 'explicitly unnumbered status' in base['rows'][0][2]
assert all('Unnumbered' not in str(row) for row in base['rows'])
auto=next(s for s in data['publishedSpecifications'] if s['name']==AUTO)
assert auto['headers'][0]=='Published statement' and '/5 or lower' in auto['rows'][0][0]
assert 'Upper bound only' in auto['rows'][0][1]
context=next(s for s in data['publishedSpecifications'] if s['name'].startswith('Set-wide'))
assert context['rows'][0][1]=='4967' and 'bundle' in context['rows'][0][2]
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
print('Verified all 37 NBA All-Star NOW physical rows, final-page 21-A, original All-Star teams/positions/accents, five base foil limits, unstated All-Star Parallel numbering, qualified autograph bound and bundle-only print run/sale dates.')
