"""Keep Pristine's original player/team/rookie cells and exact product limits."""
import collections, hashlib, json, re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire, text
from official_odds_layout import physical_odds_pdf

ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2025-topps-pristine-baseball'
PARSER='scripts/import_topps_pristine_2025.py'
PROOF=ROOT/'data/parallel-audit-sources/pristine-baseball-2025-20261017.json'
HEADERS=['Checklist section','Card number','Name','Source page','Team','Rookie']
FAMILIES={'BASE CARDS':300,'PERSEVERANCE':25,'PLATED AND POLISHED':40,'PRECISIONARIES':35,'PEARLESCENT':25,
 'AMPED':25,'PROWLERS':15,'MONOGRAM':30,'LETS GO':5,'PRISTINE AUTOGRAPHS':96,'PRISTINE PAIR DUAL AUTOGRAPHS':12,
 'PLATED AND POLISHED AUTOGRAPH VARIATION':20,'PRISTINE PERSONAL ENDORSEMENTS AUTOGRAPHS':32,'ITALICS':15,
 'POPULAR DEMAND AUTOGRAPH RELIC':35,'PRISTINE PIECES AUTOGRAPH RELIC':58,
 'ALL STAR GAME PRISTINE PIECES AUTOGRAPH RELIC':27,'ROOKIE JUMBO AUTOGRAPH RELICS':19}

def read_cards(path):
 rows=[];raw=[];notes=[];family=None
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==16
  for pn,page in enumerate(pdf.pages,1):
   raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
   for c in page.chars:groups[round(c['top'],1)].append(c)
   for y,cs in sorted(groups.items()):
    line=text(cs)
    if all('Bold' in c['fontname'] for c in cs):
     if line in {'BASE','INSERT','AUTOGRAPH','AUTOGRAPH RELIC'}:notes.append([str(pn),line])
     else:
      assert line in FAMILIES,(pn,line);family=line
     continue
    # Original drawing order and cell starts preserve overlapping names/teams.
    a=next(i for i,c in enumerate(cs) if abs(c['x0']-132.62)<.02)
    b=next(i for i,c in enumerate(cs) if abs(c['x0']-269.45)<.02)
    k=next((i for i,c in enumerate(cs) if abs(c['x0']-421.27)<.02),len(cs))
    number,name,team,rookie=[text(part) for part in [cs[:a],cs[a:b],cs[b:k],cs[k:]]]
    assert family and re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+',number) and name and team and rookie in {'','Rookie'},(pn,line)
    rows.append([family,number,name,str(pn),team,rookie])
 assert len(rows)==814 and len({tuple(r[:2]) for r in rows})==808
 assert collections.Counter(r[0] for r in rows)==FAMILIES and sum(r[5]=='Rookie' for r in rows)==224
 return rows,raw,notes

