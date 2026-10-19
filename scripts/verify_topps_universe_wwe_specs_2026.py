"""Check original workbook cells, physical odds and exact Universe guide scope."""
import hashlib,json,re
from pathlib import Path
import xlrd
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-universe-wwe'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());proof=ROOT/'data/parallel-audit-sources/universe-wwe-2026-guide-20261019.json';p=json.loads(proof.read_text());facts=p['normalizedFacts']
assert hashlib.sha256(json.dumps(facts,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==p['normalizedFactsSha256']
xp=ROOT/'data/catalog-sources/downloads'/(SLUG+'.xls');assert hashlib.sha256(xp.read_bytes()).hexdigest()==d['sha256']==p['checklistSha256']
s=xlrd.open_workbook(file_contents=xp.read_bytes()).sheet_by_index(0)
assert d['rawWorksheet']==[s.row_values(i) for i in range(s.nrows)]
assert len(d['rows'])==len([i for i in range(s.nrows) if s.cell_value(i,1)])==922
for r in d['rows']:
 values=s.row_values(int(r[6])-1);number=str(int(values[0])) if isinstance(values[0],float) and values[0].is_integer() else str(values[0])
 assert r[1:5]==[number,*values[1:4]] and r[5]==s.name
assert len({r[0] for r in d['rows']})==39 and sum(r[4]=='Rookie' for r in d['rows'])==40
assert 'Team' not in d['headers']
op=xp.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']==p['oddsSha256']
compact=lambda s:re.sub(r'\s+','',s)
for pn,page in enumerate(PdfReader(op).pages,1):
 lines=page.extract_text().splitlines();assert lines[2]=='Card '+' '.join(d['formats'])
 actual=[compact(x) for x in lines[3:] if compact(x)]
 expected=[compact(o['name']+''.join(o['values'][f] or '-' for f in d['formats'])) for o in d['odds'] if o['page']==pn]
 assert actual==expected,pn
assert len(d['odds'])==323 and d['oddsUnitsPublished'] is False
assert [(o['name'],o['values'],o['page']) for o in d['odds']]==[(o['name'],o['values'],o['page']) for o in d['officialOddsTable']]
specs=json.loads((ROOT/'data/parallel-specifications.json').read_text())['sets'][SLUG]
assert len(specs)==7 and all(s['numbering']=='1/1' and s['name']=='FoilFractor' for s in specs)
assert {s['family'] for s in specs}=={'BASE CARDS I',*['PEAK PERFORMANCE '+tag for tag in ['LGD','SPD','PWR','AGI','MIC','REF']]}
for spec in specs:
 assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
 assert any(o['name']==spec['oddsName'] and o['family']==spec['family'] for o in d['odds'])
assert all(o.get('familyAliases')==['BASE CARDS II'] for o in d['odds'] if o['family']=='BASE CARDS I')
assert all(not o.get('numbering') for o in d['odds']),'Card examples cannot turn into family-wide odds limits'
tables=[t for t in d['publishedSpecifications'] if 'Card number' in t['headers']];assert len(tables)==6
for family,number,names,parallel,statement,qualification in facts['cardExamples']:
 assert [r[2] for r in d['rows'] if r[0]==family and r[1]==number]==names
 table=next(t for t in tables if t['name']==family);assert table['rows']==[[number,' / '.join(names),parallel,statement,qualification]]
 assert 'Published numbering' not in table['headers'],'Named-card values must not become family numbering'
 assert hashlib.sha256((ROOT/table['evidenceFile']).read_bytes()).hexdigest()==table['evidenceSha256']
assert next(t for t in tables if t['name']=='BASE CARDS II')['rows'][0][2]=='Not named in guide'
assert next(t for t in tables if t['name']=='TAG TEAM RELIC AUTOGRAPHS')['rows'][0][:2]==['TTR-ZR','Sol Ruca / Zaria']
r=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG)
assert r['year']=='2026' and r['releaseDate'] is None
assert d['oddsSource'].endswith('2026_Topps_Universe_WWE_odds.pdf?v=1790191410')
print('Verified all 922 original workbook subjects / 40 Rookie flags, every physical cell of 323 three-format odds rows, seven base-only FoilFractor joins and six isolated card examples; no inferred teams, colors, odds units or release date.')
