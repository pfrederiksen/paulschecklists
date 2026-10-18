"""Reconcile all PDF cells, source hashes, exact guide families and web joins."""
import hashlib
import json
import re
from collections import Counter
from import_topps_now_rtod_pdf_2026 import ROOT,SLUG,SOURCES,parse,document,BOX_TITLE,DUAL_TITLE,GOLD_TITLE,TEAM_TITLE,FAMILY_MAP,GAP
from import_topps_now_rtod_teams_2026 import TEAMS,identity,FAMILY
from import_topps_now_rtod_special_2026 import BOX,JAPAN,PROGRAMS
import import_official_catalog as generic

catalog=json.loads((ROOT/'data/set-catalog.json').read_text())['sets'];registry=json.loads((ROOT/'data/parallel-specifications.json').read_text())['sets']
teams,_=parse(document('teams')[0],'teams');box,_=parse(document('box')[0],'box')
load=lambda slug:json.loads((ROOT/'data/imports'/(slug+'.json')).read_text())
t=load(SLUG);b=load(BOX)
assert t['rows']==[[r['family'],r['cells'][0],*r['cells'][2:],r['cells'][1],str(r['page'])] for r in teams]
assert b['rows']==[[r['family'],*r['cells'],str(r['page'])] for r in box]
assert len(t['rows'])==300 and len(b['rows'])==259
assert Counter(r[0] for r in b['rows'])=={BOX_TITLE:56,DUAL_TITLE:9,GOLD_TITLE:194}
assert sum(r[5]=='RC' for r in t['rows'])==50 and sum(r[5]=='RC' for r in b['rows'])==63
assert sum(r[6]=='PARALLELS' for r in t['rows'])==110
assert next(r for r in t['rows'] if r[1]=='OD-243')[2:6]==['Iván Herrera','St. Louis Cardinals®','OF','']
assert next(r for r in t['rows'] if r[1]=='OD-244')[2:6]==['Iván Herrera','St. Louis Cardinals®','C/DH','']
assert next(r for r in t['rows'] if r[1]=='OD-277')[6]=='PARALLELS'
assert t['rows'][-1][1:3]==['OD-300','Logan Webb'] and b['rows'][-1][1:3]==['OD-299','Willy Adames']
assert b['rows'][0][1:6]==['A-MT','Mike Trout','Angels®','OF','']
assert sum(r[0]==DUAL_TITLE and ' / ' in r[2] for r in b['rows'])==9
assert {r[3] for r in b['rows'] if r[0]==DUAL_TITLE and r[1] in ['A-SD','A-AW','A-IO']}=={'Major League Baseball®'}
assert next(r for r in t['rows'] if r[1]=='OD-239')[2]=='Rafael Flores Jr.'
assert next(r for r in b['rows'] if r[1]=='OD-239')[2]=='Rafael Flores'
for slug,kind in [(SLUG,'teams'),(BOX,'box')]+[(identity(k)[0],'teams') for k in TEAMS]:
 d=load(slug);r=next(s for s in catalog if s['slug']==slug)
 assert d['source']==r['checklistUrl']==SOURCES[kind][0] and d['sha256']==r['sha256']==SOURCES[kind][1]
 assert r['rowCount']==len(d['rows']) and r['dedicatedParser']=='scripts/import_topps_now_rtod_pdf_2026.py' and generic.run(r.copy())==r
 assert r['coverageComplete'] is False and r['releaseDate'] is None and not d.get('odds') and not d.get('formats')
 assert d['rookieColumn']==5 and d['headers'][3:6]==['Team','Pos.','RC']
 assert [p['page'] for p in d['rawPages']]==list(range(1,8 if kind=='teams' else 7)) and all(p['text'] for p in d['rawPages'])
 if kind=='teams':assert registry[slug]==[]
expected=[(FAMILY_MAP[f],name,n) for f,terms in PROGRAMS.items() for n,name in terms]
assert [(m['family'],m['name'],m['numbering']) for m in registry[BOX]]==expected
for m in registry[BOX]:assert hashlib.sha256((ROOT/m['evidenceFile']).read_bytes()).hexdigest()==m['evidenceSha256']
assert [m['family'] for m in registry[BOX] if m['numbering']=='/26']==[GOLD_TITLE]
assert GAP in b['coverageNote']
for key in TEAMS:
 d=load(identity(key)[0]);by={r['cells'][2]:r for r in teams if re.sub('[®™]','',r['cells'][3])==TEAMS[key][0]}
 assert len(d['rows'])==len(by)==10
 for r in d['rows']:
  p=by[r[2]];c=p['cells'];assert r[:7]==[FAMILY,c[0],*c[2:],c[1]] and r[-2:]==[SOURCES['teams'][0],str(p['page'])]
  assert r[7] in {'','parallel subject'} and r[8].startswith(r[2])
  if key!='angels':assert bool(r[7])==bool(r[6])
  else:assert not r[7] and bool(r[6])==(r[1] in ['OD-111','OD-112'])
assert all(not r[1] for r in load(JAPAN)['rows']) and registry[JAPAN]==[]
assert not json.loads((ROOT/'data/topps-now-archive-index.json').read_text())['coverageComplete']
print('Verified every physical cell across 559 PDF rows, 113 literal RC marks, 110 PARALLELS marks, nine dual signer pairs, 13 exact team/name joins, separate Angels web/PDF marks, raw document hashes and nine exact-family guide limits. Japan IDs and historical completeness remain unverified.')
