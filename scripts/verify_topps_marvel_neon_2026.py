"""Independently compare complete original PDF text and physical odds columns."""
import collections,copy,hashlib,json,re,sys
from pathlib import Path
from pypdf import PdfReader
import pdfplumber
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-neon-marvel'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());cp=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');op=cp.with_name(SLUG+'-odds.pdf');compact=lambda s:re.sub(r'\s+','',s)
assert hashlib.sha256(cp.read_bytes()).hexdigest()==d['sha256'] and hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
heads={r[0] for r in d['rows']}|{'BASE VARIATIONS','INSERT','CASE HITS','LENTICULAR','AUTOGRAPH','BOX TOPPERS'}
for pn,page in enumerate(PdfReader(cp).pages,1):
 actual=[compact(l) for l in page.extract_text().splitlines() if l.strip() and l.strip() not in heads and not l.startswith(('Checklists provided','product at the time','vary.'))]
 expected=[compact(r[1]+r[2]+r[3]) for r in d['rows'] if r[4]==str(pn)]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b])
assert len(d['rows'])==866 and sum(bool(r[1]) for r in d['rows'])==730 and len({tuple(r[:2]) for r in d['rows'] if r[1]})==710
assert sum(r[0]=='SKETCH CARD ARTISTS' for r in d['rows'])==136 and sum(bool(r[3]) for r in d['rows'])==49
for family in ['BASE','CHROME NEON ETCH BASE VARIATION']:assert [int(r[1]) for r in d['rows'] if r[0]==family]==list(range(1,201))
assert [r[2] for r in d['rows'] if r[:2]==['1 UP','1UP-1']]==['Venom','Carnage']
assert [r[2] for r in d['rows'] if r[:2]==['MARQUEE MOTION','MM-9']]==['Wolverine','Spider-Man','Venom']
assert next(r for r in d['rows'] if r[:2]==['FRIENDLY NEIGHBORHOOD SPIDER MAN VOICE ACTOR AUTOS','SVA-EE'])[2:4]==['Ettore "Big E" Ewen','Bulldozer']
assert d['rows'][-1][1:]==['SXL-16','Magneto','','17']
# Independently compare original text flow from a second PDF engine.
# The single stacked-cell dash precedes its label in that engine's draw order;
# its complete token multiset is retained, with no selected value.
for pn,page in enumerate(PdfReader(op).pages,1):
 lines=page.extract_text().splitlines();assert compact(lines[2])==compact(''.join(d['officialOddsHeader']))
 physical=lines[3:];expected=[o for o in d['odds'] if o['page']==pn];assert len(physical)==len(expected)
 for line,o in zip(physical,expected):
  joined=o['name']+' '+' '.join(o['values'][f] or '-' for f in d['formats'])
  if o['name']=='MARVEL SNAP XL GOLD FOIL':
   assert line.startswith('-'+o['name']) and collections.Counter(line[1:].split()+['-'])==collections.Counter(joined.split())
  else:assert compact(line)==compact(joined),(pn,line,joined)
assert len(d['odds'])==133 and sum(v=='1:XX' for o in d['odds'] for v in o['values'].values())==3
assert next(o for o in d['odds'] if o['name']=='MARVEL SNAP XL GOLD FOIL')['values']['SUPER BOX']=='-\n1:832'
assert d['oddsUnitsPublished'] is False and d['formats']==['HOBBY','VALUE BOX','MEGA BOX','SUPER BOX BONUS PACK','SUPER BOX']
assert len(d['parallelSpecifications'])==1 and d['parallelSpecifications'][0]['family']=='BASE' and d['parallelSpecifications'][0]['numbering']=='1/1'
assert not any(h in d['headers'] for h in ['Team','Rookie'])
for t in d['publishedSpecifications']:assert hashlib.sha256((ROOT/t['evidenceFile']).read_bytes()).hexdigest()==t['evidenceSha256']
r=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG);assert r['releaseDate'] is None
sys.path.insert(0,str(ROOT/'scripts'));from import_official_catalog import run
assert run(copy.deepcopy(r))==r
print('Verified 730 numbered rows / 710 identities, 136 artists, 49 original additional-text fields, all 133 x 5 physical odds cells, three 1:XX placeholders and the stacked dash/1:832; no inferred units or broader numbering.')
