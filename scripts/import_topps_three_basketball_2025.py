"""Retain Three Basketball's physical subject cells and overlapping odds text."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire,text
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-26-topps-three-basketball'
PARSER='scripts/import_topps_three_basketball_2025.py'
PROOF=ROOT/'data/parallel-audit-sources/three-basketball-2025-26-physical-20261017.json'
HEADERS=['Checklist section','Card number','Name','Source page','Team']
FAMILIES={'BASE CARDS':100,'ICE WATER':40,'FLIGHT PATH':30,'ARCHITECTS':30,'3 AND D':40,'MONSTERS OF THE DEEP':30,'THE PAINT':30,
 'ROOKIE 3 PATCH AUTOGRAPHS HORIZONTAL':40,'ROOKIE 3 PATCH AUTOGRAPHS VERTICAL':40,'RELICS AUTOGRAPHS PRIME':20,
 'TRIPLE RELICS AUTOGRAPHS':51,'ROOKIE RELICS AUTOGRAPHS':40,'VETERAN 3 PATCH AUTOGRAPHS':71,'FRESH FORCE RELIC AUTOGRAPHS':40,
 'RAINDROPS SIGNATURES':48,'SERENDIPITOUS SIGS':44,'REMARKABLE':41,'FULL COURT SIGNS':40,'HIT THE MARK':41,
 'TRIPLE POWER AUTOGRAPHS':46,'ROOKIE AUTOGRAPHS':40,'THUNDERDUNK SIGNATURES':54,'ROOKIEVERSE AUTOGRAPHS':40,
 'RIM REAPERS SIGNATURES':37,'QUEST FOR GLORY AUTOGRAPHS':30,'CITY DRIP SIGNATURES':28,'NEXT FEATURE SIGNATURES':31,'GAME TIME GRAPHS':49}
FORMATS=['Hobby','FDI']

def read_cards(path):
 rows=[];raw=[];notes=[];family=None
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==24
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
    a=next(i for i,c in enumerate(cs) if abs(c['x0']-132.62)<.02)
    b=next(i for i,c in enumerate(cs) if abs(c['x0']-269.45)<.02)
    number,name,team=[text(part) for part in [cs[:a],cs[a:b],cs[b:]]]
    assert family and re.fullmatch(r'\d+|[A-Za-z0-9]+-[A-Za-z0-9]+',number) and name and team,(pn,line)
    rows.append([family,number,name,str(pn),team])
 assert len(rows)==1171 and len({tuple(r[:2]) for r in rows})==1137
 assert collections.Counter(r[0] for r in rows)==FAMILIES
 return rows,raw,notes

def read_odds(path):
 odds=[];raw=[]
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==4
  for pn,page in enumerate(pdf.pages,1):
   raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
   for c in page.chars:groups[round(c['top'],1)].append(c)
   for y,cs in sorted(groups.items()):
    if text(cs)=='SubsetsHobbyFDI':
     assert pn==1;continue
    # Long captions overlap the first value. Original object order separates
    # them; letters at a value's x origin are still part of the caption.
    starts=[(i,c['x0']) for i,c in enumerate(cs) if c['text'].isdigit() and any(abs(c['x0']-origin)<.02 for origin in [289.01,366.67])]
    assert starts,(pn,y,text(cs));name=text(cs[:starts[0][0]]);values=dict.fromkeys(FORMATS)
    for j,(i,x) in enumerate(starts):
     value=text(cs[i:starts[j+1][0] if j+1<len(starts) else len(cs)])
     assert re.fullmatch(r'[\d,]+:[\d,]+',value),(pn,name,value)
     fmt='Hobby' if abs(x-289.01)<.02 else 'FDI';assert values[fmt] is None;values[fmt]=value
    assert name;odds.append(dict(name=name,values=values,page=pn))
 assert len(odds)==154 and sum(sum(v is not None for v in o['values'].values()) for o in odds)==304
 return odds,raw

def build():
 proof=json.loads(PROOF.read_text());sources=proof['sources'];evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=hashlib.sha256(PROOF.read_bytes()).hexdigest())
 cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(s for s in catalog['sets'] if s['slug']==SLUG)
 dp=ROOT/record['tableData'];data=json.loads(dp.read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
 sha=acquire(proof['checklistUrl'],path);rows,raw,notes=read_cards(path)
 op=path.with_name(SLUG+'-odds.pdf');oh=acquire(proof['oddsUrl'],op);original,odds_raw=read_odds(op)
 assert (sha,oh)==(proof['checklistSha256'],proof['oddsSha256'])
 aliases={f.title():f for f in FAMILIES};aliases.update({'Base':'BASE CARDS','Re-Markable':'REMARKABLE','Rookie-verse Autographs':'ROOKIEVERSE AUTOGRAPHS'})
 odds=[]
 for item in original:
  prefix=next((a for a in sorted(aliases,key=len,reverse=True) if item['name'].casefold()==a.casefold() or item['name'].casefold().startswith(a.casefold()+' ')),None)
  assert prefix,item['name'];odds.append(dict(item,family=aliases[prefix],familyBase=item['name'].casefold()==prefix.casefold()))
 assert {o['family'] for o in odds}==set(FAMILIES)
 table=lambda name,headers,values,source:dict(name=name,headers=headers,rows=values,source=source,worksheet='Official manufacturer evidence; retain exact card scope and source units',**evidence)
 published=[]
 for family in dict.fromkeys(r[0] for r in proof['cardExamples']):
  values=[r[1:] for r in proof['cardExamples'] if r[0]==family]
  for r in values:assert any(row[0]==family and row[1]==r[0] and row[2]==r[1] for row in rows),r
  published.append(table(family,['Card number','Name','Parallel / variation','Published statement','Qualification'],values,sources['guide']))
 published.append(table('Official box configuration',['Published item','Published quantity','Unit / qualification'],[['Autographs or autograph relics','3','Per box; not category odds'],['Insert or base card','1','Per box; not category odds']],sources['landing']))
 published.append(table('Qualified brand-history numbering statement',['Published statement','Qualification'],[[proof['historyStatement'],'Multi-year brand-history description; no exact 2025–26 family or parallel ladder is identified. Do not apply /49 to individual categories or cards.']],sources['history']))
 note=('All 1,171 physical subjects / 1,137 family-card identities across 28 sections retain original Name/Team cells and all 100 base numbers. '
  '3 AND D is a heading, not a card; all 17 triple relic cards retain three subjects each. The PDF publishes no Rookie column. '
  'All 154 Hobby/FDI odds retain 304 literal values and four genuinely blank Hobby cells. Original text-object origins recover six truncated captions and three lost Hobby values. '
  'Re-Markable and Rookie-verse have exact source-family aliases. Seven official guide examples are reconciled to exact cards, without a family-wide numbering ladder. '
  'The guide names a Superfractor for TD-LJ, not the odds sheet’s Platinum category. Other unnamed parallels stay unnamed. '
  'March 5, 2026 release evidence is retained separately from the 2025–26 title. Exhaustive parallel numbering remains unverified.')
 data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,rawPages=raw,sourceDocumentNotes=notes,
  unclassifiedLines=[],source=proof['checklistUrl'],sha256=sha,dedicatedParser=PARSER,importKind='pdf',coverageComplete=True,sectionColumn=0,
  odds=odds,formats=FORMATS,officialOddsTable=original,officialOddsFormats=FORMATS,officialOddsHeader=['Subsets',*FORMATS],
  oddsSource=proof['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=[],oddsParser=PARSER,
  formatNamesPublished=True,oddsUnitsPublished=False,parallelSpecifications=[],publishedSpecifications=published,
  sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
 dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
 record.update(sourcePage=sources['landing'],rowCount=1171,sections=28,sha256=sha,dedicatedParser=PARSER,coverageComplete=True,odds=154,formats=2,
  verified=proof['observed'],dataAudit=note,catalogEvidence=note,oddsParser=PARSER,oddsImportIssues=0,
  sourceObservation=dict(file=evidence['evidenceFile'],sha256=evidence['evidenceSha256'],source=sources['guide']))
 cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());inventory=[record if r['slug']==SLUG else r for r in inventory] if any(r['slug']==SLUG for r in inventory) else inventory+[record]
 ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=[]
 registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Card-specific examples reconciled; remaining numbering review',gap=' '.join(proof['remainingGaps']),source=sources['guide'],**evidence)]
 rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 print('Three Basketball: 1,171 physical subjects / 28 sections, 17 complete triples, seven exact card examples and 154 two-column odds / 304 literal values; no inferred Rookie flags or family-wide limits.')

if __name__=='__main__':build()
