"""Verify separate Japan Edition data and Collector's Box specification scope."""
import hashlib
import json
from pathlib import Path
import import_official_catalog as generic
from import_topps_now_rtod_special_2026 import JAPAN,BOX,JPAGE,BPAGE,JPROOF,BPROOF,FAMILY,PROGRAMS,GAP

root=Path(__file__).resolve().parents[1];catalog=json.loads((root/'data/set-catalog.json').read_text())['sets'];registry=json.loads((root/'data/parallel-specifications.json').read_text())['sets']
for slug,page,file in [(JAPAN,JPAGE,JPROOF),(BOX,BPAGE,BPROOF)]:
 proof=json.loads((root/file).read_text());h=hashlib.sha256((root/file).read_bytes()).hexdigest();d=json.loads((root/'data/imports'/(slug+'.json')).read_text());r=next(s for s in catalog if s['slug']==slug)
 assert d['sourceProducts'][0]['sha256']==h and proof['documentLinks']==[]
 if slug==JAPAN:assert d['source']==page and d['sha256']==h
 assert r['releaseDate'] is None and r['releaseStatus']=='Unverified' and r['coverageComplete'] is False and generic.run(r.copy())==r
 assert dict(proof['specs'])['Available From']=='Mar 20, 2026' and dict(proof['specs'])['Available Until']=='Apr 6, 2026'
 assert not d.get('odds') and not d.get('formats')
 if slug==JAPAN:
  names=['Shohei Ohtani','Mookie Betts','Freddie Freeman','Roki Sasaki','Will Smith','Yoshinobu Yamamoto','Edwin Díaz','Teoscar Hernández','Kyle Tucker','Blake Snell']
  assert d['rows']==[[FAMILY,'',name,name,page] for name in names] and len(d['headers'])==5
  lines=[s for s in proof['description'].splitlines() if s];assert lines[2:-1]==names
  assert [s.strip() for s in proof['descriptionParagraphs'] if s.strip()][2:-1]==names
  assert registry[slug]==[] and r['parallelData'] is False
  assert not any(token in str(row[1]) for s in d['publishedSpecifications'] for row in s['rows'] for token in ['/199','/150','356'])
  assert d['publishedSpecifications'][0]['headers']==['Official field','Official value','Qualification']
  fields={row[0]:row[1] for row in d['publishedSpecifications'][0]['rows']};assert fields['Published bundle print run']=='4693'
 else:
  from import_topps_now_rtod_pdf_2026 import FAMILY_MAP,GOLD_TITLE,DUAL_TITLE,GAP as PDF_GAP
  assert len(d['rows'])==259 and r['rowCount']==259 and r['sections']==3 and r['status']=='Source table'
  assert d['publishedChecklistClaim']=='300 players' and PDF_GAP in d['coverageNote']
  expected=[(FAMILY_MAP[family],name,n) for family,terms in PROGRAMS.items() for n,name in terms]
  assert [(m['family'],m['name'],m['numbering']) for m in registry[slug]]==expected and len(expected)==9
  assert [(FAMILY_MAP[family],name,n) for family in PROGRAMS for name,n,*_ in next(s for s in d['publishedSpecifications'] if s['name']==FAMILY_MAP[family])['rows']]==expected
  assert d['oddsUnitsPublished'] is False and d['formatNamesPublished'] is False
  fields={row[0]:row[1] for row in d['publishedSpecifications'][-1]['rows']}
  assert fields['Actual box print run']=='Not published' and fields['Card and signer rosters']=='259 published PDF entries'
  assert 'three 8-card packs' in fields['Published box configuration'] and 'numbered to 99 or less' in fields['Published box configuration']
  assert all(m['family']==GOLD_TITLE for m in registry[slug] if m['numbering']=='/26')
  assert len([m for m in registry[slug] if m['family']==DUAL_TITLE])==2
regular=json.loads((root/'data/imports/topps-bowman-2026-rtod-topps-now-los-angeles-dodgers.json').read_text());assert len(regular['rows'])==10 and all(row[7]=='parallel subject' for row in regular['rows']);assert any('/199' in str(s['rows']) for s in regular['publishedSpecifications'])
assert not json.loads((root/'data/topps-now-archive-index.json').read_text())['coverageComplete']
print('Verified ten separate Japan Edition names and PR4693 without regular-edition term inheritance; 259 Collector’s Box PDF rows with nine exact family terms, qualified configuration and explicit 300-player base-claim gap. No box run, pack odds or release inferred.')
