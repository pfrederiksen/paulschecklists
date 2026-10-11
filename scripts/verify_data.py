import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]
d=json.loads((p/'data/allen-ginter-2026.json').read_text())
assert len(d['sections'])==39 and len(d['odds'])==97
assert sum(len(s['cards']) for s in d['sections'])==2915
for s in d['sections']:
 assert len({c['number'] for c in s['cards']})==len(s['cards'])
 assert all(0<=i<len(d['odds']) for i in s['oddsIds'])
 for c in s['cards']:
  assert c['subjects'] and all(1<=x['page']<=57 and x['name'] for x in c['subjects'])
for o in d['odds']:
 assert set(o['odds'])=={'fat','hobby','value'}
 assert all(n is None or n>=1 for n in o['odds'].values())
by_name={o['name']:o for o in d['odds']}
assert by_name['BASE CARD MINI SIZED']['odds']=={'fat':1,'hobby':2,'value':3}
assert by_name['DYNASTY AUTOGRAPHED PATCH CARDS GOLD PARALLEL REDEMPTION CARD']['odds']['hobby']==505584
assert len(d['sections'][32]['cards'][0]['subjects'])==2
assert not next(s for s in d['sections'] if s['name']=='CAREER 250')['oddsIds']
print('Verified 2,915 cards, 39 sections, 97 odds entries and key source values.')
