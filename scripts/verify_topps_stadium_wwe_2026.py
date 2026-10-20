"""Verify every WWE glyph row, repeated odds caption and approved guide scope."""
import collections,copy,hashlib,json,re,sys
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-stadium-club-wwe';UNJOINED='Base Chrome Autographs II / repeated captions (roster join unverified)'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text());p=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');compact=lambda s:re.sub(r'\s+','',s)
assert hashlib.sha256(p.read_bytes()).hexdigest()==d['sha256']
heads={r[0] for r in d['rows']}|{'BASE','INSERT','AUTOGRAPH','2026 Topps Stadium Club WWE Checklist'}
for pn,page in enumerate(PdfReader(p).pages,1):
 actual=[compact(l) for l in page.extract_text().splitlines() if l.strip() and l.strip() not in heads and not l.startswith('Checklists provided')]
 expected=[compact(r[1]+r[2]+r[3]+r[4]) for r in d['rows'] if r[5]==str(pn)]
 assert actual==expected,(pn,[(a,b) for a,b in zip(actual,expected) if a!=b])
assert len(d['rows'])==938 and len({r[0] for r in d['rows']})==25 and len({tuple(r[:2]) for r in d['rows']})==930
assert d['originalSubjectRows']==d['rows'] and sum(r[4]=='Rookie' for r in d['rows'])==35
assert next(r for r in d['rows'] if r[:2]==['BASE CARDS','8'])[2:]==['"The American Nightmare" Cody Rhodes','Smackdown','','1']
assert {int(r[1]) for r in d['rows'] if r[0]=='BASE CARDS'}==set(range(1,201))
assert [r[2] for r in d['rows'] if r[:2]==['DUAL AUTOGRAPHS','DA-CA']]==['Charlotte Flair','Alexa Bliss']
assert not any(h.lower()=='team' for h in d['headers'])
op=p.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
for pn,page in enumerate(PdfReader(op).pages,1):
 lines=page.extract_text().splitlines();assert compact(lines[2])==compact(''.join(d['officialOddsHeader']))
 expected=[compact(o['name']+''.join(o['values'][f] or '-' for f in d['formats'])) for o in d['officialOddsTable'] if o['page']==pn]
 assert [compact(l) for l in lines[3:]]==expected
assert len(d['odds'])==122 and d['formats']==['Hobby SKU','Value Box SKU','Mega Box SKU'] and d['oddsUnitsPublished'] is False
assert [(o['name'],o['values'],o['page']) for o in d['odds']]==[(o['name'],o['values'],o['page']) for o in d['officialOddsTable']]
assert sum(o['family']==UNJOINED for o in d['odds'])==5
assert collections.Counter(o['name'] for o in d['odds'])['Base Chrome Autographs Superfractor']==2
assert len(d['parallelSpecifications'])==13
numbered={s['oddsName']:s['numbering'] for s in d['parallelSpecifications'] if s.get('oddsName')}
assert len(numbered)==11 and numbered['Base Card Autographs Gold']=='/50' and numbered['Inked Autographs Purple']=='/25' and numbered['Inked Autographs Green']=='/5'
assert not any(s['family'] in {'BASE CARDS','BASE CARDS AUTOGRAPH VARIATION II','DUAL AUTOGRAPHS','CONCENTRATION AUTOGRAPHS'} for s in d['parallelSpecifications'])
assert any(s['name']=='Pearl White' and s['numbering']=='/30' and not s.get('oddsName') for s in d['parallelSpecifications'])
assert any(s['name']=='Gold Minted' and s['numbering']=='Not stated' for s in d['parallelSpecifications'])
for t in d['publishedSpecifications']:assert hashlib.sha256((ROOT/t['evidenceFile']).read_bytes()).hexdigest()==t['evidenceSha256']
beam=next(t for t in d['publishedSpecifications'] if t['name']=='BEAM TEAM')
assert len([r for r in d['rows'] if r[0]=='BEAM TEAM'])==20
assert beam['rows'][0]==['Distribution','One per case','Manufacturer statement; box format and case configuration are not specified. This is not a per-pack rate.']
assert beam['rows'][1][1]=='20 Superstars' and beam['rows'][2][1]=='Laser foilboard'
assert not any(s['family']=='BEAM TEAM' for s in d['parallelSpecifications'])
r=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG);assert r['releaseDate']=='2026-10-23' and r['releaseStatus']=='Upcoming' and r['verifiedRelease']
sys.path.insert(0,str(ROOT/'scripts'));from import_official_catalog import run
assert run(copy.deepcopy(r))==r
print('Verified all 938 WWE subjects, 25 families, 35 literal Rookie marks, 122 × 3 odds cells, five unjoined repeated/II captions and 13 precisely scoped guide additions; October 23 remains Upcoming.')
