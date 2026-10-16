"""Reconcile Bowman’s Best original subject cells, literal Hobby odds and exact guide joins."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire,text
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-bowman-s-best-baseball';PARSER='scripts/import_bowmans_best_2025.py';PROOF=ROOT/'data/parallel-audit-sources/bowmans-best-baseball-2025-20261016.json'
FAMILIES={'BASE CARDS':100,'2025 MLB ALL STAR FUTURES GAME':20,'PIXEL PORTRAITS':25,'CIRCUITRY':25,'BEST PERFORMANCES':30,'STROKES OF GOLD':25,'BOWMAN SHOWPIECES':15,'BEST TEK':30,'BEST OF 2025 AUTOGRAPHS':131,'BEST MIX AUTOGRAPHS':52,'BEST PERFORMANCE AUTOGRAPHS':20,'BEST TEK AUTOGRAPHS':20,'DUAL AUTOGRAPHS':40,'TRIPLE AUTOGRAPHS':51,'QUAD AUTOGRAPHS':52,'FAMILY TREE TRIPLE AUTOGRAPHS':6,'FAMILY TREE DUAL AUTOGRAPHS':12,'BOWMAN SHOWPIECES AUTOGRAPHS':8,'CIRCUITRY AUTOGRAPHS':9,'PROSPECT PATCH AUTOGRAPHS':26}
def read_cards(path):
 rows=[];original=[];raw=[];notes=[];family=None
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==15
  for pn,page in enumerate(pdf.pages,1):
   raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
   for c in page.chars:groups[round(c['top'],1)].append(c)
   for y,cs in sorted(groups.items()):
    line=text(cs)
    if line in {"2025 Bowman's Best Baseball Checklist",'*Subject to Change'}:notes.append([str(pn),line]);continue
    if all('Bold' in c['fontname'] for c in cs):
     if line not in {'BASE','INSERT','AUTOGRAPH','AUTOGRAPH RELIC'}:assert line in FAMILIES,(pn,line);family=line
     continue
    assert family,(pn,line)
    a=next(i for i,c in enumerate(cs) if abs(c['x0']-133.34)<.02);b=next(i for i,c in enumerate(cs) if abs(c['x0']-270.89)<.02);k=next((i for i,c in enumerate(cs) if abs(c['x0']-422.71)<.02),len(cs))
    number,name,designation,rookie=[text(part) for part in [cs[:a],cs[a:b],cs[b:k],cs[k:]]]
    # Unicode letters are printed in B25-ÉP. Never derive or replace the code.
    assert number and not re.search(r'\s',number) and name and designation and rookie in {'','Rookie'},(pn,line)
    original.append([family,number,name,str(pn),designation,rookie])
    league=designation if family=='2025 MLB ALL STAR FUTURES GAME' else '';assert not league or league in {'NATIONAL LEAGUE','AMERICAN LEAGUE'}
    rows.append([family,number,name,str(pn),'' if league else designation,rookie,league])
 assert len(rows)==697 and collections.Counter(r[0] for r in rows)==FAMILIES and sum(r[5]=='Rookie' for r in rows)==123 and len({tuple(r[:2]) for r in rows})==594
 return rows,original,raw,notes

def read_odds(path):
 odds=[];raw=[]
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==2
  for pn,page in enumerate(pdf.pages,1):
   assert page.width==1224;raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
   for c in page.chars:groups[round(c['top'],1)].append(c)
   for y,cs in sorted(groups.items()):
    label=text([c for c in cs if c['x0']<1100]);value=text([c for c in cs if c['x0']>=1100])
    if value=='HOBBY':assert label=="2025 Bowman's Best Baseball Odds";continue
    if not value:assert label in {"2025 Bowman's Best Baseball",'SUBJECT TO CHANGE'},(pn,label);continue
    assert label and re.fullmatch(r'[\d,]+:[\d,]+',value),(pn,label,value)
    assert abs(min(c['x0'] for c in cs)-14.2)<.02 and abs(max(c['x1'] for c in cs)-1209.8)<.02
    odds.append(dict(name=label,values={'HOBBY':value},page=pn))
 assert len(odds)==107
 return odds,raw

def build():
 proof=json.loads(PROOF.read_text());sources=proof['sources'];ph=hashlib.sha256(PROOF.read_bytes()).hexdigest();evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=ph)
 cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(r for r in catalog['sets'] if r['slug']==SLUG);dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
 path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');sha=acquire(record['checklistUrl'],path);rows,original_rows,raw,notes=read_cards(path)
 op=path.with_name(SLUG+'-odds.pdf');oh=acquire(record['oddsUrl'],op);original_odds,odds_raw=read_odds(op);assert (sha,oh)==(proof['checklistSha256'],proof['oddsSha256'])
 aliases={f.title():f for f in FAMILIES};aliases.update({'Base Cards':'BASE CARDS','2025 MLB All-Star Futures Game':'2025 MLB ALL STAR FUTURES GAME','Best Performance':'BEST PERFORMANCES','Best-Tek':'BEST TEK','Best-Tek Autographs':'BEST TEK AUTOGRAPHS','Prospect Patch Autograph':'PROSPECT PATCH AUTOGRAPHS','Best Mix Autograph Diecuts':'BEST MIX AUTOGRAPHS'})
 odds=[]
 for item in original_odds:
  prefix=next((a for a in sorted(aliases,key=len,reverse=True) if item['name'].casefold()==a.casefold() or item['name'].casefold().startswith(a.casefold()+' ')),None);assert prefix,item['name']
  odds.append(dict(item,family=aliases[prefix],familyBase=item['name'].casefold()==prefix.casefold()))
 specs=[dict(s,source=sources['guide'],**evidence) for s in proof['guideSpecifications']];assert len(specs)==53
 for spec in specs:
  if spec.get('oddsName'):assert any(o['name']==spec['oddsName'] and o['family']==spec['family'] for o in odds),spec
 table=lambda name,headers,values,source:dict(name=name,worksheet='Official product guide',headers=headers,rows=values,source=source,**evidence)
 distributions=[table(family,['Parallel / variation','Published distribution','Scope'],[[name,value,'Manufacturer guide; retain the published pack, box or case unit'] for f,name,value in proof['guideDistribution'] if f==family],sources['guide']) for family in dict.fromkeys(x[0] for x in proof['guideDistribution'])]
 note=('All 697 physical subject rows / 594 family-card identities across 20 sections are reconciled, retaining 123 literal Rookie marks, original names and team trademarks. '
       'The year-leading 2025 MLB ALL STAR FUTURES GAME heading is a caption, not card 2025; its 20 National/American League values remain league designations, not teams. '
       'Previously omitted B25-ÉP Émilien Pitre is restored with its original accented code, keeping the net row count unchanged. All repeated dual, triple, quad and Family Tree subjects remain separate. '
       'All 107 odds categories retain the literal HOBBY header and values, including Best of 2025 Autographs 1:07. No ratio unit is printed. '
       'All 53 reviewed guide numbering statements are retained with exact scope; Lazer /350 now joins Base Cards Lazer without a duplicate specification-only category. '
       'Guide pack, box and case distributions retain their separate units. The Refractor limit of 500 has no stated serial marking; Sterling-Tek and Strokes of Gold named parallels remain guide-only. '
       'The guide describes 50 Best Mix players but the PDF publishes 52 entries. Exhaustive parallel numbering and general release date remain unverified.')
 data.update(headers=['Checklist section','Card number','Name','Source page','Team','Rookie','Published league designation'],rows=rows,originalSubjectHeaders=['Checklist section','Card number','Name','Source page','Team / league designation','Rookie'],originalSubjectRows=original_rows,source=record['checklistUrl'],sha256=sha,rawPages=raw,sourceDocumentNotes=notes,unclassifiedLines=[],importKind='pdf',sectionColumn=0,dedicatedParser=PARSER,coverageComplete=True,odds=odds,formats=['HOBBY'],oddsSource=record['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=[],oddsParser=PARSER,officialOddsTable=original_odds,officialOddsFormats=['HOBBY'],officialOddsHeader=["2025 Bowman's Best Baseball Odds",'HOBBY'],formatNamesPublished=True,oddsUnitsPublished=False,parallelSpecifications=[],publishedSpecifications=[*distributions,table('Official guide program sizes',['Checklist family','Published size','Qualification'],proof['guideProgramSizes'],sources['guide'])],sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[gap] for gap in proof['remainingGaps']]])])
 dp.write_text(json.dumps(data,ensure_ascii=False)+'\n');record.update(sourcePage=sources['landing'],rowCount=697,sections=20,sha256=sha,dedicatedParser=PARSER,coverageComplete=True,odds=107,formats=1,oddsParser=PARSER,oddsImportIssues=0,verified=proof['observed'],dataAudit=note,catalogEvidence=note,sourceObservation=dict(file=evidence['evidenceFile'],sha256=ph,source=sources['guide']));assert record['releaseDate'] is None
 cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n');ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());inventory=[record if r['slug']==SLUG else r for r in inventory] if any(r['slug']==SLUG for r in inventory) else inventory+[record];ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=specs;registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Guide-only programs, other numbering and general release date',gap=' '.join(proof['remainingGaps']),source=sources['guide'],**evidence)];rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 print('Bowman’s Best: 697 original subjects / 594 identities / 123 Rookie marks, 107 literal Hobby odds, 53 scoped guide terms and separate league designations; unverified fields remain explicit.')
if __name__=='__main__':build()
