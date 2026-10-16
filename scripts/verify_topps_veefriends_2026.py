"""Independently compare every VeeFriends source row and all eight odds cells."""
import collections,hashlib,json,logging,re,unicodedata
from pathlib import Path
from pypdf import PdfReader
import pdfplumber
logging.getLogger('pypdf').setLevel(logging.ERROR)
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-chrome-veefriends'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
norm=lambda s:re.sub(r'\s+','',unicodedata.normalize('NFKC',s))
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_veefriends_2026.py' and d['rows']==d['originalSubjectRows']
headings={norm(r[0]) for r in d['rows']}|{'BASE','INSERT','RELIC','AUTOGRAPH','SKETCH'}
for pn,page in enumerate(PdfReader(path).pages,1):
 actual=[]
 for line in page.extract_text(extraction_mode='layout').splitlines():
  value=norm(line)
  if not value or value in headings or value.startswith(('Checklistsprovided','timeofproduction')):continue
  actual.append(value)
 expected=[norm(r[1]+r[2]) for r in d['rows'] if r[3]==str(pn)]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b][:4])
assert len(d['rows'])==823 and sum(bool(r[1]) for r in d['rows'])==711
count=collections.Counter(r[0] for r in d['rows']);assert len(count)==22
assert count['SKETCH CARDS']==111 and count['BLANK CANVAS SKETCH CARDS']==1
for f in ['BASE CARDS','BASE CARDS GARY VEE AUTOGRAPH PARALLEL']:assert {int(r[1]) for r in d['rows'] if r[0]==f}==set(range(1,201))
assert {r[1] for r in d['rows'] if r[0]=='MANGA SPECKLE SET'}=={'SSA-'+str(n) for n in range(1,101)}
assert next(r for r in d['rows'] if r[1]=='SSA-100')[2]=='Zealous Zombie'
assert count['CONTENT CONDORS']==6 and count['CONTENT CONDORS AUTOGRAPHS']==8
assert {r[1] for r in d['rows'] if r[0]=='CONTENT CONDORS AUTOGRAPHS'}=={'CCA-GV','CCA-JP','CCA-KP','CCA-LD','CCA-MR','CC-CB','CC-CL','CC-MG'}
assert not any('MrBeast' in r[2] for r in d['rows'] if r[0]=='CONTENT CONDORS AUTOGRAPHS')
assert next(r for r in d['rows'] if r[1]=='BB-7')[2]=='Macro Micro'
assert next(r for r in d['rows'] if r[0]=='BLANK CANVAS SKETCH CARDS')[4]=='Gary Vee'
assert any(r[4]=='COHEN' and not r[1] for r in d['rows']) and any(r[4]=='Señor Pants & Aria Heath' for r in d['rows']) and d['rows'][-1][4]=='Zachary Maers'
assert 'Team' not in d['headers'] and 'Rookie' not in d['headers']
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
expected=[];formats=d['formats'];token=re.compile(r'(?<!\S)(?:1:[\d,]+|-)(?!\S)')
with pdfplumber.open(op) as pdf:
 for pn,page in enumerate(pdf.pages,1):
  tables=page.find_tables();assert len(tables)==1;header=False
  for row in tables[0].extract():
   assert len(row)==1;full=' '.join((row[0] or '').split())
   if full=='Cards '+' '.join(formats):header=True;continue
   if not header:assert pn==1 and full.startswith('Checklists and odds');continue
   values=token.findall(full);assert len(values)==8,(pn,full,values)
   name=' '.join(token.sub('',full).split());expected.append((pn,norm(name),[None if v=='-' else v for v in values]))
assert expected==[(o['page'],norm(o['name']),list(o['values'].values())) for o in d['odds']]
assert len(expected)==104 and formats==['Hobby','Sapphire','Value Box SE','Value Box EA','Value Box CEE','Mega Box SE','Mega Box EA','Mega Box CEE']
assert d['formatNamesPublished'] is True and d['oddsUnitsPublished'] is False
assert all(o['family'] in count for o in d['odds']) and len(d['oddsSourceNotes'])==1
by={o['name']:o for o in d['odds']}
assert by['Content Condor On-Card Autograph']['family']=='CONTENT CONDORS AUTOGRAPHS' and by['Content Condor On-Card Autograph']['values']['Hobby']=='1:1,280'
assert by['Base Set Gary Vee Autograph Parallel']['family']=='BASE CARDS GARY VEE AUTOGRAPH PARALLEL'
assert by['VeeFriends Variants Last Glass Standing Rosé Variant']['family']=='VEEFRIENDS VARIANTS - LAST GLASS STANDING'
assert by['Sketch Cards']['family']=='SKETCH CARDS'
specs=d['parallelSpecifications'];assert len(specs)==34 and sum('oddsName' in s for s in specs)==33
assert next(s for s in specs if s.get('oddsName')=='Base Set Black Cat Refractor')['numbering']=='/7'
assert next(s for s in specs if s.get('oddsName')=='Base Set Gary Vee Autograph Parallel')['numbering']=='/5'
assert next(s for s in specs if s.get('oddsName')=='Manga Speckle Set Black Speckle Refractor')['numbering']=='1/1'
assert next(s for s in specs if s.get('oddsName')=='Topps 1986 Variation')['numbering']=='Limited to 86 per character; serial numbering not stated'
assert next(s for s in specs if 'oddsName' not in s)['numbering']=='Not published'
assert not any(s['family'] in {'HIDDEN GEMS','INFINITE SAPPHIRE','SKETCH CARDS','BLANK CANVAS SKETCH CARDS','CONTENT CONDORS','CONTENT CONDORS AUTOGRAPHS','ICONICS'} for s in specs)
for s in specs:
 assert hashlib.sha256((ROOT/s['evidenceFile']).read_bytes()).hexdigest()==s['evidenceSha256']
 if s.get('oddsName'):assert by[s['oddsName']]['family']==s['family']
registry=json.loads((ROOT/'data/parallel-specifications.json').read_text());assert registry['sets'][SLUG]==specs
record=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG)
inventory=next(r for r in json.loads((ROOT/'data/topps-product-official-catalog.json').read_text()) if r['slug']==SLUG)
assert record['releaseDate']==inventory['releaseDate']=='2026-06-10' and 'Sapphire is explicitly a later launch' in record['verifiedRelease']['scope']
print('Verified 711 numbered entries, 112 artist entries and every original line across 22 sections; all 104 physical odds rows/eight columns, 33 exact guide joins and one unnumbered Green specification. Print limits, guide discrepancies and pack/box/case units remain distinct.')
