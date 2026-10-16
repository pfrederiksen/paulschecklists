"""Independently check physical signer rows, source blanks and literal Hobby odds."""
import collections,hashlib,json,logging,re,unicodedata
from pathlib import Path
from pypdf import PdfReader
import pdfplumber
logging.getLogger('pypdf').setLevel(logging.ERROR)
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-26-bowman-university-best-basketball'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
norm=lambda s:re.sub(r'\s+','',unicodedata.normalize('NFKC',s))
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_bowman_u_best_basketball_2025.py'
headings={norm(r[0]) for r in d['rows']}|{'INSERT','AUTOGRAPH','AUTOGRAPHRELIC'}
for pn,page in enumerate(PdfReader(path).pages,1):
 actual=[]
 for line in page.extract_text(extraction_mode='layout').splitlines():
  v=norm(line)
  if not v or v in headings or v.startswith(('Checklistsprovided','intendedconfiguration','thetimeofproduction','contentsandoddsmayvary')):continue
  actual.append(v)
 expected=[norm(r[5]+r[2]+r[4]) for r in d['rows'] if r[3]==str(pn)]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b][:4],len(actual),len(expected))
assert len(d['rows'])==658 and len({tuple(r[:2]) for r in d['rows']})==618
assert len(d['sourceContinuationRows'])==40 and sum(not r[5] for r in d['rows'])==40
assert d['originalSubjectRows']==[[r[0],r[5],r[2],r[3],r[4]] for r in d['rows']]
count=collections.Counter(r[0] for r in d['rows']);assert len(count)==17
assert count['BASE CARDS']==100 and count['BEST OF 2025 AUTOGRAPHS']==100 and count['GAME GRAPHS']==89
assert {int(r[1]) for r in d['rows'] if r[0]=='BASE CARDS'}==set(range(1,101))
for family,n,size in [('DUAL AUTOGRAPHS REFRACTOR',20,2),('TRIPLE AUTOGRAPHS REFRACTOR',10,3)]:
 c=collections.Counter(r[1] for r in d['rows'] if r[0]==family);assert len(c)==n and set(c.values())=={size}
assert [r[2] for r in d['rows'] if r[1]=='DRA-AD']==['AJ Dybantsa','Darryn Peterson']
assert [r[2] for r in d['rows'] if r[1]=='TRA-NB']==['Nyla Brooks','Grace Knox','Hailee Swain']
assert [r[3] for r in d['rows'] if r[1]=='TRA-NB']==['9','10','10']
assert d['rows'][-1][1:] == ['GGBM','Brynn McGaughy','13','Washington®','GGBM']
assert next(r for r in d['rows'] if r[:2]==['BASE CARDS','47'])[4]=='Maryland™'
assert 'Rookie' not in d['headers']
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
expected=[]
with pdfplumber.open(op) as pdf:
 for pn,page in enumerate(pdf.pages,1):
  tables=page.find_tables();assert len(tables)==1
  for row in tables[0].extract():
   full=' '.join(' '.join((v or '').split()) for v in row)
   if full=='Card Hobby':continue
   match=re.fullmatch(r'(.+?) ([\d,]+:[\d,]+)',full);assert match,(pn,full)
   expected.append((pn,norm(match[1]),match[2]))
assert expected==[(o['page'],norm(o['name']),o['values']['Hobby']) for o in d['odds']]
assert len(expected)==133 and d['formats']==['Hobby']
assert d['formatNamesPublished'] is True and d['oddsUnitsPublished'] is False
assert all(o['family'] in count for o in d['odds'])
assert {o['family'] for o in d['odds'] if o['familyBase']}==set(count)
by={o['name']:o for o in d['odds']}
assert by['Dual Autos Refractors Refractor']['family']=='DUAL AUTOGRAPHS REFRACTOR'
assert by['Prospect Dual Relic Auto']['family']=='PROSPECT DUAL RELIC AUTOGRAPHS'
specs=d['parallelSpecifications'];assert len(specs)==1
assert specs[0]['family']=='LETS GO' and specs[0]['numbering']=='1/1' and specs[0]['oddsName']=="LET'S GO Superfractor"
for s in specs:assert hashlib.sha256((ROOT/s['evidenceFile']).read_bytes()).hexdigest()==s['evidenceSha256']
registry=json.loads((ROOT/'data/parallel-specifications.json').read_text());assert registry['sets'][SLUG]==specs
record=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG)
assert record['releaseDate'] is None and record['rowCount']==658
inventory=next(r for r in json.loads((ROOT/'data/topps-product-official-catalog.json').read_text()) if r['slug']==SLUG)
assert inventory['dedicatedParser']==record['dedicatedParser'] and inventory['rowCount']==658
print('Verified all 658 physical subject rows / 618 card identities, 40 literal blank-number signer continuations, cross-page groups, GGBM and 133 Hobby odds cells. Only the exact Let’s Go 1/1 guide join is applied; other limits and release date remain unverified.')
