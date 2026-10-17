"""Independently compare all Chrome Black Football subject and odds lines."""
import collections,hashlib,json,re
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-topps-chrome-black-football'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
compact=lambda s:re.sub(r'\s+','',s)
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_chrome_black_football_2025.py'
assert d['headers']==['Checklist section','Card number','Name','Source page','Team','Rookie']
heads={compact(r[0]) for r in d['rows']}|{compact(n[1]) for n in d['sourceDocumentNotes']}
for pn,page in enumerate(PdfReader(path).pages,1):
 actual=[compact(line) for line in page.extract_text().splitlines() if compact(line) and compact(line) not in heads]
 expected=[compact(r[1]+r[2]+r[4]+r[5]) for r in d['rows'] if r[3]==str(pn)]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b],len(actual),len(expected))
assert len(d['rows'])==475 and len({tuple(r[:2]) for r in d['rows']})==458 and len({r[0] for r in d['rows']})==12
assert d['rows']==d['originalSubjectRows'] and sum(r[5]=='Rookie' for r in d['rows'])==189
assert {r[1] for r in d['rows'] if r[0] in {'BASE CARDS','ROOKIES'}}=={str(i) for i in range(1,151)}
duals=[r for r in d['rows'] if r[0]=='PITCH BLACK PAIRINGS DUAL AUTOGRAPHS']
assert len(duals)==34 and set(collections.Counter(r[1] for r in duals).values())=={2}
assert [(r[2],r[4],r[5]) for r in duals if r[1]=='PBDA-CWMO']==[('Cam Ward','Tennessee Titans','Rookie'),('Warren Moon','Houston Oilers','')]
assert all(r[5]=='' for r in duals if r[1] in {'PBDA-JDCW','PBDA-CWLB'})
assert next(r for r in d['rows'] if r[1]=='31')[4]=='Green Bay Packers'
assert next(r for r in d['rows'] if r[1]=='79')[4]=='Indianapolis Colts'
assert next(r for r in d['rows'] if r[1]=='SFA-THE')[2]=='TREVEYON Henderson'
assert d['rows'][-1]==['PITCH BLACK PAIRINGS DUAL AUTOGRAPHS','PBDA-TTJW','Tua Tagovailoa','7','Miami Dolphins','']
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
for pn,page in enumerate(PdfReader(op).pages,1):
 actual=[compact(line) for line in page.extract_text().splitlines() if re.search(r'\d+:[\d,]+',line)]
 expected=[compact(o['name']+o['values']['Hobby']) for o in d['officialOddsTable'] if o['page']==pn]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b],len(actual),len(expected))
assert len(d['odds'])==84 and d['formats']==['Hobby'] and d['oddsUnitsPublished'] is False
assert [(o['name'],o['values'],o['page']) for o in d['odds']]==[(o['name'],o['values'],o['page']) for o in d['officialOddsTable']]
by=lambda n:next(o for o in d['odds'] if o['name']==n)
assert by('Base')['values']=={'Hobby':'3:1'} and by('Rookie')['values']=={'Hobby':'2:1'}
assert by('Base')['family']=='BASE CARDS' and by('Rookie')['family']=='ROOKIES'
assert by('Rookie Design Variation')['family']=='ROOKIES DESIGN VARIATION'
assert by('Rookie Autographs')['family']=='ROOKIES AUTOGRAPHS'
assert by('Autographs')['family']=='AUTOGRAPH CARDS'
assert by('Pitch Black Pairings Dual Autos Refractor')['family']=='PITCH BLACK PAIRINGS DUAL AUTOGRAPHS'
assert not d['parallelSpecifications'] and not any(o.get('numbering') for o in d['odds'])
for spec in d['publishedSpecifications']:assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
examples=[r for s in d['publishedSpecifications'] if s['headers'][0]=='Card number' for r in s['rows']]
assert len(examples)==5 and {r[0] for r in examples}=={'PBDA-DMTB','PBDA-JDCW','IA-JD','BL-6','RAU-JD'}
assert next(r for r in examples if r[0]=='RAU-JD')[2]=='Not named'
registry=json.loads((ROOT/'data/release-dates.json').read_text());release=next(e for e in registry['dates'] if e['slug']==SLUG)
assert release['releaseDate']=='2026-07-10' and 'Friday, July 10' in registry['sources'][release['source']]['statement']
print('Verified 475 physical subjects / 458 identities, 189 Rookie marks, 17 complete duals, all 84 literal Hobby odds and five strictly card-scoped examples; July 10 release evidence retained separately.')
