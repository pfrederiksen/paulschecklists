"""Independently check physical college rosters and literal guides with pypdf."""
import collections,csv,hashlib,json,re
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
proof_path=ROOT/'data/official-panini/college-boxes-pdf-observations-20261021-1700.json';proof=json.loads(proof_path.read_text());registry=json.loads((ROOT/'data/parallel-specifications.json').read_text())
for src in proof['sources']:
 key=src['key'];slug=Path(src['file']).stem;data=json.loads((ROOT/f'data/imports/{slug}.json').read_text());record=next(s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if s['slug']==slug)
 raw=(ROOT/src['file']).read_bytes();assert hashlib.sha256(raw).hexdigest()==src['sha256']==data['sha256']==record['sha256']
 assert hashlib.sha256(proof_path.read_bytes()).hexdigest()==data['sourceObservation']['sha256']
 assert len(raw)==src['bytes']
 rows=[];family=None;heading=None;last=None;guides=[];pending=''
 names=[x['printedHeading'] for x in data['printedHeadings']]
 for pn,page in enumerate(PdfReader(ROOT/src['file']).pages,1):
  # Texas original draw order is independently column sequential; Ohio's draw
  # order puts headings after rows, so its independent positioned layout is used.
  text=page.extract_text() if key=='texas' else page.extract_text(extraction_mode='layout')
  for printed in text.splitlines():
   line=re.sub(r'\s+',' ',pending+printed).strip();pending=''
   if not line:continue
   head=re.sub(r' \(\d+-\d+\)$','',line)
   if head in names:
    heading=head;family=head+(' · page 2' if key=='texas' and head=='SCHOOL COLORS' and pn==2 else '');last=None;continue
   if key=='texas':
    if line=='\uf0a3':pending=line+' ';continue
    if not line.startswith('\uf0a3'):continue
    m=re.fullmatch(r'\uf0a3\s*(\S+)\s+(.+?)(?: (SSP|SP))?',line);assert m,line
    rows.append([family,m[1],m[2],m[3] or '',str(pn),heading]);continue
   if line.startswith('2025 Panini Ohio State NIL - ') or line in ['Parallels:','0']:continue
   if family and line.startswith(family+' '):guides.append((family,line,pn));continue
   m=re.fullmatch(r'(\d+|[A-Z]+(?:-\d+)?|-) (.+?)(?: (SP|SSP))?',line)
   if m:rows.append([family,m[1],m[2],m[3] or '',str(pn),family]);last=m[1];continue
   assert family=='College Ties Dual Autograph' and last,(pn,line)
   rows.append([family,last,line,'',str(pn),family])
 assert not pending
 assert rows==[r[:6] for r in data['rows']],key+' every physical source field must match independent PDF text'
 assert len(rows)==record['rowCount']==src['rows'] and len({r[0] for r in rows})==16
 assert not data.get('odds') and not data.get('formats') and record['releaseDate'] is None
 assert not data.get('rookieColumn') and not any(h.lower()=='team' for h in data['headers'])
 csvproof=data['headerOnlyCsvEvidence'];assert hashlib.sha256((ROOT/csvproof['file']).read_bytes()).hexdigest()==csvproof['sha256']
 assert len(list(csv.reader((ROOT/csvproof['sourceExport']).read_text().splitlines())))==1
 if key=='texas':
  assert len(rows)==219 and collections.Counter(r[3] for r in rows)=={'':183,'SP':18,'SSP':18}
  assert len([r for r in rows if r[0]=='PRIVATE SIGNINGS'])==46
  assert any(r[1:3]==['AH','Anthony Hill Jr.'] for r in rows if r[0]=='PRIVATE SIGNINGS')
  assert len([r for r in rows if r[0]=='NIL AUTOGRAPHS' and r[1]=='JW' and r[2]=='Jonah Williams'])==2
  assert any(r[2]=='Anthon McDermott' for r in rows)
  assert not any(r[0]=='PRIZM' and r[1]=='3' for r in rows)
  assert len([r for r in rows if r[0]=='SCHOOL COLORS · page 2'])==5
  assert all(r[3]=='SSP' for r in rows if r[0]=='SCHOOL COLORS · page 2')
  assert len([r for r in rows if r[0]=='COLLEGE TIES AUTOGRAPHS' and ' / ' in r[2]])==10
  assert not registry['sets'].get(slug) and not record['parallelData']
 else:
  assert len(rows)==243 and len([r for r in rows if r[1]=='-'])==3
  assert not any(r[1]=='49' for r in rows if r[0]=='Legendary Contenders')
  assert not any(r[1]=='TH-8' for r in rows)
  assert collections.Counter(r[1] for r in rows if r[0]=='College Ties Dual Autograph')=={f'OSU-{i}':2 for i in range(1,11)}
  assert len(guides)==119 and collections.Counter(guides)==collections.Counter((x['family'],x['literal'],x['page']) for x in src['guideRows'])
  assert len([x for x in guides if '# to None/' in x[1]])==15
  mapped=registry['sets'][slug];assert len(mapped)==68 and all(re.fullmatch(r'# to \d+',x['numbering']) for x in mapped)
  for entry in mapped:
   scope_path=ROOT/entry['evidenceFile'];assert entry['evidenceSha256']==hashlib.sha256(scope_path.read_bytes()).hexdigest()
   scope=json.loads(scope_path.read_text());assert scope['sourceObservation']==data['sourceObservation'] and len(scope['unresolvedNumbering'])==15
   assert any(g[0]==entry['family'] and re.search(r'\('+re.escape(entry['numbering'])+r'\)',g[1]) for g in guides)
  assert data['sourceNotes'][0]['text']=='0' and record['coverageComplete'] is False
  assert '2024-25' in record['catalogEvidence'] and '2025-26' in record['catalogEvidence']
print('Verified Texas219 rows /36 SP-SSP marks and Ohio243 physical rows /119 literal guides /68 scoped numeric terms against independent PDF text; dash placeholders, None qualifiers, repeated captions/codes and all multi-signers preserved.')
