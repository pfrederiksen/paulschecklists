"""Reconcile Signature Class physical cells, colored odds columns and education ladders."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire,text
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-26-topps-signature-class-basketball';PARSER='scripts/import_topps_signature_basketball_2025.py'
PROOF=ROOT/'data/parallel-audit-sources/signature-class-basketball-2025-26-20261016.json'
FORMATS=['Odds Hobby:','Odds Hobby Jumbo:','Odds Value Box:','Odds Mega Box:']
FAMILIES={'BASE CARDS I':99,'BASE CARDS II':49,'BASE CARDS I CHROME VARIATION':100,'BASE CARDS II CHROME VARIATION':50,'AFTER IMAGE':25,'HIGH FIDELITY':30,'PURE':25,'UNFAZED':20,'STAR CAST':25,'ALGORITHM':25,'ROSES':25,'ARISTOCRATS':20,'MONARCHS OF THE GAME':30,'FLUIDITY':20,'LEVIATHANS':20,'ODYSSEY':20,'PRESSURE POINTS':10,'BASE VETERAN CLASS AUTOGRAPHS':46,'BASE VETERAN CLASS CHROME AUTOGRAPHS':46,'VETERAN CLASS CRYSTAL CLEAR AUTOGRAPHS':37,'BASE ROOKIE CLASS AUTOGRAPHS':46,'BASE ROOKIE CLASS CHROME AUTOGRAPHS':46,'ROOKIE CLASS CRYSTAL CLEAR AUTOGRAPHS':45,'LEGENDS OF THEIR CLASS CRYSTAL CLEAR AUTOGRAPHS':10,'SIGNATURE BLEND':25,'SHADOW SCRIPTS':25,'PENSTROKE SIGNATURES':29,'ETERNAL MARKS':19,'MANUSCRIPTS':70,'DUAL AUTOGRAPHS':30,'TRIPLE AUTOGRAPHS':30}
def read_cards(path):
 rows=[];raw=[];notes=[];packaging=[];family=None
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==23
  for pn,page in enumerate(pdf.pages,1):
   raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
   for c in page.chars:groups[round(c['top'],1)].append(c)
   for y,cs in sorted(groups.items()):
    line=text(cs)
    if pn==1 and y<80:notes.append([str(pn),line]);continue
    if all('Bold' in c['fontname'] for c in cs):
     if line not in {'BASE','INSERT','AUTOGRAPH'}:
      assert line in FAMILIES or line in {'PACKAGING','SELL SHEET'},(pn,line);family=line
     continue
    assert family,(pn,line)
    a=next(i for i,c in enumerate(cs) if abs(c['x0']-133.34)<.02);b=next(i for i,c in enumerate(cs) if abs(c['x0']-270.89)<.02);k=next((i for i,c in enumerate(cs) if abs(c['x0']-422.71)<.02),len(cs))
    number,name,team,mark=[text(part) for part in [cs[:a],cs[a:b],cs[b:k],cs[k:]]]
    if family=='PACKAGING':assert not number and not mark;packaging.append([name,team,str(pn)]);continue
    assert re.fullmatch(r'\d+|[A-Z]+-[A-Za-z0-9]+',number) and name and team and mark in {'','Rookie'},(pn,line)
    rows.append([family,number,name,str(pn),team,mark])
 assert len(rows)==1097 and collections.Counter(r[0] for r in rows)==FAMILIES and sum(r[5]=='Rookie' for r in rows)==439 and len(packaging)==4
 return rows,raw,notes,packaging

def read_odds(path):
 rows=[];raw=[];exceptions=[]
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==5
  for pn,page in enumerate(pdf.pages,1):
   raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
   # The four colored rectangles are the original format columns, even where
   # their backgrounds overlap by .69pt. All glyph origins lie unambiguously inside.
   assert len(page.rects)==4
   assert [(round(r['x0'],2),round(r['x1'],2)) for r in page.rects]==[(287.73,342.24),(341.55,423.66),(422.97,491.97),(491.28,560.28)]
   for c in page.chars:groups[round(c['matrix'][5],2)].append(c)
   for baseline,cs in sorted(groups.items(),reverse=True):
    cells=[[c for c in cs if left<=c['x0']<right] for left,right in [(0,287),(287,342),(342,423),(423,491),(491,612)]]
    values=[text(cell) for cell in cells]
    if pn==1 and baseline>656.77:continue
    if pn==1 and abs(baseline-656.76)<.02:assert values==['Subset:',*FORMATS];continue
    assert values[0] and any(values[1:]) and all(not v or re.fullmatch(r'[\d,.]+(?::[\d,.]+)*',v) for v in values[1:]),(pn,values)
    row=dict(name=values[0],values=dict(zip(FORMATS,[v or None for v in values[1:]])),page=pn);rows.append(row)
    for fmt,cell,value in zip(FORMATS,cells[1:],values[1:]):
     if value and ':' not in value:
      box=lambda chars:[min(c['x0'] for c in chars)-.001,min(c['top'] for c in chars)-.001,max(c['x1'] for c in chars)+.001,max(c['bottom'] for c in chars)+.001]
      exceptions.append(dict(page=pn,name=values[0],format=fmt,value=value,nameBox=box(cells[0]),valueBox=box(cell)))
 assert len(rows)==199 and len(exceptions)==1 and exceptions[0]['value']=='2.1'
 return rows,raw,exceptions

def build():
 proof=json.loads(PROOF.read_text());sources=proof['sources'];ph=hashlib.sha256(PROOF.read_bytes()).hexdigest();evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=ph)
 cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(r for r in catalog['sets'] if r['slug']==SLUG);dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
 path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');digest=acquire(record['checklistUrl'],path);rows,raw,notes,packaging=read_cards(path)
 op=path.with_name(SLUG+'-odds.pdf');oh=acquire(record['oddsUrl'],op);original,odds_raw,exceptions=read_odds(op)
 eh=acquire(sources['education'],ROOT/proof['educationFile']);assert (digest,oh,eh)==(proof['checklistSha256'],proof['oddsSha256'],proof['educationSha256'])
 aliases={f.title():f for f in FAMILIES};aliases.update({'Veteran Class Base':'BASE CARDS I','Rookie Class Base':'BASE CARDS II','Veteran Class Chrome Base':'BASE CARDS I CHROME VARIATION','Rookie Class Chrome Base':'BASE CARDS II CHROME VARIATION','Veteran Class Autographs':'BASE VETERAN CLASS AUTOGRAPHS','Rookie Class Autographs':'BASE ROOKIE CLASS AUTOGRAPHS','Veteran Class Chrome Autographs':'BASE VETERAN CLASS CHROME AUTOGRAPHS','Rookie Class Chrome Autographs':'BASE ROOKIE CLASS CHROME AUTOGRAPHS','Aristocrat':'ARISTOCRATS'})
 odds=[];prefixes={}
 for item in original:
  prefix=next((a for a in sorted(aliases,key=len,reverse=True) if item['name'].casefold()==a.casefold() or item['name'].casefold().startswith(a.casefold()+' ')),None);assert prefix,item['name']
  odds.append(dict(item,family=aliases[prefix],familyBase=item['name'].casefold()==prefix.casefold()));prefixes[item['name']]=prefix
 specs=[]
 for item in odds:
  family=item['family'];kind='paper' if family in {'BASE CARDS I','BASE CARDS II'} else 'chrome' if family in {'BASE CARDS I CHROME VARIATION','BASE CARDS II CHROME VARIATION'} else 'crystal' if 'CRYSTAL CLEAR AUTOGRAPHS' in family else None
  if not kind:continue
  suffix=item['name'][len(prefixes[item['name']]):].strip() or 'Base';terms=dict(proof['educationParallelTables'][kind]);assert suffix in terms,(kind,suffix)
  limit=terms[suffix];numbering='Not serial-numbered (published)' if limit=="Non-#'d" else '1/1' if limit=='/1' else limit
  specs.append(dict(family=family,name=suffix,numbering=numbering,oddsName=item['name'],qualification=f'Education sheet page 2: {kind} ladder only; never applied to other insert or autograph families. Original printed value: /{limit}' if limit=="Non-#'d" else f'Education sheet page 2: {kind} ladder only; never applied to other insert or autograph families.',source=sources['education'],**evidence))
 assert len(specs)==79
 table=lambda name,headers,values,source:dict(name=name,worksheet='Official product specifications',headers=headers,rows=values,source=source,**evidence)
 note=('All 1,097 numbered subject rows across 31 sections are reconciled with separate Name/Team cells and 439 literal Rookie marks. '
       'Paper has 148 numbers (68 and 150 absent), while Chrome has all 150; no missing subjects are invented. Four unnumbered packaging subjects are retained separately. '
       'All 199 odds categories retain four literal format headings and original cells, including Rookie Class Base Hobby Jumbo 2.1. The headers do not state a ratio unit; no pack rate is computed. '
       'The education sheet supplies 79 exact paper base, Chrome base and Crystal Clear parallel terms, including explicitly unnumbered cards. These limits do not apply to other autograph or insert programs. '
       'The guide describes 25 Aristocrats subjects but the checklist prints 20; the discrepancy remains explicit. Other parallel ladders and a general release date remain unverified.')
 data.update(headers=['Checklist section','Card number','Name','Source page','Team','Rookie'],rows=rows,originalSubjectHeaders=['Checklist section','Card number','Name','Source page','Team','Rookie'],originalSubjectRows=rows,source=record['checklistUrl'],sha256=digest,rawPages=raw,sourceDocumentNotes=notes,unclassifiedLines=[],importKind='pdf',sectionColumn=0,dedicatedParser=PARSER,coverageComplete=True,odds=odds,formats=FORMATS,oddsSource=record['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=[],oddsParser=PARSER,officialOddsTable=original,officialOddsFormats=FORMATS,officialOddsHeader=['Subset:',*FORMATS],oddsLiteralExceptions=exceptions,formatNamesPublished=True,oddsUnitsPublished=False,parallelSpecifications=[],publishedSpecifications=[table('Official box configuration',['Published format','Published contents','Scope'],proof['configuration'],sources['education']),table('Official distribution terms',['Published family','Published scope'],proof['distribution'],sources['education']),table('Official guide descriptions and discrepancies',['Published subject','Published description','Qualification'],proof['guideFacts'],sources['guide']),table('Unnumbered packaging subjects',['Name','Team','Source page'],packaging,sources['checklist'])],sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[gap] for gap in proof['remainingGaps']]])])
 dp.write_text(json.dumps(data,ensure_ascii=False)+'\n');record.update(sourcePage=sources['landing'],rowCount=len(rows),sections=31,sha256=digest,dedicatedParser=PARSER,coverageComplete=True,odds=199,formats=4,oddsParser=PARSER,oddsImportIssues=0,verified=proof['observed'],dataAudit=note,catalogEvidence=note,sourceObservation=dict(file=evidence['evidenceFile'],sha256=ph,source=sources['education']));assert record['releaseDate'] is None
 cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());inventory=[record if r['slug']==SLUG else r for r in inventory] if any(r['slug']==SLUG for r in inventory) else inventory+[record];ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=specs;registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Other parallel numbering, source omissions and release date',gap=' '.join(proof['remainingGaps']),source=sources['education'],**evidence)];rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 print('Signature Class: 1,097 original rows / 31 families / 439 Rookie marks, 199 literal four-column odds and 79 education terms; remaining discrepancies and numbering gaps retained.')
if __name__=='__main__':build()
