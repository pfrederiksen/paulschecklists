"""Check MLS backfills against original card-number glyphs and published scope."""
import json,re,hashlib
from pathlib import Path
import pdfplumber
from import_topps_mls_2025 import CONFIG,ROOT
for title,slug,page,cl,od,date in CONFIG:
 d=json.loads((ROOT/'data/imports'/f'{slug}.json').read_text())
 p=ROOT/'data/catalog-sources/downloads'/f'{slug}.pdf'
 assert hashlib.sha256(p.read_bytes()).hexdigest()==d['sha256']
 source=[]
 with pdfplumber.open(p) as pdf:
  for pn,page in enumerate(pdf.pages,1):
   # Font distinguishes the AUTOGRAPH-RELIC group heading from card codes.
   words=page.extract_words(extra_attrs=['fontname'])
   source.extend((w['text'],str(pn)) for w in words if w['x0']<132 and 'Bold' not in w['fontname'] and 'Italic' not in w['fontname'] and re.fullmatch(r'\d+|[A-Z0-9]+-[A-Z0-9]+',w['text']))
 assert source==[(row[1],row[-1]) for row in d['rows']],title
 base=[r for r in d['rows'] if r[0] in ('BASE CARDS','PITCH PRODIGIES')]
 assert [int(r[1]) for r in base]==list(range(1,201))
 assert len([r for r in base if r[0]=='PITCH PRODIGIES'])==25
 assert next(r for r in base if r[1]=='6')[2:5]==['Cavan Sullivan','Philadelphia Union','Rookie']
 assert all(r[4] in ('','Rookie') for r in d['rows'])
 if 'Sapphire' in title:
  assert len(d['rows'])==358 and len(d['odds'])==29 and d['formats']==['Sapphire']
  assert len(d['officialOddsTable'])==186
  assert next(o for o in d['odds'] if o['name']=='Base Cards Gold Sapphire')['values']=={'Sapphire':'1:5'}
  assert all(o['values'].get('Hobby') is None for o in d['odds'])
 else:
  assert len(d['rows'])==861 and len(d['odds'])==186
  assert next(r for r in d['rows'] if r[1]=='MLS-1')[2:5]==['','','']
  assert next(r for r in d['rows'] if r[0]=='BASE CARDS SUPER SHORT PRINTS' and r[1]=='154')[2:5]==['Bob Marley','','']
  assert any('Lionel Messi' in ' '.join(n) and 'Black Donut Holes /10' in ' '.join(n) for sheet in d['sourceSheets'] for n in sheet['notes'])
print('Verified every MLS printed card-code glyph, physical base/rookie values, blank subjects, card-specific exclusion and Sapphire-only odds scope.')
