"""Compare all Three Basketball original text lines using independent pypdf."""
import collections,hashlib,json,re
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-26-topps-three-basketball'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
compact=lambda s:re.sub(r'\s+','',s)
assert hashlib.sha256(path.read_bytes()).hexdigest()==d['sha256']
assert d['dedicatedParser']=='scripts/import_topps_three_basketball_2025.py'
assert d['headers']==['Checklist section','Card number','Name','Source page','Team']
heads={compact(r[0]) for r in d['rows']}|{compact(n[1]) for n in d['sourceDocumentNotes']}
for pn,page in enumerate(PdfReader(path).pages,1):
 actual=[compact(line) for line in page.extract_text().splitlines() if compact(line) and compact(line) not in heads]
 expected=[compact(r[1]+r[2]+r[4]) for r in d['rows'] if r[3]==str(pn)]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b],len(actual),len(expected))
assert len(d['rows'])==1171 and len({tuple(r[:2]) for r in d['rows']})==1137 and len({r[0] for r in d['rows']})==28
assert d['rows']==d['originalSubjectRows'] and 'Rookie' not in d['headers']
assert {r[1] for r in d['rows'] if r[0]=='BASE CARDS'}=={str(i) for i in range(1,101)}
assert len([r for r in d['rows'] if r[0]=='3 AND D'])==40 and not any(r[1]=='3' and r[2]=='AND D' for r in d['rows'])
triples=[r for r in d['rows'] if r[0]=='TRIPLE RELICS AUTOGRAPHS']
assert len(triples)==51 and set(collections.Counter(r[1] for r in triples).values())=={3}
assert [r[2] for r in triples if r[1]=='TRA-CKK']==['Kon Knueppel','Khaman Maluach','Cooper Flagg']
assert next(r for r in d['rows'] if r[1]=='6')[4]=='Houston Rockets'
assert next(r for r in d['rows'] if r[1]=='IW-25')[4]=='Phoenix Suns'
assert next(r for r in d['rows'] if r[1]=='90')[2]=='Yanic Konan-Niederhaüser'
assert next(r for r in d['rows'] if r[1]=='RPV-NC')[2]=='NIque Clifford'
assert next(r for r in d['rows'] if r[1]=='TP-Td')[2]=='Tristan da Silva'
assert d['rows'][-1]==['GAME TIME GRAPHS','GT-ZRA','Zach Randolph','24','Memphis Grizzlies']
op=path.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
for pn,page in enumerate(PdfReader(op).pages,1):
 actual=[compact(line) for line in page.extract_text().splitlines() if re.search(r'\d+:[\d,]+',line)]
 expected=[compact(o['name']+''.join(o['values'][f] or '' for f in ['Hobby','FDI'])) for o in d['officialOddsTable'] if o['page']==pn]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b],len(actual),len(expected))
assert len(d['odds'])==154 and d['formats']==['Hobby','FDI'] and d['oddsUnitsPublished'] is False
assert [(o['name'],o['values'],o['page']) for o in d['odds']]==[(o['name'],o['values'],o['page']) for o in d['officialOddsTable']]
by=lambda n:next(o for o in d['odds'] if o['name']==n)
assert by('3 and D')['family']=='3 AND D' and by('Re-Markable')['family']=='REMARKABLE'
assert by('Rookie-verse Autographs')['family']=='ROOKIEVERSE AUTOGRAPHS'
for label,value in [('Horizontal Bronze','1:23'),('Horizontal Platinum','1:554'),('Vertical Platinum','1:554')]:
 assert by('Rookie 3 Patch Autographs '+label)['values']=={'Hobby':value,'FDI':value}
for direction in ['Horizontal','Vertical']:
 for parallel,value in [('Emerald','1:2'),('Holo Gold','1:5')]:assert by('Rookie 3 Patch Autographs '+direction+' '+parallel)['values']=={'Hobby':None,'FDI':value}
assert sum(sum(v is not None for v in o['values'].values()) for o in d['odds'])==304
assert not d['parallelSpecifications'] and not any(o.get('numbering') for o in d['odds'])
for spec in d['publishedSpecifications']:assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
examples=[r for s in d['publishedSpecifications'] if s['headers'][0]=='Card number' for r in s['rows']]
assert len(examples)==7 and sum(r[2]=='Not named' for r in examples)==6
assert next(r for r in examples if r[0]=='TD-LJ')[2:4]==['Superfractor','1/1']
proof=json.loads((ROOT/'data/parallel-audit-sources/three-basketball-2025-26-physical-20261017.json').read_text())
assert hashlib.sha256((ROOT/proof['candidateEvidence']['file']).read_bytes()).hexdigest()==proof['candidateEvidence']['sha256']
r=next(s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if s['slug']==SLUG)
assert r['releaseDate']=='2026-03-05' and r['year']=='2025-26'
print('Verified all 1,171 Three subjects / 1,137 identities, 28 sections, 17 complete triples, all 154 odds / 304 literal values and seven exact card-scoped guide examples; no inferred rookie flags or family-wide limits.')
