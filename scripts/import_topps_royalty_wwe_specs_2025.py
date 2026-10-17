"""Reapply exact UK Royalty WWE guide terms without global color/date inference."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-topps-royalty-wwe'
PROOF=ROOT/'data/parallel-audit-sources/royalty-wwe-2025-guide-20261017.json'
UNJOINED='Liquid Gold (roster join unverified)'

def supplement(data):
 proof=json.loads(PROOF.read_text());evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=hashlib.sha256(PROOF.read_bytes()).hexdigest())
 assert (data['sha256'],data['oddsSha256'])==(proof['checklistSha256'],proof['oddsSha256']),'A source revision requires physical and guide reconciliation'
 assert len(data['rows'])==739 and len(data['odds'])==118
 families={r[0] for r in data['rows']};aliases={f.title():f for f in families}
 aliases.update({'Base':'BASE CARDS','Autograph Jumbo Relic Booklet':'AUTOGRAPH JUMBO RELIC BOOKLET CARDS',
  'Dual Superstar Relic Autos':'DUAL SUPERSTAR RELIC AUTOGRAPHS',"U Can't See Me Relics":'U CANT SEE ME RELICS',
  '100% Stratusfaction Relics':'100 PERCENT STRATUSFACTION RELICS','The Rock Retrospective':'THE ROCK RETROSPECTIVE AUTOGRAPHS'})
 original=[{k:o[k] for k in ['name','values','page']} for o in data['odds']];odds=[]
 for item in original:
  if item['name']=='Liquid Gold':odds.append(dict(item,family=UNJOINED));continue
  prefix=next((a for a in sorted(aliases,key=len,reverse=True) if item['name'].casefold()==a.casefold() or item['name'].casefold().startswith(a.casefold()+' ')),None)
  assert prefix,item['name'];odds.append(dict(item,family=aliases[prefix],familyBase=item['name'].casefold()==prefix.casefold()))
 specs=[]
 for term in proof['guideTerms']:
  assert term['family'] in families
  if term.get('oddsName'):assert any(o['name']==term['oddsName'] and o['family']==term['family'] for o in odds),term
  specs.append(dict(term,source=proof['source'],**evidence))
 assert len(specs)==21 and sum(bool(s.get('oddsName')) for s in specs)==19
 table=lambda name,headers,rows:dict(name=name,headers=headers,rows=rows,source=proof['source'],worksheet='Official UK guide; regional date and exact family scopes retained',**evidence)
 note=('All 739 physical subject rows / 34 sections and original designation/Rookie cells remain unchanged. All 118 Pack Odds values remain literal. '
  'Pack Odds states a pack unit but names no format; the format selector remains disabled. '
  'The UK guide supplies 21 exact-family numbering terms, including 19 odds joins and two guide-only Regalia Silver/Green entries. '
  'Regalia Gold remains unnumbered. The guide’s 50-versus-31 WrestleMania and 50-versus-42 Regalia subject counts remain explicit. '
  'Mixed 2025/2026 prose and generic Superfractor wording do not relabel the source or number unreviewed families. '
  'May 1 is UK regional release evidence, separate from May 5 publication and an unverified general release date. Exhaustive parallel numbering remains incomplete.')
 data.update(odds=odds,officialOddsTable=original,officialOddsFormats=['Pack Odds'],officialOddsHeader=['Card','Pack Odds'],
  formatNamesPublished=False,oddsUnitsPublished=True,parallelSpecifications=[],
  publishedSpecifications=[table('Official guide program sizes',['Checklist family','Guide subjects','Physical checklist subjects'],proof['guideCounts']),
   table('Regional release evidence',['Region','Published release date','Qualification'],[['UK','2026-05-01','Requested U.S. guide redirected to UK; general release date remains unverified']]),
   table('Qualified guide wording',['Published statement','Qualification'],[[s,'Retained source inconsistency; no additional family limits inferred'] for s in proof['sourceQualifications']])],
  sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
 rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=specs
 registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Guide-only parallels, program-size discrepancies and regional scope',gap=' '.join(proof['remainingGaps']),source=proof['source'],**evidence)]
 rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 meta=dict(verified=proof['observed'],catalogEvidence=note,dataAudit=note,
  regionalReleaseEvidence=dict(**proof['regionalRelease'],source=proof['source'],**evidence),
  sourceObservation=dict(file=evidence['evidenceFile'],sha256=evidence['evidenceSha256'],source=proof['source']))
 return data,meta

def build():
 from import_topps_tribute_2026 import acquire
 cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(s for s in catalog['sets'] if s['slug']==SLUG)
 dp=ROOT/record['tableData'];data=json.loads(dp.read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
 assert acquire(record['checklistUrl'],path)==data['sha256']
 assert acquire(data['oddsSource'],path.with_name(SLUG+'-odds.pdf'))==data['oddsSha256']
 data,meta=supplement(data);record.update(meta);dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
 cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());inventory=[record if r['slug']==SLUG else r for r in inventory]
 ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 print('Royalty WWE: retained 739 subjects / 118 literal odds; reconciled 21 scoped guide terms / 19 exact odds joins; May 1 stays UK-only.')

if __name__=='__main__':build()
