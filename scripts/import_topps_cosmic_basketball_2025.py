"""Reconcile Cosmic Basketball's original subject cells and scoped guide evidence."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire,text
from official_odds_layout import physical_odds_pdf
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-26-topps-cosmic-chrome-basketball'
PARSER='scripts/import_topps_cosmic_basketball_2025.py';PROOF=ROOT/'data/parallel-audit-sources/cosmic-basketball-2025-26-20261016.json'
HEADERS=['Checklist section','Card number','Name','Source page','Team','Rookie']
FAMILIES={'BASE CARDS':100,'BASE CARDS II':100,'GALAXY GREATS':35,'EXTRATERRESTRIAL TALENT':25,'PROPULSION':25,'HYPER NOVA':20,'COSMIC DUST':20,'STARFRACTOR':50,'RE ENTRY':40,'GEOCENTRIC':30,'FIRST LIGHT':30,'SPACE WALK':15,'PLANETARY PURSUIT':100,'COSMIC CHROME AUTOGRAPH VARIATION':48,'SINGULARITY SIGNATURES':46,'ALIEN AUTOGRAPHS':32,'ELECTRO STATIC SIGNATURES REFRACTOR':30,'FIRST FLIGHT SIGNATURES REFRACTOR':29,'COSMIC CHROME AUTOGRAPH VARIATION II':2}

def read_cards(path):
 rows=[];raw=[];notes=[];family=None
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==16
  for pn,page in enumerate(pdf.pages,1):
   raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
   for c in page.chars:groups[round(c['top'],1)].append(c)
   for y,cs in sorted(groups.items()):
    line=text(cs)
    if pn==1 and y<149:notes.append([str(pn),line]);continue
    if all('Bold' in c['fontname'] for c in cs):
     if line not in {'BASE','INSERT','AUTOGRAPH'}:assert line in FAMILIES,(pn,line);family=line
     continue
    # Original drawing sequence preserves cells even where glyphs overlap.
    a=next(i for i,c in enumerate(cs) if abs(c['x0']-121.44)<.02)
    b=next(i for i,c in enumerate(cs) if abs(c['x0']-258.96)<.02)
    k=next((i for i,c in enumerate(cs) if abs(c['x0']-410.76)<.02),len(cs))
    number,name,team,rookie=[text(v) for v in [cs[:a],cs[a:b],cs[b:k],cs[k:]]]
    assert family and re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+',number) and name and team and rookie in {'','Rookie'},(pn,line)
    rows.append([family,number,name,str(pn),team,rookie])
 assert len(rows)==777 and collections.Counter(r[0] for r in rows)==FAMILIES
 assert sum(r[5]=='Rookie' for r in rows)==278
 return rows,raw,notes

def build():
 proof=json.loads(PROOF.read_text());sources=proof['sources'];ph=hashlib.sha256(PROOF.read_bytes()).hexdigest();evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=ph)
 cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(s for s in catalog['sets'] if s['slug']==SLUG);dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
 path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');sha=acquire(proof['checklistUrl'],path);rows,raw,notes=read_cards(path)
 op=path.with_name(SLUG+'-odds.pdf');oh=acquire(proof['oddsUrl'],op);original,formats,odds_raw,issues=physical_odds_pdf(op)
 assert (sha,oh)==(proof['checklistSha256'],proof['oddsSha256']) and len(original)==126 and formats==['Hobby'] and not issues
 aliases={f.title():f for f in FAMILIES};aliases.update({'Base':'BASE CARDS','Re-Entry':'RE ENTRY','HyperNova':'HYPER NOVA','Electro-Static Signatures':'ELECTRO STATIC SIGNATURES REFRACTOR','First Flight Signatures':'FIRST FLIGHT SIGNATURES REFRACTOR'})
 odds=[]
 for item in original:
  prefix=next((a for a in sorted(aliases,key=len,reverse=True) if item['name'].casefold()==a.casefold() or item['name'].casefold().startswith(a.casefold()+' ')),None);assert prefix,item['name']
  family=aliases[prefix];base=prefix+(' Refractor' if 'AUTOGRAPH' in family or 'SIGNATURES' in family else '')
  odd=dict(item,family=family,familyBase=item['name'].casefold()==base.casefold())
  if family=='BASE CARDS':odd['familyAliases']=['BASE CARDS II']
  odds.append(odd)
 assert set(o['family'] for o in odds)==set(FAMILIES)-{'BASE CARDS II'}
 specs=[dict(s,source=sources['guide'],**evidence) for s in proof['guideSpecifications']];assert len(specs)==51
 for spec in specs:assert any(o['name']==spec['oddsName'] and o['family']==spec['family'] for o in odds),spec
 table=lambda name,headers,values,source:dict(name=name,worksheet='Official manufacturer guide; preserve family scope and source units',headers=headers,rows=values,source=source,**evidence)
 unnumbered=[table(family,['Parallel / variation','Guide numbering statement'],[[name,'No numbering stated in the guide'] for f,name in proof['unnumberedGuideNames'] if f==family],sources['guide']) for family in dict.fromkeys(x[0] for x in proof['unnumberedGuideNames'])]
 note=('All 777 physical subject rows / 777 family-card identities across 19 sections are reconciled, with original Name/Team cells and 278 literal Rookie marks. '
       'The two 100-row base sections print number 101 twice (Nikola Jović / Darius Garland) and omit 48; original numbers, source spellings and historical team assignments remain unchanged. '
       'All 126 Hobby odds retain literal values, including Base 3:1; the sheet does not state a ratio unit. Both base sections share the exact Base odds family. '
       'The full official guide confirms April 29, 2026 release and 51 exact family numbering joins, including five Singularity Signatures limits. '
       'Guide-listed parallels without numbering remain unnumbered; the product’s /50-and-lower rare-insert statement has no individual parallel join. Exhaustive parallel coverage remains unverified.')
 data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,rawPages=raw,sourceDocumentNotes=notes,unclassifiedLines=[],sha256=sha,source=proof['checklistUrl'],dedicatedParser=PARSER,importKind='pdf',coverageComplete=True,sectionColumn=0,odds=odds,formats=formats,officialOddsTable=original,officialOddsFormats=formats,officialOddsHeader=['Card','Hobby'],oddsSource=proof['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=[],oddsParser='scripts/official_odds_layout.py',formatNamesPublished=True,oddsUnitsPublished=False,parallelSpecifications=[],publishedSpecifications=[*unnumbered,table('PLANETARY PURSUIT',['Published parallel name','Guide numbering statement'],[[n,'No numbering stated in the guide'] for n in proof['planetaryNames']],sources['guide']),table('Official guide program sizes',['Checklist family','Published size','Qualification'],proof['guideProgramSizes'],sources['guide']),table('Product-described rare insert scope',['Published program','Published statement','Qualification'],proof['productQualifications'],sources['landing'])],sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[gap] for gap in proof['remainingGaps']]])])
 dp.write_text(json.dumps(data,ensure_ascii=False)+'\n');record.update(sourcePage=sources['landing'],rowCount=777,sections=19,sha256=sha,dedicatedParser=PARSER,coverageComplete=True,odds=126,formats=1,oddsParser='scripts/official_odds_layout.py',oddsImportIssues=0,verified=proof['observed'],dataAudit=note,catalogEvidence=note,sourceObservation=dict(file=evidence['evidenceFile'],sha256=ph,source=sources['guide']));cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());inventory=[record if r['slug']==SLUG else r for r in inventory] if any(r['slug']==SLUG for r in inventory) else inventory+[record];ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=specs;registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Other numbering and qualified product scope',gap=' '.join(proof['remainingGaps']),source=sources['guide'],**evidence)];rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 print('Cosmic Basketball: 777 subjects / 19 sections / 278 Rookie flags, 126 literal Hobby odds and 51 exact guide numbering joins; release evidence retained separately.')
if __name__=='__main__':build()
