"""Reconcile Resurgence's original columns, mixed-case families and four odds SKUs."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire,text
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-topps-resurgence-football';PARSER='scripts/import_topps_resurgence_2025.py'
PROOF=ROOT/'data/parallel-audit-sources/resurgence-football-2025-20261016.json'
FAMILIES={'BASE':100,'ROOKIES':100,'ELECTRO LIGHTS':25,'PERFECT FITS':20,'WIRED':30,'STRING THEORY':25,'CONDUCTORS':25,'PROTONYX':25,'VOLTAIC':25,'CIRCUIT BREAKERS':25,'Base Signatures':70,'Rookie Signatures':90,'ARC FLASH AUTOGRAPHS':22,'MOLECULAR MARKS':21,'NEON INITIATES':26,'THERMAL RED INK AUTOGRAPHS':20,'RESURGENCE ROOKIE RELIC SIGNATURES':40,'AMPED UP ROOKIE RELIC AUTOGRAPHS':30,'RADIAL ROOKIE RELICS':30}
FORMATS=['Hobby Pack Rate','Delight Pack Rate','Value Pack Rate','Mega Pack Rate']
def read_cards(path):
 rows=[];raw=[];notes=[];family=None
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==16
  for pn,page in enumerate(pdf.pages,1):
   raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
   for c in page.chars:groups[round(c['top'],1)].append(c)
   for y,cs in sorted(groups.items()):
    line=text(cs)
    if pn==1 and y<120:notes.append([str(pn),line]);continue
    if all('Bold' in c['fontname'] for c in cs):
     if line not in {'INSERT','AUTOGRAPH','AUTOGRAPH RELIC'}:assert line in FAMILIES,(pn,line);family=line
     continue
    assert family,(pn,line)
    # Split original drawing sequence at cell origins: long names overlap
    # the next column, so x-sorting or merged words can corrupt subjects.
    a=next(i for i,c in enumerate(cs) if abs(c['x0']-133.34)<.02);b=next(i for i,c in enumerate(cs) if abs(c['x0']-270.89)<.02);c=next((i for i,c in enumerate(cs) if abs(c['x0']-422.71)<.02),len(cs))
    number,name,team,mark=[text(part) for part in [cs[:a],cs[a:b],cs[b:c],cs[c:]]]
    assert re.fullmatch(r'\d+|[A-Z]+-[A-Za-z0-9]+',number) and name and team and mark in {'','Rookie'},(pn,line)
    rows.append([family,number,name,str(pn),team,mark])
 assert len(rows)==749 and collections.Counter(r[0] for r in rows)==FAMILIES and sum(r[5]=='Rookie' for r in rows)==379
 return rows,raw,notes

def read_odds(path):
 rows=[];raw=[];exceptions=[]
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==7
  table=pdf.pages[0].find_tables()[0];header=table.extract()[0];boxes=table.rows[0].cells
  assert header==['All Components',*FORMATS] and len(table.rows)==1
  for pn,page in enumerate(pdf.pages,1):
   assert page.width==792 and page.height==612
   raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
   for c in page.chars:
    if pn==1 and c['top']<table.bbox[3]:continue
    groups[round(c['top'],1)].append(c)
   for y,cs in sorted(groups.items()):
    cells=[text([c for c in cs if box[0]<=c['x0']<box[2]]) for box in boxes]
    assert sum(len([c for c in cs if box[0]<=c['x0']<box[2]]) for box in boxes)==len(cs)
    assert cells[0] and all(v=='-' or re.fullmatch(r'[\d,.]+(?::[\d,.]+)+',v) or (pn==1 and cells[0]=='Base Prism' and i==4 and v=='0.05') for i,v in enumerate(cells[1:],1)),(pn,y,cells)
    row=dict(name=cells[0],values=dict(zip(FORMATS,[None if v=='-' else v for v in cells[1:]])),page=pn);rows.append(row)
    if cells[0]=='Base Prism':
     top=min(c['top'] for c in cs);bottom=max(c['bottom'] for c in cs)
     exceptions.append(dict(page=pn,name=cells[0],format=FORMATS[3],value='0.05',nameBox=[boxes[0][0],top,boxes[0][2],bottom],valueBox=[boxes[4][0],top,boxes[4][2],bottom]))
 assert len(rows)==249 and len(exceptions)==1
 return rows,raw,exceptions

def build():
 proof=json.loads(PROOF.read_text());sources=proof['sources'];ph=hashlib.sha256(PROOF.read_bytes()).hexdigest();evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=ph)
 cp=ROOT/'data/set-catalog.json';cat=json.loads(cp.read_text());record=next(s for s in cat['sets'] if s['slug']==SLUG);dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
 path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');digest=acquire(record['checklistUrl'],path);rows,raw,notes=read_cards(path)
 op=path.with_name(SLUG+'-odds.pdf');oh=acquire(record['oddsUrl'],op);original,odds_raw,exceptions=read_odds(op);assert digest==proof['checklistSha256'] and oh==proof['oddsSha256']
 aliases={f:f for f in FAMILIES};aliases['Rookies Signatures']='Rookie Signatures';odds=[]
 for item in original:
  prefix=next((a for a in sorted(aliases,key=len,reverse=True) if item['name'].casefold()==a.casefold() or item['name'].casefold().startswith(a.casefold()+' ')),None);assert prefix,item['name']
  odds.append(dict(item,family=aliases[prefix],familyBase=item['name'].casefold() in {prefix.casefold(),prefix.casefold()+' base'}))
 note=('All 749 physical subject rows across 19 original sections retain separate Name, Team and 379 literal Rookie fields. '
       'Base Signatures and Rookie Signatures remain distinct, including their exact veteran/rookie odds joins. '
       'The 200 base entries print numbers 1–202 with 106 and 183 absent; the official guide instead describes 201 entries / 101 rookies. Neither source is silently corrected. '
       'All 249 odds categories retain four literal Pack Rate columns; the production disclaimer is not a format. Base Prism Mega 0.05 remains an uninterpreted published cell. '
       'Crimson Surge /199 joins only the veteran and rookie base categories. Neon Initiates Gold Power Surge is limited to 50 copies, with serial marking unstated. '
       'Named SuperFractor and Jalen Hurts /15 examples remain card-specific, without numbering other cards. '
       'Exhaustive parallel numbering and a general release-date statement remain unverified; article dates and box contents do not establish either.')
 table=lambda name,headers,values,source:dict(name=name,worksheet='Official Resurgence guides',headers=headers,rows=values,source=source,**evidence)
 data.update(headers=['Checklist section','Card number','Name','Source page','Team','Rookie'],rows=rows,originalSubjectHeaders=['Checklist section','Card number','Name','Source page','Team','Rookie'],originalSubjectRows=rows,source=record['checklistUrl'],sha256=digest,rawPages=raw,sourceDocumentNotes=notes,unclassifiedLines=[],importKind='pdf',sectionColumn=0,dedicatedParser=PARSER,coverageComplete=True,odds=odds,formats=FORMATS,oddsSource=record['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=[],oddsParser=PARSER,officialOddsTable=original,officialOddsFormats=FORMATS,officialOddsHeader=['All Components',*FORMATS],oddsLiteralExceptions=exceptions,formatNamesPublished=True,oddsUnitsPublished=True,parallelSpecifications=[],publishedSpecifications=[table('Official box configuration',['Published format','Published contents','Scope'],proof['configuration'],sources['boxGuide']),table('Guide parallel terms and card examples',['Checklist family','Subject scope','Parallel','Published term','Qualification'],proof['guideTerms'],sources['guide']),table('Official interview card example',['Checklist family','Card number','Subject','Parallel','Published numbering','Qualification'],proof['interviewTerms'],sources['preview']),table('Guide and PDF checklist discrepancy',['Source','Published base entries','Published rookie entries','Scope'],proof['counts'],sources['guide'])],sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
 dp.write_text(json.dumps(data,ensure_ascii=False)+'\n');record.update(sourcePage=sources['landing'],rowCount=749,sections=19,sha256=digest,dedicatedParser=PARSER,coverageComplete=True,odds=249,formats=4,oddsParser=PARSER,oddsImportIssues=0,verified=proof['observed'],dataAudit=note,catalogEvidence=note,sourceObservation=dict(file=evidence['evidenceFile'],sha256=ph,source=sources['guide']));assert record['releaseDate'] is None
 cp.write_text(json.dumps(cat,ensure_ascii=False,indent=2)+'\n')
 ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());inventory=[record if r['slug']==SLUG else r for r in inventory] if any(r['slug']==SLUG for r in inventory) else inventory+[record];ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=[dict(**spec,source=sources['guide'],**evidence) for spec in proof['approvedSpecifications']];registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Remaining numbering, source discrepancies and release-date evidence',gap=' '.join(proof['remainingGaps']),source=sources['guide'],**evidence)];rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 print('Resurgence: 749 physical rows / 19 sections / 379 Rookie marks; all 249 four-column odds, three scoped guide limits and card-specific examples reconciled.')
if __name__=='__main__':build()
