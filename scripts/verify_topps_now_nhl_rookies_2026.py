"""Verify literal NHL Rookie Collection subjects, absent IDs and bundle scope."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import import_official_catalog as generic
from import_topps_now_nhl_rookies_2026 import SLUG,TITLE,PAGE,EVIDENCE,FAMILY,CONFIG,TERMS

root=Path(__file__).resolve().parents[1];proof=json.loads((root/EVIDENCE).read_text());ph=hashlib.sha256((root/EVIDENCE).read_bytes()).hexdigest()
data=json.loads((root/'data/imports'/(SLUG+'.json')).read_text())
assert data['source']==PAGE and data['sha256']==ph and data['sourceProducts'][0]['sha256']==ph
assert data['headers']==['Checklist section','Card number','Player / subjects','Team','Published subject','Official source']
assert len(data['rows'])==10 and all(len(r)==6 and r[0]==FAMILY and r[1]=='' and r[5]==PAGE for r in data['rows'])
text=proof['overview'].split(FAMILY+'\n',1)[1].split('The processing time',1)[0]
assert [line.strip() for line in text.splitlines() if line.strip()]==[r[4] for r in data['rows']]
assert all(r[4]==r[2]+' -- '+r[3] for r in data['rows'])
assert [r[2] for r in data['rows']]==['Matthew Schaefer','Michael Misa','Beckett Sennecke','Ivan Demidov','Ryan Leonard','Jimmy Snuggerud','Ben Kindel','Alexander Nikishin','Cole Hutson','Anton Frondell']
assert Counter(r[3] for r in data['rows'])=={'New York Islanders':1,'San Jose Sharks':1,'Anaheim Ducks':1,'Montréal Canadiens':1,'Washington Capitals':2,'St. Louis Blues':1,'Pittsburgh Penguins':1,'Carolina Hurricanes':1,'Chicago Blackhawks':1}
assert not data.get('odds') and not data.get('formats') and not data.get('serialColumn')
assert not any('rookie' in h.lower() for h in data['headers']) and proof['documentLinks']==[] and proof['title']==TITLE
terms=next(s for s in data['publishedSpecifications'] if s['name']=='Unjoined product Ice parallel terms')
assert [r[:2] for r in terms['rows']]==[[term,n] for term,n in zip(TERMS,['Unnumbered','/10','/5','/1'])]
assert terms['name']!=FAMILY and all('no exact per-subject eligibility' in r[2] for r in terms['rows'])
assert json.loads((root/'data/parallel-specifications.json').read_text())['sets'][SLUG]==[]
fields={r[0]:r[1] for r in next(s for s in data['publishedSpecifications'] if s['name'].startswith('Set-wide'))['rows']}
assert fields['Published bundle contents']==CONFIG and fields['Published bundle print run']=='600'
assert fields['Available From']=='Apr 20, 2026' and fields['Available Until']=='Apr 27, 2026'
assert fields['Product Year']=='2026' and fields['Season in title']=='2025-26'
assert fields['Printed sticker numbers']==fields['Per-sticker rookie marks']=='Not published'
record=next(s for s in json.loads((root/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert record['year']=='2026' and record['sport']=='hockey' and record['releaseDate'] is None and record['releaseStatus']=='Unverified' and record['coverageComplete'] is False
assert generic.run(record.copy())==record
assert not any(p['source']==PAGE for p in json.loads((root/'data/topps-now-observations.json').read_text()))
assert not json.loads((root/'data/topps-now-archive-index.json').read_text())['coverageComplete']
print('Verified ten exact NHL subject/team and original delimiter cells, blank IDs, no inferred rookie marks, four qualified unjoined Ice terms, bundle-only PR600 and separate season/product-year/sale dates.')
