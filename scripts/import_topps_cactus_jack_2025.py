"""Preserve Cactus Jack original columns and its vertically offset odds cells."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire,text
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-26-topps-chrome-cactus-jack-basketball';PARSER='scripts/import_topps_cactus_jack_2025.py'
PROOF=ROOT/'data/parallel-audit-sources/cactus-jack-basketball-2025-26-20261016.json';FORMAT='Published odds (format not named)'
FAMILIES={'BASE CARDS':100,'UTOPIA HIGHLIGHTS':40,'JACKED UP':40,'LA FLAME LEGENDS':20,'ASTROVISION':20,'CACTUS MODE':20,'BASE AUTOGRAPH VARIATION':49,'CACTUS INK':49}
def read_cards(path):
 rows=[];raw=[];notes=[];family=None
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==8
  for pn,page in enumerate(pdf.pages,1):
   raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
   for c in page.chars:groups[round(c['top'],1)].append(c)
   for y,cs in sorted(groups.items()):
    line=text(cs)
    if pn==1 and y<100:notes.append([str(pn),line]);continue
    if all('Bold' in c['fontname'] for c in cs):
     if line not in {'INSERT','AUTOGRAPH'}:assert line in FAMILIES,(pn,line);family=line
     continue
    assert family,(pn,line)
    a=next(i for i,c in enumerate(cs) if abs(c['x0']-133.34)<.02);b=next(i for i,c in enumerate(cs) if abs(c['x0']-270.89)<.02);c=next((i for i,c in enumerate(cs) if abs(c['x0']-422.71)<.02),len(cs))
    number,name,team,mark=[text(part) for part in [cs[:a],cs[a:b],cs[b:c],cs[c:]]]
    assert re.fullmatch(r'\d+|[A-Z]+-[A-Za-z0-9]+',number) and name and team and mark in {'','Rookie'},(pn,line)
    rows.append([family,number,name,str(pn),team,mark])
 assert len(rows)==338 and collections.Counter(r[0] for r in rows)==FAMILIES and sum(r[5]=='Rookie' for r in rows)==154
 return rows,raw,notes

def read_odds(path):
 rows=[];raw=[];layout=[]
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==2
  for pn,page in enumerate(pdf.pages,1):
   raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
   for c in page.chars:groups[round(c['top'],1)].append(c)
   labels=[(y,cs) for y,cs in sorted(groups.items()) if abs(cs[0]['x0']-52.56)<.02]
   values=[(y,cs) for y,cs in sorted(groups.items()) if re.fullmatch(r'\d+:\d+',text(cs))]
   if pn==1:assert any(text(cs)=='Odds' for cs in groups.values())
   assert len(labels)==len(values)
   # The larger ratio glyphs start three points above their associated caption;
   # reading by generic text lines incorrectly treats the disclaimer as a header.
   for (ly,label),(vy,value) in zip(labels,values):
    assert abs((ly-vy)-3)<.12,(pn,ly,vy,text(label),text(value))
    name,ratio=text(label),text(value);rows.append(dict(name=name,values={FORMAT:ratio},page=pn))
    box=lambda cs:[round(min(c['x0'] for c in cs),3),round(min(c['top'] for c in cs),3),round(max(c['x1'] for c in cs),3),round(max(c['bottom'] for c in cs),3)]
    layout.append(dict(page=pn,name=name,value=ratio,labelBox=box(label),valueBox=box(value)))
 assert len(rows)==60 and len({r['name'] for r in rows})==60
 return rows,raw,layout

def build():
 proof=json.loads(PROOF.read_text());sources=proof['sources'];ph=hashlib.sha256(PROOF.read_bytes()).hexdigest();evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=ph)
 cp=ROOT/'data/set-catalog.json';cat=json.loads(cp.read_text());record=next(s for s in cat['sets'] if s['slug']==SLUG);dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
 path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');digest=acquire(record['checklistUrl'],path);rows,raw,notes=read_cards(path)
 op=path.with_name(SLUG+'-odds.pdf');oh=acquire(record['oddsUrl'],op);original,odds_raw,layout=read_odds(op);assert digest==proof['checklistSha256'] and oh==proof['oddsSha256']
 aliases={f:f for f in FAMILIES};aliases['Base']='BASE CARDS';odds=[]
 for item in original:
  prefix=next((a for a in sorted(aliases,key=len,reverse=True) if item['name'].casefold()==a.casefold() or item['name'].casefold().startswith(a.casefold()+' ')),None);assert prefix,item['name']
  odds.append(dict(item,family=aliases[prefix],familyBase=item['name'].casefold()==prefix.casefold()))
 note=('All 338 physical entries across eight sections are reconciled, retaining 100 base numbers, separate player/team cells and 154 literal Rookie marks. '
       'Original accents, Seattle Supersonics and the single printed Portland Trailblazers spelling remain intact. The final-page CI-YK row is retained. '
       'All 60 ratios are paired with their physically aligned captions, including Base 4:1; the larger value glyphs begin three points above the caption. '
       'The heading prints only Odds, without a named format or ratio unit. No Hobby format, pack rate or serial limit is inferred from box contents or ratio values. '
       'The official June 11 checklist spotlight explicitly announces June 19, 2026 for the main release; article publication and the separate All-Star product remain distinct. '
       'Reviewed guides confirm the eight checklist program sizes but do not establish a numeric serial-number ladder. Exhaustive parallel numbering remains unconfirmed.')
 table=lambda name,headers,values,source:dict(name=name,worksheet='Official main-release guide',headers=headers,rows=values,source=source,**evidence)
 data.update(headers=['Checklist section','Card number','Name','Source page','Team','Rookie'],rows=rows,originalSubjectHeaders=['Checklist section','Card number','Name','Source page','Team','Rookie'],originalSubjectRows=rows,source=record['checklistUrl'],sha256=digest,rawPages=raw,sourceDocumentNotes=notes,unclassifiedLines=[],importKind='pdf',sectionColumn=0,dedicatedParser=PARSER,coverageComplete=True,odds=odds,formats=[FORMAT],oddsSource=record['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=[],oddsParser=PARSER,officialOddsTable=original,officialOddsFormats=[FORMAT],officialOddsHeader=['Odds'],oddsLayoutRows=layout,formatNamesPublished=False,oddsUnitsPublished=False,parallelSpecifications=[],publishedSpecifications=[table('Hobby box and case configuration',['Published format','Published contents','Scope'],proof['configuration'],sources['spotlight']),table('Official guide checklist program sizes',['Checklist family','Published entries','Manufacturer description'],proof['guideFamilies'],sources['guide'])],sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
 dp.write_text(json.dumps(data,ensure_ascii=False)+'\n');record.update(sourcePage=sources['landing'],rowCount=338,sections=8,sha256=digest,dedicatedParser=PARSER,coverageComplete=True,odds=60,formats=1,oddsParser=PARSER,oddsImportIssues=0,verified=proof['observed'],dataAudit=note,catalogEvidence=note,sourceObservation=dict(file=evidence['evidenceFile'],sha256=ph,source=sources['spotlight']));cp.write_text(json.dumps(cat,ensure_ascii=False,indent=2)+'\n')
 ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());inventory=[record if r['slug']==SLUG else r for r in inventory] if any(r['slug']==SLUG for r in inventory) else inventory+[record];ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=[];registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Unverified main-release numbering and unnamed odds format/unit',gap=' '.join(proof['remainingGaps']),source=sources['guide'],**evidence)];rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 print('Cactus Jack: 338 entries / eight sections, 154 literal Rookie marks and 60 physical odds pairs. Format, ratio units and numbering remain unverified; official main release is June 19, 2026.')
if __name__=='__main__':build()
