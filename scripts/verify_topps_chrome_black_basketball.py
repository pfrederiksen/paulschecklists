"""Validate printed numbering, rookie columns and physical row completeness."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
root=Path(__file__).resolve().parents[1];slug='topps-bowman-2026-topps-chrome-black-basketball'
data=json.loads((root/'data/imports'/f'{slug}.json').read_text());path=root/'data/catalog-sources/downloads'/f'{slug}.pdf'
assert hashlib.sha256(path.read_bytes()).hexdigest()==data['sha256']
assert data['dedicatedParser']=='scripts/import_topps_chrome_black_basketball.py'
assert len(data['rows'])==556
# Independent source-word scan counts every physical numbered line. Numeric
# prefixes in fused words belong to the number cell, not the player name.
printed=[]
with pdfplumber.open(path) as pdf:
 for page in pdf.pages:
  for word in page.extract_words():
   if word['x0']<98:
    m=re.match(r'^(\d+|[A-Z]+-[A-Z0-9]+)',word['text'])
    if m:printed.append(m[1])
assert collections.Counter(printed)==collections.Counter(r[1] for r in data['rows'])
rows=data['rows'];base=[r for r in rows if r[0]=='BASE CARDS'];rookies=[r for r in rows if r[0]=='ROOKIES'];variation=[r for r in rows if r[0]=='ROOKIE DESIGN VARIATION']
assert [int(r[1]) for r in base+rookies]==list(range(1,151))
assert next(r for r in base if r[1]=='31')[2:5]==['Karl-Anthony Towns','New York Knicks','']
assert next(r for r in rookies if r[1]=='128')[2:5]==['Will Richard','Golden State Warriors','Rookie']
assert len(variation)==30 and not any(r[1]=='128' for r in variation),'No absent variation number may be invented'
assert next(r for r in rows if r[1]=='CF-19')[3]=='Portland Trailblazers','Keep the printed team spelling'
assert sum(r[4]=='Rookie' for r in base)==5 and all(r[4]=='Rookie' for r in rookies)
print('Verified 556 physical card rows, all 150 base/rookie numbers, original teams and 30 literal design variations.')
