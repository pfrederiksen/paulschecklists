"""Check every Flagship Football source number and continuation subject."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
root=Path(__file__).resolve().parents[1];slug='topps-bowman-2026-topps-flagship-football';d=json.loads((root/'data/imports'/f'{slug}.json').read_text());p=root/'data/catalog-sources/downloads'/f'{slug}.pdf'
assert hashlib.sha256(p.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_flagship_football_2026.py'
assert len(d['rows'])==4082 and len(d['originalSubjectRows'])==4171
printed=[]
with pdfplumber.open(p) as pdf:
 for page in pdf.pages:
  lines=collections.defaultdict(list)
  for w in page.extract_words(x_tolerance=.1):lines[round(w['top'],1)].append(w)
  for ws in lines.values():
   if any(abs(w['x0']-173.06)<.03 for w in ws):
    number=''.join(w['text'] for w in ws if w['x0']<172)
    if number:printed.append(number)
assert collections.Counter(printed)==collections.Counter(r[1] for r in d['rows'])
base={'BASE CARDS I','FUTURE STARS','TEAM CARDS','LEAGUE LEADERS','COMBO CARDS','ROOKIES'}
assert {int(r[1]) for r in d['rows'] if r[0] in base}==set(range(1,401))
assert len([r for r in d['rows'] if r[0]=='LEAGUE LEADERS'])==30,'Repeated printed numbers must remain'
assert next(r for r in d['rows'] if r[0]=='BASE CARDS I' and r[1]=='66')[2:4]==['Amon-Ra St. Brown','Detroit Lions']
triple=next(r for r in d['rows'] if r[1]=='NFLTA-ABM');ss=json.loads(triple[6]);assert [s['Name'] for s in ss]==['Drake Maye','Josh Allen','Joe Burrow'];assert [s['Printed card number'] for s in ss]==['NFLTA-ABM','','']
assert sum(len(json.loads(r[6]))-1 for r in d['rows'])==89
assert any(r[5]=='Rookie Silver Pack Auto' and r[4]=='Rookie' for r in d['rows'])
assert all(teams==list(dict.fromkeys(s['Team'] for s in json.loads(row[6]) if s['Team'])) for row,teams in zip(d['rows'],d['rowTeams']))
assert len(d['odds'])==1097 and len(d['formats'])==20
assert next(o for o in d['odds'] if o['name']=='Base Cards Base')['values']['Hobby Pack Rate']=='1:1'
assert not any('provided by' in f or '*Chec' in f for f in d['formats'])
print('Verified all 4082 source numbers, 4171 subjects, 89 attached signers, base numbers 1–400 and literal 20-column odds.')
