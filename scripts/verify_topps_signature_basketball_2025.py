"""Independently compare all Signature Class source lines, odds cells and education terms."""
import collections,hashlib,json,re,sys
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-26-topps-signature-class-basketball'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());p=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');compact=lambda s:re.sub(r'\s+','',s)
assert hashlib.sha256(p.read_bytes()).hexdigest()==d['sha256'];assert d['originalSubjectRows']==d['rows']
heads={compact(r[0]) for r in d['rows']}|{'BASE','INSERT','AUTOGRAPH','PACKAGING','SELLSHEET'}
packaging=d['publishedSpecifications'][3]['rows']
for pn,page in enumerate(PdfReader(p).pages,1):
 actual=[compact(line) for line in page.extract_text().splitlines() if compact(line) and compact(line) not in heads and not line.startswith(('Checklists provided','product at the time'))]
 expected=[compact(r[1]+r[2]+r[4]+r[5]) for r in d['rows'] if r[3]==str(pn)]+[compact(r[0]+r[1]) for r in packaging if r[2]==str(pn)]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b])
assert len(d['rows'])==1097 and len({tuple(r[:2]) for r in d['rows']})==1062 and len({r[0] for r in d['rows']})==31
assert sum(r[5]=='Rookie' for r in d['rows'])==439
for family,start,end,missing in [('BASE CARDS I',1,100,{68}),('BASE CARDS II',101,150,{150}),('BASE CARDS I CHROME VARIATION',1,100,set()),('BASE CARDS II CHROME VARIATION',101,150,set())]:
 assert {int(r[1]) for r in d['rows'] if r[0]==family}==set(range(start,end+1))-missing
assert len([r for r in d['rows'] if r[0]=='ARISTOCRATS'])==20
assert [(r[2],r[4]) for r in d['rows'] if r[1]=='DA-AN']==[('Nique Clifford','Sacramento Kings'),('Asa Newell','Atlanta Hawks')]
assert [(r[2],r[4]) for r in d['rows'] if r[1]=='TA-CSJ']==[('Chet Holmgren','Oklahoma City Thunder'),('Shai Gilgeous-Alexander','Oklahoma City Thunder'),('Jalen Williams','Oklahoma City Thunder')]
assert d['rows'][-1][1:]==['TA-SZA','Stephon Castle','23','San Antonio Spurs','']
op=p.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
for pn,page in enumerate(PdfReader(op).pages,1):
 lines=[compact(line) for line in page.extract_text().splitlines() if compact(line)]
 if pn==1:lines=lines[5:]
 expected=[compact(o['name']+''.join(v or '' for v in o['values'].values())) for o in d['officialOddsTable'] if o['page']==pn]
 assert lines==expected,(pn,[(a,b) for a,b in zip(lines,expected) if a!=b])
assert len(d['odds'])==199 and d['formats']==['Odds Hobby:','Odds Hobby Jumbo:','Odds Value Box:','Odds Mega Box:']
assert d['oddsUnitsPublished'] is False and d['formatNamesPublished'] is True
assert next(o for o in d['odds'] if o['name']=='Rookie Class Base')['values']['Odds Hobby Jumbo:']=='2.1'
assert [(o['name'],o['page'],o['values']) for o in d['odds']]==[(o['name'],o['page'],o['values']) for o in d['officialOddsTable']]
proof=json.loads((ROOT/'data/parallel-audit-sources/signature-class-basketball-2025-26-20261016.json').read_text());ep=ROOT/proof['educationFile'];assert hashlib.sha256(ep.read_bytes()).hexdigest()==proof['educationSha256']
edu=PdfReader(ep).pages[1].extract_text();section=edu.split('CRYSTAL CLEAR AUTOGRAPHS\n')[1];crystal,base=section.split('BASE PARALLELS CHROME PARALLELS\n');paper,chrome=base.split('FoilFractor /1\n');paper+='FoilFractor /1';chrome=chrome.split('Roses – Red Parallel')[0]
for key,part in [('paper',paper),('chrome',chrome),('crystal',crystal)]:
 expected='\n'.join(name+' '+('/'+n if n=="Non-#'d" else n) for name,n in proof['educationParallelTables'][key]);assert compact(part)==compact(expected),(key,part,expected)
reg=json.loads((ROOT/'data/parallel-specifications.json').read_text())['sets'][SLUG];assert len(reg)==79
for family,cap,number in [('BASE CARDS I','Veteran Class Base Yellow','/399'),('BASE CARDS I CHROME VARIATION','Veteran Class Chrome Base Yellow','/275'),('VETERAN CLASS CRYSTAL CLEAR AUTOGRAPHS','Veteran Class Crystal Clear Autographs Monarch','/5')]:
 assert next(s for s in reg if s['oddsName']==cap)['numbering']==number
assert not any('BASE VETERAN CLASS CHROME AUTOGRAPHS'==s['family'] or s['family']=='ROSES' for s in reg)
for spec in reg+d['publishedSpecifications']:assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
r=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG);assert r['releaseDate'] is None and r['dedicatedParser']=='scripts/import_topps_signature_basketball_2025.py'
sys.path.insert(0,str(ROOT/'scripts'));from verify_official_imports import verify
assert verify(r)[0]==199
print('Verified all 1,097 physical subject rows / 1,062 identities, 439 Rookie marks, 199 four-column odds including 2.1, 79 exact education joins, packaging subjects and explicit source discrepancies.')
