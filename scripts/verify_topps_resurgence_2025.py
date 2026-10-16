"""Independently compare all physical Resurgence subjects and four odds columns."""
import collections,hashlib,json,re,sys,copy
from pathlib import Path
from pypdf import PdfReader
import pdfplumber
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-topps-resurgence-football'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
compact=lambda s:re.sub(r'\s+','',s)
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
heads={compact(r[0]) for r in d['rows']}|{'INSERT','AUTOGRAPH','AUTOGRAPHRELIC'}
for pn,page in enumerate(PdfReader(path).pages,1):
 actual=[compact(line) for line in page.extract_text().splitlines() if compact(line) and compact(line) not in heads and not line.startswith(('Checklists provided','product at','vary.'))]
 expected=[compact(r[1]+r[2]+r[4]+r[5]) for r in d['rows'] if r[3]==str(pn)]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b])
assert len(d['rows'])==749 and len({r[0] for r in d['rows']})==19 and len({tuple(r[:2]) for r in d['rows']})==749
assert d['originalSubjectRows']==d['rows'] and sum(r[5]=='Rookie' for r in d['rows'])==379
assert {int(r[1]) for r in d['rows'] if r[0]=='BASE'}==set(range(1,101))
assert {int(r[1]) for r in d['rows'] if r[0]=='ROOKIES'}==set(range(101,203))-{106,183}
assert sum(r[0]=='Base Signatures' for r in d['rows'])==70 and sum(r[0]=='Rookie Signatures' for r in d['rows'])==90
assert next(r for r in d['rows'] if r[:2]==['BASE','26'])[2:]==['Micah Parsons','1','Green Bay Packers','']
assert next(r for r in d['rows'] if r[:2]==['BASE','43'])[2:]==['Sauce Gardner','1','Indianapolis Colts','']
assert d['rows'][-1]==['RADIAL ROOKIE RELICS','RRA-TW','Tyler Warren','16','Indianapolis Colts','Rookie']
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
assert d['formats']==['Hobby Pack Rate','Delight Pack Rate','Value Pack Rate','Mega Pack Rate'] and d['formatNamesPublished'] and d['oddsUnitsPublished']
for pn,page in enumerate(PdfReader(op).pages,1):
 lines=[compact(line) for line in page.extract_text().splitlines() if not line.startswith(('Checklists and odds','inclusion of a subject'))]
 actual=lines[1:] if pn==1 else lines
 if pn==1:assert lines[0]==compact(''.join(d['officialOddsHeader']))
 expected=[compact(o['name']+''.join(o['values'][f] or '-' for f in d['formats'])) for o in d['officialOddsTable'] if o['page']==pn]
 assert actual==expected,(pn,actual[:10],expected[:10])
assert len(d['odds'])==249 and not d['oddsIssues']
assert [(o['name'],o['values'],o['page']) for o in d['odds']]==[(o['name'],o['values'],o['page']) for o in d['officialOddsTable']]
assert {o['family'] for o in d['odds']}=={r[0] for r in d['rows']}
assert next(o for o in d['odds'] if o['name']=='Rookies Signatures Gold Power Surge')['family']=='Rookie Signatures'
assert next(o for o in d['odds'] if o['name']=='Base Signatures Gold Power Surge')['family']=='Base Signatures'
e=d['oddsLiteralExceptions'][0];assert e['value']=='0.05' and e['format']=='Mega Pack Rate'
with pdfplumber.open(op) as pdf:
 b=e['valueBox'];cs=[c for c in pdf.pages[0].chars if b[0]<=c['x0'] and c['x1']<=b[2] and b[1]-.01<=c['top'] and c['bottom']<=b[3]+.01]
 assert ''.join(c['text'] for c in cs)=='0.05'
 assert pdf.pages[0].find_tables()[0].extract()==[d['officialOddsHeader']]
for spec in d['publishedSpecifications']:assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
specs=d['parallelSpecifications'];assert len(specs)==3
assert {s['oddsName']:s['numbering'] for s in specs}=={'Base Crimson Surge':'/199','Rookies Crimson Surge':'/199','Neon Initiates Gold Power Surge':'Limited to 50 copies (serial numbering not stated)'}
assert all(s.get('numbering')!='/15' for s in specs),'A named subject example must not number a family'
r=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG)
assert r['releaseDate'] is None and r['year']=='2025' and r['dedicatedParser']=='scripts/import_topps_resurgence_2025.py'
sys.path.insert(0,str(ROOT/'scripts'));from import_official_catalog import run
assert run(copy.deepcopy(r))==r,'Generic refresh must preserve this dedicated import'
print('Verified all 749 Resurgence physical subjects, 19 families, 379 Rookie marks and all 249 × 4 literal odds cells; decimal, scoped limits, guide discrepancy and card examples preserved.')
