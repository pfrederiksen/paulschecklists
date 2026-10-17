"""Independently verify every Universe name/designation/flag with pypdf text flow."""
import collections, hashlib, json, re
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-topps-universe-wwe'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());p=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
assert hashlib.sha256(p.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_universe_wwe_2025.py'
assert d['headers']==['Checklist section','Card number','Name','Source page','Published designation (source column 3)','Rookie']
families={r[0] for r in d['rows']};family=None;actual=[]
for pn,page in enumerate(PdfReader(p).pages,1):
 for line in page.extract_text().splitlines():
  line=line.strip()
  if not line or line in {'BASE','INSERT','AUTOGRAPH','AUTOGRAPH RELIC','RELIC'}:continue
  if line in families:family=line;continue
  m=re.fullmatch(r'(\S+)\s+(.+?)(Raw|Smackdown|NXT|Legends|Legend|WWE)(?:\s+(Rookie))?',line)
  assert m,(pn,line)
  number,name,designation,rookie=m.groups()
  actual.append([family,number,name.strip(),str(pn),designation,rookie or ''])
compact=lambda s:re.sub(r'\s+','',s)
assert [[compact(c) for c in r] for r in actual]==[[compact(c) for c in r] for r in d['rows']],'Every original printed cell must reconcile independently'
assert len(actual)==846 and len(families)==32 and len({tuple(r[:2]) for r in actual})==820
assert d['rows']==d['originalSubjectRows'] and d['headers']==d['originalSubjectHeaders']
for f,a,b in [('BASE CARDS I',1,101),('BASE CARDS II',101,201),('BASE CARDS EVENT VARIATION',201,301)]:
 assert {r[1] for r in d['rows'] if r[0]==f}=={str(n) for n in range(a,b)}
assert [(r[1],r[2]) for r in d['rows'] if r[5]=='Rookie']==[('109','Zaria'),('118','Jordynne Grace')]
assert next(r for r in d['rows'] if r[:2]==['BASE CARDS I','72'])[2]=='"The American Nightmare" Cody Rhodes'
assert next(r for r in d['rows'] if r[:2]==['BASE CARDS II','143'])[2]=='Channing "Stacks" Lorenzo'
assert next(r for r in d['rows'] if r[:2]==['BASE CARDS II','174'])[2]=='"Million Dollar Man" Ted DiBiase'
duals=[r for r in d['rows'] if r[0]=='TAG TEAM RELIC AUTOGRAPHS']
assert len(duals)==32 and set(collections.Counter(r[1] for r in duals).values())=={2}
assert [(r[2],r[3],r[4]) for r in duals if r[1]=='TTA-ANF']==[('Nathan Frazer','15','NXT'),('Axiom','16','NXT')]
assert d['rows'][-1]==['RINGSIDE RELICS','RSR-UND','Undertaker','18','Legend','']
assert not any(h.lower()=='team' for h in d['headers']) and not d['odds'] and not d['formats']
assert not d['parallelSpecifications'] and not d['oddsUnitsPublished'] and not d['formatNamesPublished']
proof_path=ROOT/'data/parallel-audit-sources/universe-wwe-2025-physical-20261017.json'
proof=json.loads(proof_path.read_text());digest=hashlib.sha256(proof_path.read_bytes()).hexdigest()
assert all(s['evidenceSha256']==digest and ROOT/s['evidenceFile']==proof_path for s in d['publishedSpecifications'])
assert all(not any('numbering' in h.lower() for h in s['headers']) for s in d['publishedSpecifications'])
assert proof['parallelContext'][1][0]=='Galaxy' and 'Value' in proof['parallelContext'][1][1]
assert len(proof['remainingGaps'])==3
record=next(s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert record['releaseDate']=='2026-02-27' and record['year']=='2025'
registry=json.loads((ROOT/'data/parallel-specifications.json').read_text())
assert not registry['sets'].get(SLUG)
assert any(c['slug']==SLUG and '2026 odds source is a different product' in c['gap'] for c in registry['conflicts'])
print('Verified all 846 original physical subjects / 820 identities / 32 sections, three 100-number base programs, two literal Rookie marks and all 16 duals, including the page-break pair. Published box/case terms do not create odds, teams or serial limits.')
