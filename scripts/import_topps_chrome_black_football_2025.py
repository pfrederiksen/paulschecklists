"""Reconcile Chrome Black Football's original subject cells and exact odds families."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire,text
from official_odds_layout import physical_odds_pdf,UnsupportedOddsLayout
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-topps-chrome-black-football'
PARSER='scripts/import_topps_chrome_black_football_2025.py'
PROOF=ROOT/'data/parallel-audit-sources/chrome-black-football-2025-20261016.json'
HEADERS=['Checklist section','Card number','Name','Source page','Team','Rookie']
FAMILIES={'BASE CARDS':100,'ROOKIES':50,'ROOKIES DESIGN VARIATION':30,'BLACK LIGHTNING':25,'HIT THE LIGHTS':25,
 'NOCTURNAL':20,'DEPTHS OF DARKNESS':20,'AUTOGRAPH CARDS':59,'ROOKIES AUTOGRAPHS':40,'IVORY AUTOGRAPHS':34,
 'SUPER FUTURES AUTOGRAPHS':38,'PITCH BLACK PAIRINGS DUAL AUTOGRAPHS':34}

def read_cards(path):
 rows=[];raw=[];notes=[];family=None
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==7
  for pn,page in enumerate(pdf.pages,1):
   raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
   for c in page.chars:groups[round(c['top'],2)].append(c)
   for y,cs in sorted(groups.items()):
    line=text(cs)
    if line.startswith(('Checklists provided','of production')):
     notes.append([str(pn),line]);continue
    if all('Bold' in c['fontname'] for c in cs):
     if line in {'BASE','INSERT','AUTOGRAPH'}:notes.append([str(pn),line])
     else:
      assert line in FAMILIES,(pn,line);family=line
     continue
    # Read original drawing order at cell origins: long names/teams can overlap.
    a=next(i for i,c in enumerate(cs) if abs(c['x0']-94.5)<.02)
    b=next(i for i,c in enumerate(cs) if abs(c['x0']-191.25)<.02)
    r=next((i for i,c in enumerate(cs) if abs(c['x0']-298.5)<.02),len(cs))
    number,name,team,rookie=[text(part) for part in [cs[:a],cs[a:b],cs[b:r],cs[r:]]]
    assert family and re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+',number) and name and team and rookie in {'','Rookie'},(pn,line)
    rows.append([family,number,name,str(pn),team,rookie])
 assert len(rows)==475 and len({tuple(r[:2]) for r in rows})==458 and sum(r[5]=='Rookie' for r in rows)==189
 assert collections.Counter(r[0] for r in rows)==FAMILIES
 return rows,raw,notes

def read_odds(path):
 try:
  return physical_odds_pdf(path)
 except UnsupportedOddsLayout:
  pass
 odds=[];raw=[]
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==3
  for pn,page in enumerate(pdf.pages,1):
   raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
   for c in page.chars:groups[round(c['top'],1)].append(c)
   header=False
   for y,cs in sorted(groups.items()):
    line=text(cs)
    if line=='CardHobby':
     assert not header;header=True;continue
    if not header:continue
    name=text([c for c in cs if c['x0']<350]);value=text([c for c in cs if c['x0']>=350])
    assert name and re.fullmatch(r'\d+:[\d,]+',value),(pn,y,line)
    assert all(388<c['x0']<438 for c in cs if c['x0']>=350),(pn,line)
    odds.append(dict(name=name,values={'Hobby':value},page=pn))
   assert header
 assert len(odds)==84
 return odds,['Hobby'],raw,[]

def build():
 proof=json.loads(PROOF.read_text());sources=proof['sources']
 evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=hashlib.sha256(PROOF.read_bytes()).hexdigest())
 cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(s for s in catalog['sets'] if s['slug']==SLUG)
 dp=ROOT/record['tableData'];data=json.loads(dp.read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
 sha=acquire(proof['checklistUrl'],path);rows,raw,notes=read_cards(path)
 op=path.with_name(SLUG+'-odds.pdf');oh=acquire(proof['oddsUrl'],op);original,formats,odds_raw,issues=read_odds(op)
 assert (sha,oh)==(proof['checklistSha256'],proof['oddsSha256']) and len(original)==84 and formats==['Hobby'] and not issues
 assert acquire(proof['productOddsUrl'],path.with_name(SLUG+'-product-odds.pdf'))==oh
 aliases={f.title():f for f in FAMILIES};aliases.update({'Base':'BASE CARDS','Rookie':'ROOKIES',
  'Rookie Design Variation':'ROOKIES DESIGN VARIATION','Autographs':'AUTOGRAPH CARDS','Rookie Autographs':'ROOKIES AUTOGRAPHS',
  'Ivory Autos':'IVORY AUTOGRAPHS','Super Futures Autos':'SUPER FUTURES AUTOGRAPHS',
  'Pitch Black Pairings Dual Autos':'PITCH BLACK PAIRINGS DUAL AUTOGRAPHS'})
 odds=[]
 for item in original:
  prefix=next((a for a in sorted(aliases,key=len,reverse=True) if item['name'].casefold()==a.casefold() or item['name'].casefold().startswith(a.casefold()+' ')),None)
  assert prefix,item['name'];odds.append(dict(item,family=aliases[prefix],familyBase=item['name'].casefold() in {prefix.casefold(),(prefix+' Refractor').casefold()}))
 assert {o['family'] for o in odds}==set(FAMILIES)
 def table(name,headers,values,source):
  return dict(name=name,headers=headers,rows=values,source=source,worksheet='Official manufacturer evidence; preserve exact card scope',**evidence)
 published=[]
 for family in dict.fromkeys(r[0] for r in proof['cardExamples']):
  values=[r[1:] for r in proof['cardExamples'] if r[0]==family]
  for r in values:assert any(row[0]==family and row[1]==r[0] for row in rows),r
  published.append(table(family,['Card number','Name','Parallel / variation','Published statement','Qualification'],values,sources['pulls']))
 published.append(table('ROOKIES AUTOGRAPHS',['Card number','Name','Parallel / variation','Published statement','Qualification'],proof['unnamedExample'],sources['launch']))
 published.append(table('Manufacturer product fields',['Published field','Published value','Scope'],proof['productFields'],sources['product']))
 note=('All 475 physical subject rows / 458 family-card identities across 12 sections retain original Name/Team/Rookie cells, '
  '150 numeric base entries, 189 literal Rookie marks and both signers on 17 dual cards. '
  'Historical team names, original spellings and card-specific blank Rookie cells are preserved. '
  'All 84 Hobby odds retain literal values, including Base 3:1 and Rookie 2:1; the sheet states no ratio unit. '
  'Four exact pull-report card examples and the unnamed-parallel Jaxson Dart ten-copy example stay card-specific without numbering entire families. '
  'The official launch article explicitly announces July 10, 2026; product year 2025 and store Product Year 2026 remain separate. '
  'Exhaustive parallel numbering remains unverified.')
 data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,rawPages=raw,sourceDocumentNotes=notes,
  unclassifiedLines=[],source=proof['checklistUrl'],sha256=sha,dedicatedParser=PARSER,importKind='pdf',coverageComplete=True,sectionColumn=0,
  odds=odds,formats=formats,officialOddsTable=original,officialOddsFormats=formats,officialOddsHeader=['Card',*formats],
  oddsSource=proof['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=issues,oddsParser=PARSER,
  formatNamesPublished=True,oddsUnitsPublished=False,parallelSpecifications=[],publishedSpecifications=published,
  supplementaryOddsSources=[dict(url=proof['productOddsUrl'],sha256=oh,qualification='Fresh product-linked odds bytes match the official landing/global source.')],
  sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
 dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
 record.update(sourcePage=sources['landing'],rowCount=475,sections=12,sha256=sha,dedicatedParser=PARSER,coverageComplete=True,odds=84,formats=1,
  verified=proof['observed'],dataAudit=note,catalogEvidence=note,oddsParser=PARSER,oddsImportIssues=0,
  sourceObservation=dict(file=evidence['evidenceFile'],sha256=evidence['evidenceSha256'],source=sources['launch']))
 cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text())
 inventory=[record if r['slug']==SLUG else r for r in inventory] if any(r['slug']==SLUG for r in inventory) else inventory+[record]
 ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=[]
 registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Card-specific guide scope and remaining numbering',gap=' '.join(proof['remainingGaps']),source=sources['launch'],**evidence)]
 rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 print('Chrome Black Football: 475 subjects / 458 identities, 189 Rookie marks, 17 complete duals, 84 literal Hobby odds and five qualified card examples.')

if __name__=='__main__':build()
