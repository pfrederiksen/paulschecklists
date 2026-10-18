"""Verify every WrestleMania NOW physical cell, source typo and exact base foil scope."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
import pdfplumber
import import_official_catalog as generic
from import_topps_now_wrestlemania_2026 import SLUG,PAGE,URL,EVIDENCE,BASE,LEGEND,AUTO,LEGEND_AUTO,COLORS,BOUNDS

root=Path(__file__).resolve().parents[1];path=root/'data/catalog-sources/downloads'/(SLUG+'.pdf')
data=json.loads((root/'data/imports'/(SLUG+'.json')).read_text())
assert data['source']==URL and data['sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
assert data['headers']==['Checklist section','Card number','Subject','Source page'] and data['originalPrintedHeaders']==['Card No.','Subject']
assert Counter(r[0] for r in data['rows'])=={BASE:14,LEGEND:7,AUTO:12,LEGEND_AUTO:7}
assert len(data['rows'])==len({r[1] for r in data['rows']})==40
physical=[]
with pdfplumber.open(path) as doc:
 assert len(doc.pages)==2
 for pn,page in enumerate(doc.pages,1):
  words=page.extract_words();anchors=[w for w in words if w['x0']<120 and re.fullmatch(r'(?:\d+(?:-A)?|LSP-\d+A?)',w['text']) and (pn>1 or w['top']>100)]
  for anchor in anchors:
   line=sorted([w for w in words if abs(w['top']-anchor['top'])<.2],key=lambda w:w['x0'])
   physical.append([*[' '.join(w['text'] for w in line if lo<=w['x0']<hi) for lo,hi in [(50,120),(120,450)]],str(pn)])
assert physical==[r[1:] for r in data['rows']]
assert [r[1] for r in data['rows'] if r[0]==BASE]==[str(i) for i in range(1,15)]
assert [r[1] for r in data['rows'] if r[0]==AUTO]==[str(i)+'-A' for i in [1,2,3,4,6,7,8,9,10,11,12,14]]
assert [r[1] for r in data['rows'] if r[0]==LEGEND]==['LSP-'+str(i) for i in range(1,8)]
assert [r[1] for r in data['rows'] if r[0]==LEGEND_AUTO]==['LSP-'+str(i)+'A' for i in range(1,8)]
by_code={r[1]:r for r in data['rows']}
assert by_code['1'][2]=='"The American Nightmare" Cody Rhodes'
assert by_code['1-A'][2]=='"The American Nightmare\' Cody Rhodes'
assert by_code['LSP-4'][2]=='Bret "Hit Man" Hart' and by_code['LSP-4A'][2]=='Bret "Hit Man"'
assert by_code['LSP-7A']==[LEGEND_AUTO,'LSP-7A','Undertaker','2']
assert '5-A' not in by_code and '13-A' not in by_code
assert not data.get('odds') and not data.get('formats') and not data.get('serialColumn')
assert not any(re.search('rookie|^team$',h,re.I) for h in data['headers'])
proof=json.loads((root/EVIDENCE).read_text());ph=hashlib.sha256((root/EVIDENCE).read_bytes()).hexdigest()
assert data['sourceProducts'][0]['sha256']==ph and proof['url']==PAGE and proof['checklistUrl']==URL
assert proof['title'].endswith('15-Card Set - PR: 5847')
base=next(s for s in data['publishedSpecifications'] if s['name']==BASE)
assert [r[:2] for r in base['rows']]==[[n,v] for n,v in COLORS]
for family,term in BOUNDS.items():
 spec=next(s for s in data['publishedSpecifications'] if s['name']==family)
 assert spec['rows'][0][0]==term and 'Upper bound only;' in spec['rows'][0][1]
context=next(s for s in data['publishedSpecifications'] if s['name'].startswith('Set-wide'))
fields={r[0]:r[1] for r in context['rows']}
assert fields['Published bundle print run (title)']=='5847' and fields['Available From']=='Apr 13, 2026' and fields['Available Until']=='Apr 20, 2026'
assert fields['Event context']=='WrestleMania 42 · April 18–19' and 'not a general product release' in context['rows'][2][2]
entries=json.loads((root/'data/parallel-specifications.json').read_text())['sets'][SLUG]
assert len(entries)==5 and all(e['family']==BASE and e['evidenceSha256']==ph and e['source']==PAGE for e in entries)
assert [[e['name'],e['numbering']] for e in entries]==[[n,v] for n,v in COLORS]
record=next(s for s in json.loads((root/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert record['releaseDate'] is None and record['releaseStatus']=='Unverified' and record['coverageComplete'] is False
assert generic.run(record.copy())==record
assert not any(p['source']==PAGE for p in json.loads((root/'data/topps-now-observations.json').read_text()))
assert not json.loads((root/'data/topps-now-archive-index.json').read_text())['coverageComplete']
print('Verified all 40 WrestleMania NOW physical number/Subject cells, four rosters, literal Cody quote differences and omitted Hart, five base-only foils, separate autograph bounds and bundle/sale/event scope.')
