"""Compare every Finest PL subject and odds literal with independent PDF text."""
import collections,hashlib,json,re,unicodedata
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-topps-finest-premier-league-2026'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
norm=lambda s:re.sub(r'\s+','',unicodedata.normalize('NFKC',s))
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256'] and d['dedicatedParser']=='scripts/import_topps_finest_pl_2026.py'
heads={norm(r[0]) for r in d['rows']}|{'BASE','INSERT','AUTOGRAPH'}
for pn,page in enumerate(PdfReader(path).pages,1):
 actual=[]
 for line in page.extract_text().splitlines():
  v=norm(line)
  if not v or v in heads or v.startswith(('Checklistsprovided','productatthetime')):continue
  actual.append(v)
 expected=[norm(r[7]+r[2]+r[4]+r[6]) for r in d['rows'] if r[3]==str(pn)]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b][:4],len(actual),len(expected))
assert len(d['rows'])==767 and len({tuple(r[:2]) for r in d['rows']})==752
assert d['originalSubjectRows']==[[r[0],r[7],r[2],r[3],r[4],r[6]] for r in d['rows']]
count=collections.Counter(r[0] for r in d['rows']);assert len(count)==23
for family,first in [('BASE COMMON',1),('BASE UNCOMMON',101),('BASE RARE',201)]:
 assert count[family]==100 and {int(r[1]) for r in d['rows'] if r[0]==family}==set(range(first,first+100))
assert count['(xB) EXPECTED BRILLIANCE']==40 and {r[1] for r in d['rows'] if r[0]=='(xB) EXPECTED BRILLIANCE'}=={'XB-'+str(n) for n in range(1,41)}
assert count['FINEST PARTNERSHIPS']==30 and len(d['sourceContinuationRows'])==15 and sum(not r[7] for r in d['rows'])==15
assert set(collections.Counter(r[1] for r in d['rows'] if r[0]=='FINEST PARTNERSHIPS').values())=={2}
for cont in d['sourceContinuationRows']:
 i=cont['row'];assert d['rows'][i][1]==d['rows'][i-1][1]==cont['cardNumber'] and not d['rows'][i][7]
assert [r[2] for r in d['rows'] if r[1]=='FP-SM']==['Sadio Mané','Mohamed Salah']
assert [r[2] for r in d['rows'] if r[1]=='FP-MS']==['Gabriel Magalhães','William Saliba']
assert [r[2] for r in d['rows'] if r[1]=='FP-SS']==['Luis Suárez','Daniel Sturridge']
assert sum(r[5]=='Rookie' for r in d['rows'])==156 and sum(r[6]=='On-Card' for r in d['rows'])==1
assert next(r for r in d['rows'] if r[1]=='FF-LBJ')[4:8]==['Liverpool FC','','On-Card','FF-LBJ']
assert next(r for r in d['rows'] if r[1]=='FF-CT')[4]=='' and sum(not r[4] for r in d['rows'])==1
assert next(r for r in d['rows'] if r[1]=='FF-SLJ')[2]=='Samuel L. Jackson'
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
source=[]
for pn,page in enumerate(PdfReader(op).pages,1):
 lines=page.extract_text().splitlines()
 if pn==1:assert any(norm(v)=='CardPLFINEST2026' for v in lines)
 if pn>=4:assert not page.extract_text().strip()
 for line in lines:
  m=re.fullmatch(r'\s*(.+?)\s*([\d,.]+:[\d,.]+)\s*',line)
  if m:source.append((pn,norm(m[1]),m[2]))
assert source==[(o['page'],norm(o['name']),o['values']['PL FINEST 2026']) for o in d['officialOddsTable']]
assert len(source)==115 and source==[(o['page'],norm(o['name']),o['values'][d['formats'][0]]) for o in d['odds']]
assert d['formats']==['Published odds (format not named)'] and d['formatNamesPublished'] is False and d['oddsUnitsPublished'] is False and d['formatHeaderIsProductTitle']
assert d['officialOddsHeader']==['Card','PL FINEST 2026']
assert len(d['unjoinedOddsCategories'])==13
by={o['name']:o for o in d['odds']}
assert by['COMMON BASE CARD BLUE REFRACTOR']['family']=='BASE COMMON'
assert by['UNCOMMON BASE CARD BLUE REFRACTOR']['family']=='BASE UNCOMMON'
assert by['RARE BASE CARD BLUE REFRACTOR']['family']=='BASE RARE'
assert by['COMMON INSERTS (FIVE THEMES) BASE']['values'][d['formats'][0]]=='2:1'
assert all(o['family']=='COMMON INSERTS (FIVE THEMES)' for o in d['odds'] if o['name'].startswith('COMMON INSERTS'))
assert all(o['family']=='FINEST SEASONS - 1996/97' for o in d['odds'] if o['name'].startswith('FINEST SEASONS'))
assert not any(o['family']=='FINEST SEASONS 1995 96' for o in d['odds'])
assert by['FINEST PARTNERSHIPS - DUAL AUTOGRAPHS SUPERFRACTOR']['family']=='FINEST PARTNERSHIPS'
assert not d['parallelSpecifications'] and not any(o.get('numbering') for o in d['odds'])
assert sum(bool(r[8]) for r in d['rows'])==3 and '1/1' in next(r for r in d['rows'] if r[1]=='FP-SM')[8]
assert 'limited to five copies; serial numbering is not stated' in next(r for r in d['rows'] if r[1]=='FS-IW')[8]
for spec in d['publishedSpecifications']:assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
record=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG)
assert record['rowCount']==767 and record['releaseDate'] is None
print('Verified all 767 Finest PL source subjects / 752 identities, 15 signer continuations, all 300 tiered base numbers, 40 Expected Brilliance entries, 156 Rookie flags plus separate On-Card, and all 115 literal odds. Product title is not a format; five-theme / Seasons-year joins and general numbering remain unresolved.')
