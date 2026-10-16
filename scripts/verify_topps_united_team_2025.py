"""Independently verify the original Manchester United PDF and guide scoping."""
import collections,hashlib,json,re
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-topps-manchester-united-2025-26-team-set'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
compact=lambda s:re.sub(r'\s+','',s)
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
heads={compact(r[0]) for r in d['rows']}
for pn,page in enumerate(PdfReader(path).pages,1):
 actual=[compact(line) for line in page.extract_text().splitlines() if compact(line) and compact(line) not in heads]
 expected=[compact(r[1]+r[2]+r[4]+r[5]) for r in d['rows'] if r[3]==str(pn)]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b])
assert len(d['rows'])==119 and len({r[0] for r in d['rows']})==8
assert len({tuple(r[:2]) for r in d['rows']})==119
assert d['originalSubjectRows']==[r[:6] for r in d['rows']]
assert {int(r[1]) for r in d['rows'] if r[1].isdigit()}==set(range(1,51))
assert len([r for r in d['rows'] if r[0]=='RAINBOW FLICK'])==25
assert {r[1] for r in d['rows'] if r[5]=='Rookie'}=={'9','11','14','16','29','RF-1','RF-5','AU-AI','AU-SK'}
assert {r[1] for r in d['rows'] if r[4]=='Manchester United Women'}=={'27','34','35','AU-ET','AU-FR','AU-LT'}
assert next(r for r in d['rows'] if r[1]=='AU-PS')[2]=='Peter Schmeichel'
assert next(r for r in d['rows'] if r[1]=='AU-SC')[2]=='Paul Scholes'
assert next(r for r in d['rows'] if r[1]=='RF-8')[2]=='Bastian Schweinsteiger'
assert sum(bool(r[6]) for r in d['rows'])==1
assert '1/1' in next(r for r in d['rows'] if r[1]=='AU-AF')[6]
assert not next(r for r in d['rows'] if r[1]=='AU-AI')[6]
assert not d['odds'] and not d['formats'] and not d['parallelSpecifications']
assert d['formatNamesPublished'] is False and d['oddsUnitsPublished'] is False
for spec in d['publishedSpecifications']:assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
config=d['publishedSpecifications'][0]['rows'];assert ['Autograph distribution','1 in every 2 boxes','Published box unit; no per-pack conversion'] in config
r=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG)
assert r['releaseDate'] is None and r['regionalReleaseEvidence']['date']=='2026-02-12' and r['regionalReleaseEvidence']['market']=='United Kingdom'
assert r['year']=='2025/26' and r['dedicatedParser']=='scripts/import_topps_united_team_2025.py'
print('Verified every Manchester United source row and original column: 119 unique entries, eight sections, nine Rookie marks, six women’s-team rows, one card-specific 1/1 example; regional date and box/case units remain separate from general release and pack odds.')
