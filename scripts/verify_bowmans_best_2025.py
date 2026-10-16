"""Independently validate original Bowman’s Best lines, columns, literal odds and guide scopes."""
import hashlib,json,re,sys
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-bowman-s-best-baseball';d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());p=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');compact=lambda s:re.sub(r'\s+','',s)
assert hashlib.sha256(p.read_bytes()).hexdigest()==d['sha256']
heads={compact(r[0]) for r in d['rows']}|{'BASE','INSERT','AUTOGRAPH','AUTOGRAPHRELIC',compact("2025 Bowman's Best Baseball Checklist"),'*SubjecttoChange'}
for pn,page in enumerate(PdfReader(p).pages,1):
 actual=[compact(line) for line in page.extract_text().splitlines() if compact(line) and compact(line) not in heads]
 expected=[compact(r[1]+r[2]+r[4]+r[5]) for r in d['originalSubjectRows'] if r[3]==str(pn)]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b])
assert len(d['rows'])==697 and len({tuple(r[:2]) for r in d['rows']})==594 and len({r[0] for r in d['rows']})==20
assert sum(r[5]=='Rookie' for r in d['rows'])==123
assert next(r for r in d['rows'] if r[1]=='B25-ÉP')[2:]==['Émilien Pitre','7','Tampa Bay Rays™','','']
base={r[1] for r in d['rows'] if r[0]=='BASE CARDS'};assert base=={str(i) for i in range(1,71)}|{'TP-'+str(i) for i in range(1,31)}
futures=[r for r in d['rows'] if r[0]=='2025 MLB ALL STAR FUTURES GAME'];assert len(futures)==20 and all(not r[4] and r[6] in {'NATIONAL LEAGUE','AMERICAN LEAGUE'} for r in futures)
assert not any(r[1]=='2025' for r in d['rows'])
for r,original in zip(d['rows'],d['originalSubjectRows']):assert r[:4]==original[:4] and (r[4] or r[6])==original[4] and r[5]==original[5]
assert [(r[2],r[4]) for r in d['rows'] if r[1]=='DA-CG']==[('Bubba Chandler','Pittsburgh Pirates®'),('Konnor Griffin','Pittsburgh Pirates®')]
assert d['rows'][-1][1:]==['PPA-YM','Yohandy Morales','15','Washington Nationals®','','']
op=p.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
for pn,page in enumerate(PdfReader(op).pages,1):
 # Bowman Showpieces rows are cards, unlike the two document-heading lines.
 actual=[compact(l) for l in page.extract_text().splitlines() if compact(l) and not l.startswith("2025 Bowman's Best Baseball") and l.strip()!='SUBJECT TO CHANGE']
 expected=[compact(o['name']+o['values']['HOBBY']) for o in d['officialOddsTable'] if o['page']==pn]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b])
assert len(d['odds'])==107 and d['formats']==['HOBBY'] and d['oddsUnitsPublished'] is False
assert next(o for o in d['odds'] if o['name']=='Best of 2025 Autographs')['values']['HOBBY']=='1:07'
assert next(o for o in d['odds'] if o['name']=='2025 MLB All-Star Futures Game')['family']=='2025 MLB ALL STAR FUTURES GAME'
assert next(o for o in d['odds'] if o['name']=='Best Mix Autograph Diecuts')['family']=='BEST MIX AUTOGRAPHS'
assert [(o['name'],o['page'],o['values']) for o in d['odds']]==[(o['name'],o['page'],o['values']) for o in d['officialOddsTable']]
reg=json.loads((ROOT/'data/parallel-specifications.json').read_text())['sets'][SLUG];assert len(reg)==53
assert next(s for s in reg if s['oddsName']=='Base Cards Lazer')['numbering']=='/350'
assert next(s for s in reg if s.get('oddsName')=='Best of 2025 Autographs Refractor')['numbering']=='Limited to 500; serial numbering not stated'
assert len([s for s in reg if s['family']=='STROKES OF GOLD' and not s.get('oddsName')])==5
assert next(s for s in reg if s['name']=='Sterling-Tek').get('oddsName') is None
assert not any(s.get('oddsName')=='Best-Tek' for s in reg)
for spec in reg+d['publishedSpecifications']:assert hashlib.sha256((ROOT/spec['evidenceFile']).read_bytes()).hexdigest()==spec['evidenceSha256']
assert d['publishedSpecifications'][0]['rows'][0][:2]==['Refractor','1 per pack']
assert d['publishedSpecifications'][1]['rows'][0][:2]==['Mini-Diamond Refractor','1 per case']
r=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG);assert r['releaseDate'] is None and r['year']=='2025' and r['dedicatedParser']=='scripts/import_bowmans_best_2025.py'
sys.path.insert(0,str(ROOT/'scripts'));from verify_official_imports import verify;assert verify(r)[0]==107
print('Verified 697 physical subjects / 594 identities, restored B25-ÉP, 123 Rookie marks, 20 separate league values, all 107 Hobby literals, 53 scoped guide terms and distinct distribution units.')
