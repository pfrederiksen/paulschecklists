"""Independently compare every Winter Olympics row and literal odds column."""
import collections,hashlib,json,re
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-chrome-u-s-winter-olympics-paralympic-team-hopefuls'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');compact=lambda s:re.sub(r'\s+','',s)
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
heads={compact(r[0]) for r in d['rows']}|{'BASE','INSERT','AUTOGRAPH','RELIC','AUTOGRAPHRELIC'}
for pn,page in enumerate(PdfReader(path).pages,1):
 actual=[compact(line) for line in page.extract_text().splitlines() if compact(line) and compact(line) not in heads]
 expected=[compact(r[1]+r[2]) for r in d['rows'] if r[3]==str(pn)];assert actual==expected,(pn,actual,expected)
assert len(d['rows'])==707 and len({r[0] for r in d['rows']})==18 and len({tuple(r[:2]) for r in d['rows']})==701
assert d['rows']==d['originalSubjectRows'] and not {'Team','Rookie'}&set(d['headers'])
assert {int(r[1]) for r in d['rows'] if r[0].startswith('BASE CARDS ') and r[1].isdigit()}==set(range(1,201))
assert not any(r[1]=='1986' for r in d['rows'])
assert len([r for r in d['rows'] if r[0]=='1986 TOPPS'])==40 and len([r for r in d['rows'] if r[0]=='1986 TOPPS AUTOGRAPH VARIATION'])==10
duals=[r for r in d['rows'] if r[0]=='DUAL AUTOGRAPHS'];assert len(duals)==12 and set(collections.Counter(r[1] for r in duals).values())=={2}
assert [r[2] for r in duals if r[1]=='DA-LG']==['Alysa Liu','Amber Glenn']
assert next(r for r in d['rows'] if r[1]=='37')[2]=='Jack Hughes' and next(r for r in d['rows'] if r[1]=='137')[2]=='Aaron Pike'
assert d['rows'][-1][1:]==['USJ-TL','Ted Ligety','15']
assert d['formats']==['Hobby-146','Value Box SE-148','Value Box EA-147'] and d['oddsUnitsPublished'] is False
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
for pn,page in enumerate(PdfReader(op).pages,1):
 actual=[compact(line) for line in page.extract_text().splitlines()[2:] if compact(line)]
 expected=[compact(o['name']+''.join(o['values'][f] or '-' for f in d['formats'])) for o in d['odds'] if o['page']==pn]
 assert actual==expected,(pn,actual,expected)
assert len(d['odds'])==85 and not d['oddsIssues'] and len(d['parallelSpecifications'])==1
assert [(o['name'],o['values'],o['page']) for o in d['odds']]==[(o['name'],o['values'],o['page']) for o in d['officialOddsTable']]
assert next(o for o in d['odds'] if o['name']=='Base Green Refractor Parallel')['values']['Hobby-146']=='01:23:00'
assert all(o['familyAliases']==['BASE CARDS II'] for o in d['odds'] if o['family']=='BASE CARDS I')
assert all('numbering' not in o for o in d['odds'])
spec=d['parallelSpecifications'][0];assert spec['name']=='Pink Refractors' and spec['numbering']=='/250' and 'unjoined' in spec['qualification'];assert 'oddsName' not in spec and spec['family'] not in {r[0] for r in d['rows']}
for spec in d['publishedSpecifications']:assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
r=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG);assert r['releaseDate'] is None and r['year']=='2026'
print('Verified 707 original subjects / 701 identities, all 18 caption families, six paired dual codes, 200 base numbers and every cell across 85 three-column odds rows. Pink /250 remains unjoined; no teams, rookie flags or release date are inferred.')
