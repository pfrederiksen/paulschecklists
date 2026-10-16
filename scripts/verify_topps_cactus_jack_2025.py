"""Independently verify Cactus Jack physical columns and all original odds pairs."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-26-topps-chrome-cactus-jack-basketball';FORMAT='Published odds (format not named)'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');compact=lambda s:re.sub(r'\s+','',s)
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
heads={compact(r[0]) for r in d['rows']}|{'INSERT','AUTOGRAPH'}
for pn,page in enumerate(PdfReader(path).pages,1):
 actual=[compact(line) for line in page.extract_text().splitlines() if compact(line) and compact(line) not in heads and not line.startswith(('Checklists provided','configuration of','production, but'))]
 expected=[compact(r[1]+r[2]+r[4]+r[5]) for r in d['rows'] if r[3]==str(pn)];assert actual==expected,(pn,actual,expected)
assert len(d['rows'])==338 and len({r[0] for r in d['rows']})==8 and len({tuple(r[:2]) for r in d['rows']})==338
assert d['rows']==d['originalSubjectRows']
assert {int(r[1]) for r in d['rows'] if r[0]=='BASE CARDS'}==set(range(1,101))
assert sum(r[5]=='Rookie' for r in d['rows'])==154
assert collections.Counter(r[0] for r in d['rows'] if r[5]=='Rookie')=={'BASE CARDS':40,'CACTUS INK':39,'BASE AUTOGRAPH VARIATION':25,'UTOPIA HIGHLIGHTS':20,'JACKED UP':10,'ASTROVISION':10,'CACTUS MODE':10}
assert next(r for r in d['rows'] if r[1]=='BV-Lm')[2:]==['Liam McNeeley','6','Charlotte Hornets','Rookie']
assert next(r for r in d['rows'] if r[1]=='CI-YH')[4]=='Portland Trailblazers'
assert next(r for r in d['rows'] if r[1]=='LFL-20')[4]=='Seattle Supersonics'
assert d['rows'][-1][1:]==['CI-YK','Yanic Konan-Niederhäuser','8','Los Angeles Clippers','Rookie']
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
for pn,page in enumerate(PdfReader(op).pages,1):
 actual=[compact(line) for line in page.extract_text().splitlines() if re.search(r'\d+:\d+$',line.strip())]
 expected=[compact(o['name']+o['values'][FORMAT]) for o in d['odds'] if o['page']==pn];assert actual==expected,(pn,actual,expected)
with pdfplumber.open(op) as pdf:
 for cell in d['oddsLayoutRows']:
  page=pdf.pages[cell['page']-1]
  for key,box in [('name','labelBox'),('value','valueBox')]:
   chars=[c for c in page.chars if abs(c['top']-cell[box][1])<.02];assert ''.join(c['text'] for c in chars).strip()==cell[key]
assert len(d['odds'])==60 and len(d['oddsLayoutRows'])==60 and not d['oddsIssues'] and not d['parallelSpecifications']
assert [(o['name'],o['values'],o['page']) for o in d['odds']]==[(o['name'],o['values'],o['page']) for o in d['officialOddsTable']]
assert d['formats']==[FORMAT] and d['officialOddsHeader']==['Odds'] and d['formatNamesPublished'] is False and d['oddsUnitsPublished'] is False
assert next(o for o in d['odds'] if o['name']=='Base')['values'][FORMAT]=='4:1'
assert {o['family'] for o in d['odds']}=={r[0] for r in d['rows']}
for spec in d['publishedSpecifications']:assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
print('Verified all 338 Cactus Jack source rows / eight families, 154 Rookie marks, original team/code spellings and 60 aligned literal odds cells. No format, ratio unit or serial ladder is inferred.')
