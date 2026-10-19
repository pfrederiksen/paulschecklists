"""Reconcile Universe's base FoilFractors and isolated official guide examples."""
import hashlib,json,re,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2026-topps-universe-wwe'
PROOF=ROOT/'data/parallel-audit-sources/universe-wwe-2026-guide-20261019.json'

def supplement(data):
 proof=json.loads(PROOF.read_text());facts=proof['normalizedFacts']
 assert hashlib.sha256(json.dumps(facts,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==proof['normalizedFactsSha256']
 assert (data['sha256'],data['oddsSha256'])==(proof['checklistSha256'],proof['oddsSha256']), 'Reconcile revised sources before applying guide evidence'
 assert len(data['rows'])==922 and len(data['odds'])==323
 evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=hashlib.sha256(PROOF.read_bytes()).hexdigest())
 families={r[0] for r in data['rows']};original=[{k:o[k] for k in ['name','values','page']} for o in data['odds']]
 aliases={f:f for f in families};aliases.update({'TITLE MARKS RELIC AUTOGRAPHS':'TITLE MARKS RELIC SIGNATURES','"STONE COLD" STEVE AUSTIN 30TH ANNIVERSARY AUTOGRAPHS':'STONE COLD STEVE AUSTIN 30TH ANNIVERSARY AUTOGRAPHS'})
 odds=[]
 for item in original:
  if item['name'].startswith('BASE '):
   suffix=re.search(r'\((LGD|SPD|PWR|AGI|MIC|REF)\)$',item['name'])
   family='PEAK PERFORMANCE '+suffix[1] if suffix else 'BASE CARDS I'
   odd=dict(item,family=family)
   if not suffix:odd['familyAliases']=['BASE CARDS II']
  else:
   prefix=next((a for a in sorted(aliases,key=len,reverse=True) if item['name']==a or item['name'].startswith(a+' ')),None)
   assert prefix,item['name'];odd=dict(item,family=aliases[prefix],familyBase=item['name']==prefix)
  assert odd['family'] in families;odds.append(odd)
 base_families=['BASE CARDS I','BASE CARDS II']+['PEAK PERFORMANCE '+tag for tag in ['LGD','SPD','PWR','AGI','MIC','REF']]
 assert sum(r[0] in base_families for r in data['rows'])==300
 specs=[]
 for family in base_families:
  if family=='BASE CARDS II':continue # Explicit alias shares the original Base odds.
  tag=family.removeprefix('PEAK PERFORMANCE ') if family.startswith('PEAK PERFORMANCE ') else None
  name='BASE FOILFRACTOR'+(' ('+tag+')' if tag else '')
  assert any(o['name']==name and o['family']==family for o in odds)
  specs.append(dict(family=family,name='FoilFractor',numbering='1/1',oddsName=name,sourceHeading='Base Set / Key Facts',qualification='Published for the 300-card base program (200 traditional base and 100 Peak Performance). No insert, autograph or relic limit is inferred; individual-card eligibility is not independently audited.',source=proof['source'],**evidence))
 table=lambda name,headers,rows:dict(name=name,headers=headers,rows=rows,source=proof['source'],worksheet='Official guide; exact card scope and source qualifications retained',**evidence)
 published=[]
 for family,number,names,parallel,statement,qualification in facts['cardExamples']:
  assert [r[2] for r in data['rows'] if r[0]==family and r[1]==number]==names,(family,number,names)
  published.append(table(family,['Card number','Name','Parallel / variation','Published statement','Qualification'],[[number,' / '.join(names),parallel,statement,qualification]]))
 counts=[]
 for family,n in facts['guideProgramSizes']:
  actual=len({r[1] for r in data['rows'] if r[0]==family});assert actual==n,(family,n,actual);counts.append([family,str(n),str(actual),'Distinct printed card numbers; multi-signer subject rows stay separate'])
 published.append(table('Official guide program sizes',['Checklist family','Guide cards','Printed card identities','Qualification'],counts))
 published.append(table('Qualified guide context',['Published statement','Qualification'],[['Danhausen’s first in-pack WWE cards','Not a printed Rookie flag; no additional Rookie field is inferred.'],['Guide publication: August 28, 2026','Article date only; general release date remains unverified.']]))
 note=('All 922 original workbook subjects / 39 families, 40 literal Rookie flags and 323 three-format odds rows are preserved. '
  'The official guide supplies seven FoilFractor 1/1 odds joins covering the 300-card base program through eight explicit source families. '
  'Six named-card examples retain exact card-number scope: Danhausen, Berto, Stephanie Vaquer, Sol Ruca/Zaria, Liv Morgan and Tiffany Stratton. '
  'Danhausen’s parallel is unnamed; no example becomes a family-wide color limit. Guide program sizes reconcile by distinct printed card identities. '
  'Raw/Smackdown/NXT/Legend/WWE are designations, not inferred teams. The odds ratio unit, general release date and exhaustive parallel eligibility remain unverified.')
 data.update(odds=odds,officialOddsTable=original,officialOddsFormats=data['formats'],officialOddsHeader=['Card',*data['formats']],oddsUnitsPublished=False,parallelSpecifications=[],publishedSpecifications=published,sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
 repair=ROOT/'data/official-source-reviews/universe-wwe-2026-odds-link-20261019-0100.json'
 data['oddsSourceReview']=dict(file=str(repair.relative_to(ROOT)),sha256=hashlib.sha256(repair.read_bytes()).hexdigest())
 rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=specs
 registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Card-specific examples and remaining numbering review',gap=' '.join(proof['remainingGaps']),source=proof['source'],**evidence)]
 rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 return data,dict(verified=proof['observed'],catalogEvidence=note,dataAudit=note,sourceObservation=dict(file=evidence['evidenceFile'],sha256=evidence['evidenceSha256'],source=proof['source']))

def build():
 cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(s for s in catalog['sets'] if s['slug']==SLUG)
 dp=ROOT/record['tableData'];data=json.loads(dp.read_text());proof=json.loads(PROOF.read_text())
 for key,suffix in [('checklist','xls'),('odds','pdf')]:
  with urllib.request.urlopen(proof[key+'Url'],timeout=45) as response:blob=response.read()
  assert hashlib.sha256(blob).hexdigest()==proof[key+'Sha256'],key+' source changed; reconcile before import'
  p=ROOT/'data/catalog-sources/downloads'/(SLUG+('-odds' if key=='odds' else '')+'.'+suffix);p.write_bytes(blob)
 data,meta=supplement(data);record.update(meta);dp.write_text(json.dumps(data,ensure_ascii=False)+'\n');cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());inventory=[record if r['slug']==SLUG else r for r in inventory];ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 print('Universe WWE: 922 subjects / 323 literal odds preserved; seven base FoilFractor joins and six isolated named-card examples reconciled. Exhaustive numbering remains incomplete.')

if __name__=='__main__':build()
