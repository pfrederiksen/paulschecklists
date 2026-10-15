"""Reconcile all printed Transcendent card IDs and physical source fields."""
import collections, hashlib, json, re
from pathlib import Path
import pdfplumber
ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2025-topps-transcendent-collection-baseball'
d=json.loads((ROOT/'data/imports'/f'{SLUG}.json').read_text())
p=ROOT/'data/catalog-sources/downloads'/f'{SLUG}.pdf'
assert hashlib.sha256(p.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_transcendent_2025.py'
assert d['headers']==['Checklist section','Card number','Name','Team','Rookie','Source page']
assert len(d['rows'])==1385 and len({r[0] for r in d['rows']})==35
# Independently enumerate the printed number column with positioned words.
ids=[];rookies=0
with pdfplumber.open(p) as pdf:
 for pn,page in enumerate(pdf.pages,1):
  words=page.extract_words(x_tolerance=.1)
  for w in words:
   if w['x1']<132 and (pn>1 or w['top']>130) and re.fullmatch(r'\d+|[A-Z0-9]+-[A-Z0-9-]+|CYCS|CRCS|CFCS|PRCS',w['text']) and (not w['text'].isdigit() or w['x0']>100):
    ids.append((str(pn),w['text']))
  rookies+=sum(abs(c['x0']-421.27)<.03 and c['text']=='R' for c in page.chars)
assert collections.Counter(ids)==collections.Counter((r[-1],r[1]) for r in d['rows'])
assert rookies==383==sum(r[4]=='Rookie' for r in d['rows'])
for family in ['TRANSCENDENT ICONS CHROME BASE CARDS','TRANSCENDENT ICONS CHROME IMAGE VARIATIONS']:
 assert [int(r[1]) for r in d['rows'] if r[0]==family]==list(range(1,101))
assert not any(r[1] in ['2025','1961'] for r in d['rows'])
assert len([r for r in d['rows'] if r[0]=='2025 ROOKIE THROUGH THE YEARS AUTOGRAPHS'])==89
assert len([r for r in d['rows'] if r[0]=='1961 TOPPS COMBOS SUPERFRACTOR AUTOGRAPHS'])==14
assert [r[1:4] for r in d['rows'] if r[0]=='GEMSTONES']==[
 ['CYCS','Cy Young','Cleveland Naps®'],['CRCS','Lou Gehrig','New York Yankees®'],['CRCS','Cal Ripken Jr.','Baltimore Orioles®'],['CFCS','Carlton Fisk','Boston Red Sox®'],['PRCS','Ty Cobb','Detroit Tigers®'],['PRCS','Pete Rose','Cincinnati Reds®']]
assert [r[2:5] for r in d['rows'] if r[1]=='IG-1984']==[['Ken Griffey Jr.','Seattle Mariners™',''],['Ichiro','Seattle Mariners™','']]
assert next(r for r in d['rows'] if r[1]=='JJ-1971')[2:5]==['Derek Jeter','New York Yankees®','Rookie'],'Preserve even apparently erroneous published rookie marks'
assert not d.get('odds') and not d.get('formats')
specs=json.loads((ROOT/'data/parallel-specifications.json').read_text())['sets'][SLUG]
assert len(specs)==33
for s in specs:assert hashlib.sha256((ROOT/s['evidenceFile']).read_bytes()).hexdigest()==s['evidenceSha256']
assert not any('COMBOS' in s['family'] or 'THROUGH THE YEARS' in s['family'] for s in specs)
assert not any(s['family']=='TRANSCENDENT ICONS CHROME BASE CARDS' and s['name']=='Base' for s in specs),'VIP base is separate from Chrome'
assert next(s for s in specs if s['name']=='Autograph Parallel')['numbering']=='/25 or less'
assert next(s for s in specs if s['name']=='Original autograph (print limit)')['numbering']=='Limited to 25 copies'
assert next(s for s in specs if s['family']=='GEMSTONES')['numbering']=='One-of-one'
assert not any(s['family']=='LARRY DAVID AUTOGRAPH' and s['numbering']=='/10' for s in specs)
record=next(s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert record['releaseDate'] is None
print('Verified Transcendent: 1,385 physical IDs and subjects, 35 sections, 383 literal Rookie marks, six Gemstones and 33 source-scoped specifications; no inferred odds, VIP roster or release date.')
