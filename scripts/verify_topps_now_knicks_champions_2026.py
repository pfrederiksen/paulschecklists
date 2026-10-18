"""Check all published web roster rows, blank IDs and exact redemption scopes."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import import_official_catalog as generic
from import_topps_now_knicks_champions_2026 import SLUG,TITLE,PAGE,EVIDENCE,BASE,IMAGE,AUTO,REDEMPTIONS,FOILS

root=Path(__file__).resolve().parents[1]
proof=json.loads((root/EVIDENCE).read_text());ph=hashlib.sha256((root/EVIDENCE).read_bytes()).hexdigest()
data=json.loads((root/'data/imports'/(SLUG+'.json')).read_text())
assert data['source']==PAGE and data['sha256']==ph and data['sourceProducts'][0]['sha256']==ph
assert data['sourceKind']=='official-browser-product-factual-excerpt' and 'not raw HTML' in data['sourceHashQualification']
assert data['headers']==['Checklist section','Card number','Player / subjects','Published statement','Official source']
assert len(data['rows'])==35 and all(len(r)==5 and r[1]=='' and r[4]==PAGE for r in data['rows'])
assert Counter(r[0] for r in data['rows'])=={BASE:15,IMAGE:8,AUTO:9,**{term:1 for term,_ in REDEMPTIONS}}
text=proof['description'];expected=[]
for heading,stop in [(BASE,IMAGE),(IMAGE,AUTO),(AUTO,'Your Hero. Your Team. Your Moment. ™')]:
 part=text.split(heading+'\n',1)[1].split(stop,1)[0]
 expected.extend((heading,line) for line in part.splitlines() if line)
assert expected==[(r[0],r[2]) for r in data['rows'][:32]]
assert data['rows'][0][2]=='Jalen Brunson' and data['rows'][14][2]=='Jeremy Sochan'
assert data['rows'][10][2]=='Pacôme Dadiet' and data['rows'][29][2]=='Miles\u00a0McBride'
for row,(term,subjects) in zip(data['rows'][32:],REDEMPTIONS):assert row==[term,'',subjects,term,PAGE]
assert data['rows'][-1][2]=='Knicks Starting 5' and not any(r[2]=='Walt Frazier' for r in data['rows'])
assert not any('team'==h.lower() or 'rookie'==h.lower() for h in data['headers'])
assert not data.get('odds') and not data.get('formats') and not data.get('serialColumn')
assert proof['documentLinks']==[] and proof['title']==TITLE+' - PR: 65941'
fields=dict(proof['specs']);assert fields['Available From']=='Jun 13, 2026' and fields['Available Until']=='Jun 20, 2026'
context=next(s for s in data['publishedSpecifications'] if s['name'].startswith('Set-wide'))
assert context['rows'][0][1]=='65941' and 'Bundle-level only' in context['rows'][0][2]
unjoined=next(s for s in data['publishedSpecifications'] if s['name'].startswith('Unjoined'))
assert [r[:2] for r in unjoined['rows'][:7]]==[[name,n] for name,n in FOILS]
assert all('No base, image-variation or autograph subject eligibility is inferred.' in r[2] for r in unjoined['rows'][:7])
auto=next(s for s in data['publishedSpecifications'] if s['name']==AUTO)
assert auto['rows'][0][0]=='On-Card Autograph Redemptions /10 or less' and 'Upper bound only.' in auto['rows'][0][1]
entries=json.loads((root/'data/parallel-specifications.json').read_text())['sets'][SLUG]
assert len(entries)==3 and {e['family'] for e in entries}=={t for t,_ in REDEMPTIONS}
assert all(e['numbering']=='1/1' and e['evidenceSha256']==ph and e['source']==PAGE for e in entries)
assert not any(e['family'] in {BASE,IMAGE,AUTO} for e in entries)
record=next(s for s in json.loads((root/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert record['releaseDate'] is None and record['releaseStatus']=='Unverified' and record['coverageComplete'] is False
assert generic.run(record.copy())==record
assert not any(p['source']==PAGE for p in json.loads((root/'data/topps-now-observations.json').read_text()))
assert not json.loads((root/'data/topps-now-archive-index.json').read_text())['coverageComplete']
print('Verified all 32 Knicks subject-list rows and three named redemption captions, blank IDs, exact accents/spacing, three isolated 1/1 joins, seven unjoined foil limits, autograph upper bound and bundle-only run/sale dates.')
