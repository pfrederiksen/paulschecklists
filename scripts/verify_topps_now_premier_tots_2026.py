"""Verify the literal Premier League NOW base roster and unjoined chase evidence."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import import_official_catalog as generic
from import_topps_now_premier_tots_2026 import SLUG,TITLE,PAGE,EVIDENCE,FAMILY,LIMITS

root=Path(__file__).resolve().parents[1];proof=json.loads((root/EVIDENCE).read_text());ph=hashlib.sha256((root/EVIDENCE).read_bytes()).hexdigest()
data=json.loads((root/'data/imports'/(SLUG+'.json')).read_text())
assert data['source']==PAGE and data['sha256']==ph and data['sourceProducts'][0]['sha256']==ph
assert data['headers']==['Checklist section','Card number','Player / subjects','Team','Published subject','Official source']
assert len(data['rows'])==11 and all(len(r)==6 and r[0]==FAMILY and r[1]=='' and r[5]==PAGE for r in data['rows'])
text=proof['description'].split(FAMILY+'\n',1)[1].split('All sales are final.',1)[0]
assert [line for line in text.splitlines() if line]==[r[4] for r in data['rows']]
assert all(r[4]==r[2]+' ('+r[3]+')' for r in data['rows'])
assert Counter(r[3] for r in data['rows'])=={'Arsenal':5,'Manchester City':3,'Liverpool FC':1,'Manchester United':1,'Brentford':1}
assert data['rows'][1][2]=='Gabriel Magalhães' and data['rows'][3][2]=='Jurriën Timber' and data['rows'][4][2]=='Nico O’Reilly'
assert data['rows'][-1][2:] == ['Igor Thiago','Brentford','Igor Thiago (Brentford)',PAGE]
assert not data.get('odds') and not data.get('formats') and not data.get('serialColumn')
assert not any('rookie' in h.lower() for h in data['headers']) and proof['documentLinks']==[] and proof['title']==TITLE
assert 'PR:' not in proof['title'] and dict(proof['specs'])['Product Year']=='2026'
chase=next(s for s in data['publishedSpecifications'] if s['name']=='Unjoined product chase numbering')
expected=[[heading,n] for heading,limits in LIMITS.items() for n in limits]+[['unnumbered parallel','Unnumbered']]
assert [r[:2] for r in chase['rows']]==expected
assert chase['name'] not in {r[0] for r in data['rows']} and len(chase['rows'])==9
assert all('no color, exact checklist-family join or per-player eligibility' in r[2] for r in chase['rows'][:8])
assert json.loads((root/'data/parallel-specifications.json').read_text())['sets'][SLUG]==[]
context=next(s for s in data['publishedSpecifications'] if s['name'].startswith('Set-wide'))
fields={r[0]:r[1] for r in context['rows']}
assert fields['Available From']=='Jun 11, 2026' and fields['Available Until']=='Jun 18, 2026'
assert fields['Published print run']==fields['Printed card numbers']==fields['Autograph roster']=='Not published'
assert fields['Season in Description']=='2025/26'
record=next(s for s in json.loads((root/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert record['year']=='2026' and record['releaseDate'] is None and record['releaseStatus']=='Unverified' and record['coverageComplete'] is False
assert generic.run(record.copy())==record
assert not any(p['source']==PAGE for p in json.loads((root/'data/topps-now-observations.json').read_text()))
assert not json.loads((root/'data/topps-now-archive-index.json').read_text())['coverageComplete']
print('Verified all 11 Premier League fixed-base names/clubs and original parentheticals, blank IDs, six unnamed Parallel limits, two Auto limits, explicitly unnumbered term, no family joins and separate season/product-year/sale dates.')
