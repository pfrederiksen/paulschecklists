"""Independently check Royalty's original odds, retained subjects and scoped guide joins."""
import hashlib,json,re
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-topps-royalty-wwe'
d=json.loads((ROOT/'data/imports'/(SLUG+'.json')).read_text())
p=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');assert hashlib.sha256(p.read_bytes()).hexdigest()==d['sha256']
compact=lambda s:re.sub(r'\s+','',s)
headings={compact(r[0]) for r in d['rows']}
for pn,page in enumerate(PdfReader(p).pages,1):
 lines=[line for line in page.extract_text().splitlines() if compact(line) not in headings and re.match(r'^\s*(?:\d{1,3}|[A-Z0-9]+-[A-Z0-9-]+)\s+',line)]
 assert [compact(line) for line in lines]==[compact(''.join(r[1:5])) for r in d['rows'] if r[5]==str(pn)],pn
assert len(d['rows'])==739 and len({r[0] for r in d['rows']})==34
op=p.with_name(SLUG+'-odds.pdf');assert hashlib.sha256(op.read_bytes()).hexdigest()==d['oddsSha256']
original=[]
for pn,page in enumerate(PdfReader(op).pages,1):
 lines=page.extract_text().splitlines();assert any(re.fullmatch(r'\s*Card\s+Pack Odds\s*',line) for line in lines)
 for line in lines:
  m=re.fullmatch(r'\s*(.+?)\s+([\d,]+:[\d,]+)\s*',line)
  if m:original.append((pn,compact(m[1]),m[2]))
assert original==[(o['page'],compact(o['name']),o['values']['Pack Odds']) for o in d['officialOddsTable']]
assert len(original)==118 and d['formatNamesPublished'] is False and d['oddsUnitsPublished'] is True
specs=json.loads((ROOT/'data/parallel-specifications.json').read_text())['sets'][SLUG]
assert len(specs)==21 and sum(bool(s.get('oddsName')) for s in specs)==19
for s in specs:
 assert hashlib.sha256((ROOT/s['evidenceFile']).read_bytes()).hexdigest()==s['evidenceSha256']
 if s.get('oddsName'):assert any(o['name']==s['oddsName'] and o['family']==s['family'] for o in d['odds'])
regalia={s['name']:s for s in specs if s['family']=='REGALIA RELIC SIGNATURES'}
assert not regalia['Silver'].get('oddsName') and not regalia['Green'].get('oddsName')
assert regalia['Silver']['numbering']=='/10' and regalia['Green']['numbering']=='/5'
gold=next(o for o in d['odds'] if o['name']=='Regalia Relic Signatures Gold');assert not gold.get('numbering')
assert not any(s.get('oddsName')=='Regalia Relic Signatures Gold' for s in specs)
assert len([r for r in d['rows'] if r[0]=='WRESTLEMANIA PATCH AUTOGRAPHS'])==31
assert len([r for r in d['rows'] if r[0]=='REGALIA RELIC SIGNATURES'])==42
assert next(o for o in d['odds'] if o['name']=='Liquid Gold')['family']=='Liquid Gold (roster join unverified)'
assert not any('Superfractor' in s['name'] for s in specs),'Unscoped Key Facts must not number source families'
r=next(r for r in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if r['slug']==SLUG)
assert r['releaseDate'] is None and r['year']=='2025'
assert r['regionalReleaseEvidence']['date']=='2026-05-01' and r['regionalReleaseEvidence']['region']=='UK'
assert r['regionalReleaseEvidence']['source'].startswith('https://ripped.topps.com/uk/')
print('Verified all 739 subject lines / 118 odds, 21 exact-family terms / 19 odds joins, guide-only Silver/Green, unnumbered Gold, original count discrepancies and UK-only release evidence.')
