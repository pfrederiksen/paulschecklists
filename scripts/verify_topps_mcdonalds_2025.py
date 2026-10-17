"""Independently compare every McDonald's subject and odds line to the PDFs."""
import collections, hashlib, json, re
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]; SLUG='topps-bowman-2025-topps-chrome-mcdonald-s-all-american-basketball'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text())
path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf'); compact=lambda s:re.sub(r'\s+','',s)
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_mcdonalds_2025.py'
assert d['headers']==['Checklist section','Card number','Name','Source page','Published East/West designation']
heads={compact(r[0]) for r in d['rows']}|{'INSERT','AUTOGRAPH','AUTOGRAPHRELIC','ChecklistisSubjecttochange'}
for pn,page in enumerate(PdfReader(path).pages,1):
    actual=[compact(line) for line in page.extract_text().splitlines() if compact(line) and compact(line) not in heads]
    expected=[compact(r[1]+r[2]+r[4]) for r in d['rows'] if r[3]==str(pn)]
    assert actual==expected,(pn,actual,expected)
assert len(d['rows'])==len({tuple(r[:2]) for r in d['rows']})==400 and len({r[0] for r in d['rows']})==12
assert d['rows']==d['originalSubjectRows'] and not any(h in d['headers'] for h in ['Team','Rookie'])
assert collections.Counter(r[4] for r in d['rows'])=={'East':183,'West':217}
assert {r[1] for r in d['rows'] if r[0]=='BASE CARDS'}=={str(i) for i in range(1,101)}
by=lambda code:next(r for r in d['rows'] if r[1]==code)
assert by('HR-27')[2]=='ZAKiyah Johnson' and by('GP-ZJ')[2]=='ZaKiyah Johnson' and by('27')[2]=='Zakiyah Johnson'
assert by('98')[2]=='Lebron James' and by('LA-LJ')[2]=='LeBron James'
assert d['rows'][-1]==['GOLDEN PATCH AUTOGRAPHS','GP-ZJ','ZaKiyah Johnson','9','East']
op=path.with_name(SLUG+'-odds.pdf'); assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
for pn,page in enumerate(PdfReader(op).pages,1):
    actual=[compact(line) for line in page.extract_text().splitlines() if re.search(r'\d+:\d+\s*$',line)]
    expected=[compact(o['name']+o['values']['Hobby']) for o in d['officialOddsTable'] if o['page']==pn]
    assert actual==expected,(pn,actual,expected)
assert len(d['odds'])==73 and d['formats']==['Hobby'] and d['oddsUnitsPublished'] is False
assert [(o['name'],o['values'],o['page']) for o in d['odds']]==[(o['name'],o['values'],o['page']) for o in d['officialOddsTable']]
assert d['odds'][0]['values']=={'Hobby':'9:1'}
assert next(o for o in d['odds'] if o['name']=='Event Autogrpahs')['family']=='EVENT AUTOGRAPHS'
assert not any(o['family']=='CONCRETE CANVAS' for o in d['odds'])
assert not d['parallelSpecifications'] and not any(o.get('numbering') for o in d['odds'])
for spec in d['publishedSpecifications']: assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
r=next(s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert r['year']=='2025' and r['releaseDate']=='2026-03-12' and r['releaseStatus']=='Released'
print('Verified all 400 original subjects / 12 sections, separate East/West cells, literal source spellings and 73 Hobby odds. March 12 release verified separately from product year; no inferred teams, rookie flags or parallel limits.')
