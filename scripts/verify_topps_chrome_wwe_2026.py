"""Independently compare every Chrome WWE physical row and all eleven odds cells."""
import collections,hashlib,json,re,unicodedata
from pathlib import Path
from pypdf import PdfReader
import pdfplumber
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-chrome-wwe'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
norm=lambda s:re.sub(r'\s+','',unicodedata.normalize('NFKC',s))
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_chrome_wwe_2026.py' and d['rows']==d['originalSubjectRows']
heads={norm(r[0]) for r in d['rows']}|{'BASE','INSERT','AUTOGRAPH','AUTOGRAPHRELIC'}
for pn,page in enumerate(PdfReader(path).pages,1):
 actual=[]
 # Plain extraction preserves drawing order where long names overlap the
 # designation column. Spatial layout extraction interleaves those glyphs.
 for line in page.extract_text().splitlines():
  value=norm(line)
  if not value or value in heads or value.startswith('Checklistsprovided'):continue
  actual.append(value)
 expected=[norm(r[1]+r[2]+r[4]+r[5]) for r in d['rows'] if r[3]==str(pn)]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b][:4],len(actual),len(expected))
assert len(d['rows'])==1137 and len({tuple(r[:2]) for r in d['rows']})==1110
count=collections.Counter(r[0] for r in d['rows']);assert len(count)==53
assert {int(r[1]) for r in d['rows'] if r[0] in {'BASE CARDS I','BASE CARDS II'}}==set(range(1,201))
assert [r[1] for r in d['rows'] if r[0]=='BASE CARDS III']==['301']
assert {r[1] for r in d['rows'] if r[0]=='AUSTIN 3 16 (HOBBY, FDI)'}=={'3:16-'+str(n) for n in range(1,26)}
assert count['ICONIC IMPRINTS AUTOGRAPH VARIATION (Hobby/Breaker/FDI)']==61 and count['FUTURE STARS AUTOGRAPHS']==9
assert count['1986 TOPPS AUTOGRAPH VARIATION']==30 and count['BASE CARDS I AUTOGRAPH VARIATION (FDI EXCLUSIVE)']==3
assert not any(r[1] in {'1986','2025'} for r in d['rows'])
assert count['TRISH STRATUS 25TH ANNIVERSARY AUTOGRAPHS (HOBBY, BREAKER, FDI)']==2
assert [(r[1],r[2],r[4]) for r in d['rows'] if r[0]=='2025 TOPPS CHROME WWE BUYBACK AUTOGRAPHS']==[('106','Jey Uso',''),('182','Tiffany Stratton','')]
assert next(r for r in d['rows'] if r[:2]==['BASE CARDS I','21'])[2:]==['"The American Nightmare" Cody Rhodes','1','Smackdown','']
assert next(r for r in d['rows'] if r[1]=='FTP-CR')[4]=='SmackDown'
assert sum(r[5]=='Rookie' for r in d['rows'])==13 and 'Team' not in d['headers']
assert sum(r[0]=='FAMILY TREE (HOBBY, FDI)' for r in d['rows'])==30
assert set(collections.Counter(r[1] for r in d['rows'] if r[0]=='FAMILY TREE (HOBBY, FDI)').values())=={2}
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
expected=[];token=re.compile(r'(?<!\S)(?:[\d,.]+(?::[\d,.]+)+|-)(?!\S)')
with pdfplumber.open(op) as pdf:
 for pn,page in enumerate(pdf.pages,1):
  tables=page.find_tables();assert len(tables)==1
  for row in tables[0].extract()[1:]:
   full=' '.join(' '.join((v or '').split()) for v in row)
   if pn==13 and full.startswith('CHROME 2026'):
    assert 'FIRST DAY ISSUE' in full and not re.search(r'\d+:\d+',full);continue
   matches=list(token.finditer(full));assert len(matches)>=11,(pn,full)
   selected=matches[-11:];values=[m[0] for m in selected];name=full
   for m in reversed(selected):name=name[:m.start()]+name[m.end():]
   expected.append((pn,norm(name),[None if v=='-' else v for v in values]))
assert expected==[(o['page'],norm(o['name']),list(o['values'].values())) for o in d['odds']]
assert len(expected)==410 and len(d['formats'])==11 and d['formatNamesPublished'] and not d['oddsUnitsPublished']
by={o['name']:o for o in d['odds']}
assert by['AUSTIN 3:16']['family']=='AUSTIN 3 16 (HOBBY, FDI)'
assert by['BASE BLUE REFRACTOR']['familyAliases']==['BASE CARDS II']
assert by['BASE AUTOGRAPH VARIATIONS FIRST DAY ISSUE']['family']=='BASE CARDS I AUTOGRAPH VARIATION (FDI EXCLUSIVE)'
assert by['1986 TOPPS VARIATION AUTOGRAPHS']['family']=='1986 TOPPS AUTOGRAPH VARIATION'
specs=d['parallelSpecifications'];assert len(specs)==33 and len({s['family'] for s in specs})==6
for s in specs:
 assert hashlib.sha256((ROOT/s['evidenceFile']).read_bytes()).hexdigest()==s['evidenceSha256']
 assert by[s['oddsName']]['family']==s['family']
assert next(s for s in specs if s['oddsName']=='BASE MAGENTA REFRACTOR')['numbering']=='/399'
assert next(s for s in specs if s['oddsName']=='AUSTIN 3:16 GOLD REFRACTOR')['numbering']=='/50'
assert next(s for s in specs if s['oddsName']=='GPK BLACK REFRACTOR')['numbering']=='/10'
assert not any(any(t in s['oddsName'] for t in ['SAPPHIRE','FROZEN','GEOMETRIC','AUTOGRAPH VARIATIONS']) for s in specs)
assert 'SAPPHIRE SELECTIONS' in d['unjoinedOddsCategories'] and 'HIDDEN GEMS' in d['unjoinedOddsCategories']
registry=json.loads((ROOT/'data/parallel-specifications.json').read_text());assert registry['sets'][SLUG]==specs
assert any('exalted-wwe' in c['slug'] for c in registry['conflicts'])
record=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG)
assert record['releaseDate']=='2026-04-10' and record['rowCount']==1137
print('Verified all 1,137 physical WWE rows, 1,110 identities / 53 families, 25 Austin codes, corrected autograph headings, 13 Rookie marks, source designation spellings, all 410 odds / 11 columns and 33 exact family limits. FrozenFractor scope and other numbering gaps remain explicit.')
