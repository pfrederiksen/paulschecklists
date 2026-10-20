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
proof_path=root/'data/parallel-audit-sources/flagship-football-london-2026-20261020.json'
proof=json.loads(proof_path.read_text());digest=hashlib.sha256(proof_path.read_bytes()).hexdigest()
assert d['londonGuideEvidence']['sha256']==digest
assert proof['checklist']['sha256']==d['sha256'] and proof['odds']['sha256']==d['oddsSha256']
specs=json.loads((root/'data/parallel-specifications.json').read_text())['sets'][slug]
assert len(specs)==30 and {s['family'] for s in specs}==base
limits={'Big Ben':'/59','Tudor Rose':'/5','Crown Jewels':'1/1','Union Jack Rainbow Foil':'Numbering not stated','Union Jack Blue Rainbow Foil':'Numbering not stated'}
for family in base:
 ss=[s for s in specs if s['family']==family]
 assert len(ss)==5 and {s['name']:s['numbering'] for s in ss}==limits
 for s in ss:
  assert s['evidenceSha256']==digest and 'London Store Exclusive Mega Box paper base program only' in s['qualification']
  assert any(o['name']==s['oddsName'] for o in d['odds'])
assert not any('AUTOGRAPH' in s['family'] or 'CHROME' in s['family'] or 'VARIATION' in s['family'] for s in specs)
assert len(d['odds'])==1097 and all(list(o['values'])==d['formats'] for o in d['odds'])
assert [o['values']['London Games Me Pack Rate'] for o in d['odds'] if o['name']=='Base Cards Big Ben']==['1:22','1:22','1:36']
record=next(s for s in json.loads((root/'data/set-catalog.json').read_text())['sets'] if s['slug']==slug)
assert record['releaseDate']=='2026-08-21' and record['releaseStatus']=='Released'
assert any(s['name']=='Manufacturer London Store Exclusive scope' and s['evidenceSha256']==digest for s in d['publishedSpecifications'])
print('Verified all 4082 source numbers, 4171 subjects, 89 attached signers, base numbers 1–400 and literal 20-column odds.')
print('Verified five London-only paper base programs across six exact families; only Big Ben /59, Tudor Rose /5 and Crown Jewels 1/1. All repeated odds captions and the regular release date retained; exhaustive numbering remains incomplete.')
