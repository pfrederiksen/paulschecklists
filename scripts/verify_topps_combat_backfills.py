"""Verify combat checklist columns, base numbers, overlapping cells and odds."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
ROOT=Path(__file__).resolve().parents[1]
CONFIG={'topps-bowman-2026-topps-midnight-ufc':(484,99),'topps-bowman-2025-topps-royalty-wwe':(739,96)}
for slug,(expected,boundary) in CONFIG.items():
 d=json.loads((ROOT/'data/imports'/f'{slug}.json').read_text());p=ROOT/'data/catalog-sources/downloads'/f'{slug}.pdf'
 assert hashlib.sha256(p.read_bytes()).hexdigest()==d['sha256']
 assert d['dedicatedParser']=='scripts/import_topps_combat_backfills.py'
 assert len(d['rows'])==expected
 numbers=[]
 with pdfplumber.open(p) as pdf:
  for page in pdf.pages:
   lines=collections.defaultdict(list)
   for w in page.extract_words(x_tolerance=.1):
    if w['x0']<boundary:lines[round(w['top'],1)].append(w)
   for ws in lines.values():
    value=''.join(w['text'] for w in sorted(ws,key=lambda w:w['x0']))
    if re.fullmatch(r'\d+|[A-Z0-9]+-[A-Z0-9-]+',value) and (not value.isdigit() or min(w['x0'] for w in ws)>80):numbers.append(value)
 assert collections.Counter(numbers)==collections.Counter(r[1] for r in d['rows']),(slug,collections.Counter(numbers)-collections.Counter(r[1] for r in d['rows']))
 base=[r for r in d['rows'] if r[0]=='BASE CARDS'];assert [int(r[1]) for r in base]==list(range(1,101))
 assert 'Team' not in d['headers']
 if 'royalty' in slug:
  assert next(r for r in base if r[1]=='14')[2:5]==['"The American Nightmare" Cody Rhodes','Smackdown','']
  assert next(r for r in base if r[1]=='9')[3]=='Smckdown','Retain the publisher spelling'
  assert sum(r[4]=='Rookie' for r in base)==3
  assert len([r for r in d['rows'] if r[0]=='100 PERCENT STRATUSFACTION RELICS'])==5
  assert len(d['odds'])==118 and d['formats']==['Pack Odds']
 else:
  assert next(r for r in base if r[1]=='14')[2:4]==['Chang Ho Lee','Rookie']
  assert sum(r[3]=='Rookie' for r in base)==57
  assert len(d['odds'])==86 and d['formats']==['Hobby']
  assert d['oddsRawPages'][0]['text'].startswith('2026 Topps Midnight UFC')
  assert next(o for o in d['odds'] if o['name']=='Base Moonrise')['values']=={'Hobby':'1:8'}
  assert next(o for o in d['odds'] if o['name']=='Base Autograph Variations Black Light')['values']=={'Hobby':'1:348'}
  assert not any(o['name'].startswith(('NIGHTFALL','LUNAR TIDE','CONSTELLATIONS')) for o in d['odds'])
  assert any(s['formats']==['2025 TOPPS MIDNIGHT UFC HOBBY'] for s in d['supersededOddsSources'])
  spec=d['publishedSpecifications'][0];assert 'Limited to 8 and 1' in str(spec['rows']) and 'Published numbering' not in spec['headers']
  assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
 print('Verified',slug,expected,'physical rows, all 100 base numbers, original published fields and source-scoped odds.')
