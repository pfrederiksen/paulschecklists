"""Independently reconcile Disney Neon codes and guard original field scopes."""
import json,hashlib,collections
from pathlib import Path
import pdfplumber
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-disney-neon'
d=json.loads((ROOT/'data/imports'/f'{SLUG}.json').read_text());p=ROOT/'data/catalog-sources/downloads'/f'{SLUG}.pdf'
assert hashlib.sha256(p.read_bytes()).hexdigest()==d['sha256']
codes=[]
with pdfplumber.open(p) as pdf:
 for pn,page in enumerate(pdf.pages,1):
  groups=collections.defaultdict(list);limit=88.32 if pn<3 else 72.28 if pn<5 else 91.16
  for c in page.chars:
   if c['x0']<limit-.01 and 'Verdana' in c['fontname'] and 'Bold' not in c['fontname']:groups[round(c['top'],1)].append(c)
  for y,chars in sorted(groups.items()):
   text=''.join(c['text'] for c in chars).strip()
   if text:codes.append((text,str(pn)))
assert codes==[(r[1],r[3]) for r in d['rows']]
assert len(d['rows'])==720
base=[r for r in d['rows'] if r[0]=='BASE CARDS'];assert [int(r[1]) for r in base]==list(range(1,201))
assert next(r for r in base if r[1]=='45')[6:]==['22','Soul']
assert next(r for r in base if r[1]=='19')[6:]==['WALL-E','WALL-E']
assert any(r[4:8]==['Booboo','Stewart','Jay','Descendants'] for r in d['rows'])
assert len([r for r in d['rows'] if r[0]=='TRIPLE BOOKLET SUPERFRACTOR AUTOGRAPH CARD'])==33,'Retain every printed signer row rather than inventing one consolidated card'
assert d['headers'][4:]==['First Name','Last Name','Character','Property']
assert len(d['odds'])==108 and len(d['formats'])==7
assert len([o for o in d['odds'] if not any(o['values'].values())])==8
assert next(o for o in d['odds'] if o['name']=='Base Cards Gold Parallel')['values']['Hobby']=='1:172'
assert next(o for o in d['odds'] if o['name']=='Family First')['values']['Hobby']=='1:2'
assert len({o['name'] for o in d['odds']})==108
assert next(o for o in d['odds'] if o['name']=='A Goofy Movie 30th Anniversary Auto Variation Gold Refractor Parallel')['family']=='A GOOFY MOVIE AUTOGRAPH VARIATION'
assert next(o for o in d['odds'] if o['name']=='A Goofy Movie 30th Anniversary Gold Parallel')['family']=='A GOOFY MOVIE'
assert next(o for o in d['odds'] if o['name']=='Topps Neon Autographs PETG Pink 1/1 Parallel')['numbering']=='1/1'
print('Verified all 720 Disney Neon card-number glyphs, printed actor/character/property columns, repeated signers and 108 complete odds cells.')
