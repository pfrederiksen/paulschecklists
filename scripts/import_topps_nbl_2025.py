"""Reconcile NBL's physical Name/Team/Rookie cells and ruled odds header."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire,text
from official_odds_layout import physical_odds_pdf
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-26-topps-nbl-basketball';PARSER='scripts/import_topps_nbl_2025.py'
PROOF=ROOT/'data/parallel-audit-sources/nbl-basketball-2025-26-20261016.json'
FAMILIES={'BASE CARDS':100,'CYCLONES':25,'OOHS AND AHHS':25,'THE ROAR':20,'BIG TOPPS':30,'ATLAS':10,'NEXT STARS':4,'GLASS AND GRIT':16,'LOCALS ONLY':16,'ALL TIME GREATS AUTOGRAPH':7,'NBL AUTOGRAPHS':32,'NBL RELICS':38}
def read_cards(path):
 rows=[];raw=[];notes=[];family=None
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==8
  for pn,page in enumerate(pdf.pages,1):
   raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
   for c in page.chars:groups[round(c['top'],1)].append(c)
   for y,cs in sorted(groups.items()):
    line=text(cs)
    if pn==1 and y<110:notes.append([str(pn),line]);continue
    if all('Bold' in c['fontname'] for c in cs):
     if line not in {'BASE','INSERT','AUTOGRAPH','RELIC'}:assert line in FAMILIES,(pn,line);family=line
     continue
    assert family,(pn,line)
    # Text objects can overlap horizontally. Split at their original origins,
    # preserving draw order rather than clipping long player or team names.
    a=next(i for i,c in enumerate(cs) if abs(c['x0']-132.62)<.02)
    b=next(i for i,c in enumerate(cs) if abs(c['x0']-269.45)<.02)
    c=next((i for i,c in enumerate(cs) if abs(c['x0']-421.27)<.02),len(cs))
    number,name,team,mark=[text(part) for part in [cs[:a],cs[a:b],cs[b:c],cs[c:]]]
    assert re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+',number) and name and team and mark in {'','Rookie'},(pn,line)
    rows.append([family,number,name,str(pn),team,mark])
 assert len(rows)==323 and collections.Counter(r[0] for r in rows)==FAMILIES
 assert sum(r[5]=='Rookie' for r in rows)==18
 return rows,raw,notes

def build():
 proof=json.loads(PROOF.read_text());sources=proof['sources'];ph=hashlib.sha256(PROOF.read_bytes()).hexdigest();evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=ph)
 cp=ROOT/'data/set-catalog.json';cat=json.loads(cp.read_text());record=next(s for s in cat['sets'] if s['slug']==SLUG);dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
 record.update(checklistUrl=sources['checklist'],oddsUrl=sources['odds'])
 path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');digest=acquire(record['checklistUrl'],path);rows,raw,notes=read_cards(path)
 op=path.with_name(SLUG+'-odds.pdf');oh=acquire(record['oddsUrl'],op);original,formats,odds_raw,issues=physical_odds_pdf(op)
 assert digest==proof['checklistSha256'] and oh==proof['oddsSha256'] and len(original)==48 and formats==['Hobby SKU'] and not issues
 aliases={f:f for f in FAMILIES};aliases.update({'Base':'BASE CARDS','Glass & Grit':'GLASS AND GRIT','All-Time Greats Autographs':'ALL TIME GREATS AUTOGRAPH'})
 odds=[]
 for item in original:
  prefix=next((a for a in sorted(aliases,key=len,reverse=True) if item['name'].casefold()==a.casefold() or item['name'].casefold().startswith(a.casefold()+' ')),None)
  assert prefix,item['name']
  odds.append(dict(item,family=aliases[prefix],familyBase=item['name'].casefold()==prefix.casefold()))
 note=('All 323 physical entries across 12 sections are reconciled, retaining all 100 base numbers, separate player/team cells and 18 literal Rookie marks. '
       'Historical Melbourne Tigers remains distinct from Melbourne United, and no flags or clubs are propagated between subjects. '
       'All 48 original odds categories retain their exact Hobby SKU column and values, including Base 3:1. The source does not state a ratio unit; no pack rate is computed. '
       'Exact family mappings reconcile Base, Glass & Grit and All-Time Greats Autographs with their printed checklist headings. '
       'The product-linked documents match the original source hashes. Box contents and qualitative SSP case-hit wording retain their original scope. '
       'The June 25, 2026 U.S. store availability is separate from an unverified general release date. Exhaustive parallel numbering remains unconfirmed.')
 table=lambda name,headers,values,source:dict(name=name,worksheet='Official product specifications',headers=headers,rows=values,source=source,**evidence)
 data.update(headers=['Checklist section','Card number','Name','Source page','Team','Rookie'],rows=rows,originalSubjectHeaders=['Checklist section','Card number','Name','Source page','Team','Rookie'],originalSubjectRows=rows,source=record['checklistUrl'],sha256=digest,rawPages=raw,sourceDocumentNotes=notes,unclassifiedLines=[],importKind='pdf',sectionColumn=0,dedicatedParser=PARSER,coverageComplete=True,odds=odds,formats=formats,oddsSource=record['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=issues,oddsParser='scripts/official_odds_layout.py',officialOddsTable=original,officialOddsFormats=formats,officialOddsHeader=['Cards','Hobby SKU'],formatNamesPublished=True,oddsUnitsPublished=False,parallelSpecifications=[],publishedSpecifications=[table('Manufacturer configuration and store fields',['Published field','Published value','Scope'],proof['productFields'],sources['product']),table('Manufacturer content descriptions',['Published field','Published value','Scope'],proof['landingFields'],sources['landing'])],sourceSheets=[dict(name='Official source reconciliation',notes=[[note],[proof['guideReview']],*[[g] for g in proof['remainingGaps']]])])
 dp.write_text(json.dumps(data,ensure_ascii=False)+'\n');record.update(sourcePage=sources['landing'],rowCount=323,sections=12,sha256=digest,dedicatedParser=PARSER,coverageComplete=True,odds=48,formats=1,oddsParser=data['oddsParser'],oddsImportIssues=0,verified=proof['observed'],dataAudit=note,catalogEvidence=note,sourceObservation=dict(file=evidence['evidenceFile'],sha256=ph,source=sources['product']));assert record['releaseDate'] is None
 cp.write_text(json.dumps(cat,ensure_ascii=False,indent=2)+'\n')
 ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());inventory=[record if r['slug']==SLUG else r for r in inventory] if any(r['slug']==SLUG for r in inventory) else inventory+[record];ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=[];registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Parallel numbering, ratio units and store availability',gap=' '.join(proof['remainingGaps']),source=sources['product'],**evidence)];rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 print('NBL: 323 original entries / 12 sections, 18 Rookie marks, 48 literal Hobby SKU odds; ratio units, general release and parallel numbering remain unverified.')
if __name__=='__main__':build()
