"""Compare every original Stadium Club subject and odds line independently."""
import collections,hashlib,json,re
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-topps-stadium-club-baseball'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
compact=lambda s:re.sub(r'\s+','',s)
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_stadium_baseball_2025.py'
assert d['headers']==['Checklist section','Card number','Name','Source page','Team','Rookie']
heads={compact(r[0]) for r in d['rows']}|{compact(n[1]) for n in d['sourceDocumentNotes']}
for pn,page in enumerate(PdfReader(path).pages,1):
 actual=[compact(line) for line in page.extract_text().splitlines() if compact(line) and compact(line) not in heads]
 expected=[compact(r[1]+r[2]+r[4]+r[5]) for r in d['rows'] if r[3]==str(pn)]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b],len(actual),len(expected))
assert len(d['rows'])==649 and len({tuple(r[:2]) for r in d['rows']})==640 and len({r[0] for r in d['rows']})==14
assert d['rows']==d['originalSubjectRows'] and sum(r[5]=='Rookie' for r in d['rows'])==233
assert {r[1] for r in d['rows'] if r[0]=='BASE CARDS'}=={str(i) for i in range(1,201)}
duals=[r for r in d['rows'] if r[0]=='DUAL AUTOGRAPHS'];assert len(duals)==18 and set(collections.Counter(r[1] for r in duals).values())=={2}
assert [r[2] for r in duals if r[1]=='DA-WK']==['Nick Kurtz','Jacob Wilson']
assert [r[2] for r in duals if r[1]=='DA-BW']==['George Brett','Bobby Witt Jr.']
assert next(r for r in d['rows'] if r[1]=='7')[4]=='San Francisco Giants®'
assert next(r for r in d['rows'] if r[1]=='12')[4]=='Toronto Blue Jays®'
assert next(r for r in d['rows'] if r[1]=='93')[5]==''
assert next(r for r in d['rows'] if r[1]=='C-22')[5]=='Rookie'
assert d['rows'][-1]==['CONCENTRATION AUTOGRAPH VARIATION','TVA-YY','Yoshinobu Yamamoto','13','Los Angeles Dodgers®','']
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
formats=['Hobby','Value SE','Value EA','Mega SE','Mega EA','Fat Pack SE','Fat Pack EA']
for pn,page in enumerate(PdfReader(op).pages,1):
 actual=[compact(re.sub(r'(?<!\w)-(?!\w)','',line)) for line in page.extract_text().splitlines() if re.search(r'\d+:[\d,]+',line)]
 expected=[compact(o['name']+''.join(o['values'][f] or '' for f in formats)) for o in d['officialOddsTable'] if o['page']==pn]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b],len(actual),len(expected))
assert len(d['odds'])==80 and d['formats']==formats and d['oddsUnitsPublished'] is False
assert [(o['name'],o['values'],o['page']) for o in d['odds']]==[(o['name'],o['values'],o['page']) for o in d['officialOddsTable']]
by=lambda name:next(o for o in d['odds'] if o['name']==name)
assert by('Base Card Autograps')['family']=='BASE CARDS I AUTOGRAPH VARIATION' and by('Base Card Autograps')['familyBase']
assert by('Base Chrome Autographs')['family']=='CHROME BASE CARDS AUTOGRAPH VARIATION'
assert by("Goin' Yard Autographs")['family']=='GOIN YARD AUTOGRAPHS'
assert by('Base Pink')['values']==dict(zip(formats,[None,None,None,None,None,'1:1','1:1']))
assert by('Base Printing Plates Cyan')['values']['Hobby']=='1:2,593'
assert not d['parallelSpecifications'] and not any(o.get('numbering') for o in d['odds'])
for spec in d['publishedSpecifications']:assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
r=next(s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert r['year']=='2025' and r['releaseDate'] is None
print('Verified all Stadium Club source lines: 649 subjects / 640 identities, original teams, 233 Rookie marks, nine complete duals and 80 seven-column odds; no inferred numbering or release date.')