def build():
 proof=json.loads(PROOF.read_text());sources=proof['sources']
 evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=hashlib.sha256(PROOF.read_bytes()).hexdigest())
 cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(s for s in catalog['sets'] if s['slug']==SLUG)
 dp=ROOT/record['tableData'];data=json.loads(dp.read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
 sha=acquire(proof['checklistUrl'],path);rows,raw,notes=read_cards(path)
 op=path.with_name(SLUG+'-odds.pdf');oh=acquire(proof['oddsUrl'],op);original,formats,odds_raw,issues=physical_odds_pdf(op)
 assert (sha,oh)==(proof['checklistSha256'],proof['oddsSha256']) and len(original)==89 and formats==['FGC006155 Hobby'] and not issues
 aliases={f.title():f for f in FAMILIES}
 aliases.update({'Base':'BASE CARDS','Plated & Polished':'PLATED AND POLISHED',"Let's Go":'LETS GO',
  'Personal Endorsements Autographs':'PRISTINE PERSONAL ENDORSEMENTS AUTOGRAPHS',
  'Plated & Polished Autograph Variations':'PLATED AND POLISHED AUTOGRAPH VARIATION',
  'Popular Demand Auto Relic':'POPULAR DEMAND AUTOGRAPH RELIC','Pristine Pieces Auto Relic':'PRISTINE PIECES AUTOGRAPH RELIC',
  'All Star Game Pristine Pieces Auto Relic':'ALL STAR GAME PRISTINE PIECES AUTOGRAPH RELIC',
  'Pristine Pairs Dual Autograph':'PRISTINE PAIR DUAL AUTOGRAPHS','Rookie Jumbo Relic Auto':'ROOKIE JUMBO AUTOGRAPH RELICS'})
 odds=[]
 for item in original:
  prefix=next((a for a in sorted(aliases,key=len,reverse=True) if item['name'].casefold()==a.casefold() or item['name'].casefold().startswith(a.casefold()+' ')),None)
  assert prefix,item['name']
  odds.append(dict(item,family=aliases[prefix],familyBase=item['name'].casefold() in {prefix.casefold(),prefix.casefold()+' base set'}))
 assert {o['family'] for o in odds}==set(FAMILIES)
 specs=[dict(s,source=sources['product'],**evidence) for s in proof['guideSpecifications']]
 for spec in specs:assert any(o['name']==spec['oddsName'] and o['family']==spec['family'] for o in odds),spec
 def table(name,headers,values,source):return dict(name=name,headers=headers,rows=values,source=source,worksheet='Official product and guide evidence; preserve source units and scope',**evidence)
 published=[table('Official product box configuration',['Published item','Published value'],[r[1:] for r in proof['boxContents'] if r[0]=='Product Overview'],sources['product']),
  table('Official spotlight box configuration',['Published item','Published value'],[r[1:] for r in proof['boxContents'] if r[0]=='Official spotlight'],sources['guide']),
  table('Official product metadata',['Published field','Published value','Qualification'],[['Product Year','2026','Store metadata; printed checklist title is 2025'],['Available From','Feb 12, 2026','Store availability; distinct from the verified February 4 release statement']],sources['product']),
  table('BASE CARDS',['Parallel / variation','Published statement'],[[n,'Named in the product description; no additional numeric limit published in the checked wording'] for n in ['Aqua','Pristine Aqua','Pristine Primaries','Red','Superfractor']],sources['product'])]
 note=('All 814 physical subject rows / 808 family-card identities across 18 sections retain original Name/Team cells, 300 base numbers and 224 literal Rookie marks. '
  'All six dual cards retain both signers. Historical teams, trademarks and card-specific assignments remain unchanged. '
  'All 89 odds categories retain the literal FGC006155 Hobby header and values, including 01:16:00; no ratio unit is printed. '
  'Six product-description 1/1 terms join only Base Pristine Black, the four named short-print Superfractors and All Star Game Pristine Pieces. '
  'Other color limits are not inferred. The guide’s 10 cards per tri-pack and store’s 8 cards per pack retain their original units without choosing a corrected count. '
  'February 12 store availability and Product Year 2026 remain separate from the 2025 title and verified February 4, 2026 release. Exhaustive parallel numbering remains unverified.')
 data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,rawPages=raw,sourceDocumentNotes=notes,
  unclassifiedLines=[],source=proof['checklistUrl'],sha256=sha,dedicatedParser=PARSER,importKind='pdf',coverageComplete=True,sectionColumn=0,
  odds=odds,formats=formats,officialOddsTable=original,officialOddsFormats=formats,officialOddsHeader=['Cards',*formats],
  oddsSource=proof['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=[],oddsParser='scripts/official_odds_layout.py',
  formatNamesPublished=True,oddsUnitsPublished=False,parallelSpecifications=[],publishedSpecifications=published,
  sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
 dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
 record.update(sourcePage=sources['product'],rowCount=814,sections=18,sha256=sha,dedicatedParser=PARSER,coverageComplete=True,odds=89,formats=1,
  verified=proof['observed'],dataAudit=note,catalogEvidence=note,oddsParser='scripts/official_odds_layout.py',oddsImportIssues=0,
  sourceObservation=dict(file=evidence['evidenceFile'],sha256=evidence['evidenceSha256'],source=sources['product']))
 cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text())
 inventory=[record if r['slug']==SLUG else r for r in inventory] if any(r['slug']==SLUG for r in inventory) else inventory+[record]
 ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=specs
 registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Remaining numbering and pack configuration scope',gap=' '.join(proof['remainingGaps']),source=sources['product'],**evidence)]
 rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 print('2025 Pristine: 814 subjects / 808 identities, 18 sections, 224 Rookie marks, six duals, 89 literal Hobby odds and six exact 1/1 joins.')

if __name__=='__main__':build()
