"""Preserve Manchester United Team Set physical columns and scoped guide facts."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-topps-manchester-united-2025-26-team-set';PARSER='scripts/import_topps_united_team_2025.py'
PROOF=ROOT/'data/parallel-audit-sources/manchester-united-team-2025-26-20261016.json'
FAMILIES={'FIRST TEAM':20,'BONAFIDE BALLER':5,'PITCH PURSUITS':10,'COLLECTORS CORNER':5,'UNITED ROAD':10,'RAINBOW FLICK':25,'BASE CARDS AUTOGRAPH VARIATION':32,'BONAFIDE BALLER AUTOGRAPH VARIATION':12}
def read_cards(path):
 rows=[];raw=[];family=None
 with pdfplumber.open(path) as p:
  assert len(p.pages)==3
  for pn,page in enumerate(p.pages,1):
   raw.append(dict(page=pn,text=page.extract_text()))
   groups=collections.defaultdict(list)
   for c in page.chars:groups[round(c['top'],1)].append(c)
   for y,cs in sorted(groups.items()):
    text=''.join(c['text'] for c in cs).strip()
    if all('Bold' in c['fontname'] for c in cs):assert text in FAMILIES,(pn,text);family=text;continue
    assert family,(pn,text)
    # Name, club and Rookie are separate original text objects. Keep their
    # origins rather than deriving clubs or flags from subject identities.
    starts=[next(i for i,c in enumerate(cs) if abs(c['x0']-x)<.02) for x in [132.62,269.45]]
    rookie=next((i for i,c in enumerate(cs) if abs(c['x0']-421.27)<.02),len(cs))
    a,b=starts;cells=[''.join(c['text'] for c in part).strip() for part in [cs[:a],cs[a:b],cs[b:rookie],cs[rookie:]]]
    number,name,team,mark=cells
    assert re.fullmatch(r'\d+|(?:RF|AU|BB)-[A-Z0-9]+',number),(pn,cells)
    assert name and team in {'Manchester United','Manchester United Women'} and mark in {'','Rookie'},(pn,cells)
    rows.append([family,number,name,str(pn),team,mark,''])
 assert len(rows)==119 and collections.Counter(r[0] for r in rows)==FAMILIES
 assert sum(r[5]=='Rookie' for r in rows)==9 and sum(r[4]=='Manchester United Women' for r in rows)==6
 return rows,raw

def build():
 proof=json.loads(PROOF.read_text());ph=hashlib.sha256(PROOF.read_bytes()).hexdigest();evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=ph)
 cp=ROOT/'data/set-catalog.json';cat=json.loads(cp.read_text());record=next(s for s in cat['sets'] if s['slug']==SLUG);path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
 digest=acquire(record['checklistUrl'],path);assert digest==proof['checklistSha256'];rows,raw=read_cards(path)
 example=proof['cardSpecific'];match=[r for r in rows if r[:3]==[example['family'],example['cardNumber'],example['subject']]];assert len(match)==1
 match[0][6]=example['statement']+'. '+example['qualification']+' Official UK source: '+proof['source']
 note=('All 119 physical entries across eight exact checklist sections are reconciled, with separate names, original club assignments and nine printed Rookie marks. '
       'The six Manchester United Women rows remain distinct from Manchester United; no rookie flags are propagated between subjects. '
       'All 50 numeric base entries, 25 Rainbow Flick cards, 32 Base autograph variations and 12 Bonafide Baller autograph variations are retained. '
       'Only AU-AF Sir Alex Ferguson receives the guide’s card-specific 1/1 example; no named parallel or family-wide numbering is inferred. '
       'Box contents, one autograph per two boxes and one Rainbow Flick card per case retain their published units, without invented pack odds. '
       'The UK guide announces February 12, 2026; this regional date is separate from the unverified general release date. '
       'Exhaustive parallel numbering remains unconfirmed.')
 table=lambda name,headers,values:dict(name=name,worksheet='Official UK guide',headers=headers,rows=values,source=proof['source'],**evidence)
 data=dict(title=record['title'],headers=['Checklist section','Card number','Name','Source page','Team','Rookie','Card-specific guide specification'],rows=rows,originalSubjectHeaders=['Checklist section','Card number','Name','Source page','Team','Rookie'],originalSubjectRows=[r[:6] for r in rows],source=record['checklistUrl'],sha256=digest,rawPages=raw,unclassifiedLines=[],importKind='pdf',sectionColumn=0,dedicatedParser=PARSER,coverageComplete=True,odds=[],formats=[],formatNamesPublished=False,oddsUnitsPublished=False,parallelSpecifications=[],publishedSpecifications=[table('Manufacturer configuration and distribution',['Published field','Published value','Scope'],proof['configuration']),table('Regional release evidence',['Market','Announced date','Qualification'],[['United Kingdom',proof['regionalRelease']['date'],proof['regionalRelease']['qualification']]]),table('Card-specific guide example',['Checklist family','Card number','Subject','Published statement','Qualification'],[[example['family'],example['cardNumber'],example['subject'],example['statement'],example['qualification']]])],sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
 (ROOT/record['tableData']).write_text(json.dumps(data,ensure_ascii=False)+'\n')
 record.update(rowCount=119,sections=8,sha256=digest,dedicatedParser=PARSER,coverageComplete=True,verified=proof['observed'],dataAudit=note,catalogEvidence=note,regionalReleaseEvidence={**proof['regionalRelease'],'source':proof['source'],**evidence},sourceObservation=dict(file=evidence['evidenceFile'],sha256=ph,source=proof['source']))
 assert record['releaseDate'] is None
 cp.write_text(json.dumps(cat,ensure_ascii=False,indent=2)+'\n')
 ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());inventory=[record if r['slug']==SLUG else r for r in inventory] if any(r['slug']==SLUG for r in inventory) else inventory+[record];ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=[];registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Card-specific autograph example, distribution units and regional release',gap=' '.join(proof['remainingGaps']),source=proof['source'],**evidence)];rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 print('Manchester United Team Set: 119 original entries / eight sections, nine Rookie marks, six women’s-team rows; box/case units and UK release remain scoped.')
if __name__=='__main__':build()
