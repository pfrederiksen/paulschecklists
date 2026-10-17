"""Preserve Stadium Club Baseball's physical player/team/rookie columns."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire,text
from official_odds_layout import physical_odds_pdf
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-topps-stadium-club-baseball'
PARSER='scripts/import_topps_stadium_baseball_2025.py';PROOF=ROOT/'data/parallel-audit-sources/stadium-baseball-2025-20261016.json'
HEADERS=['Checklist section','Card number','Name','Source page','Team','Rookie']
FAMILIES={'BASE CARDS':200,'BEAM TEAM':20,'SAVAGE SLUGGERS':25,'CONCENTRATION':25,'YOURS FOR THE TAKING':25,
 'IN CASE OF EMERGENCY':25,'BASE CARDS I AUTOGRAPH VARIATION':161,'CHROME BASE CARDS AUTOGRAPH VARIATION':73,
 'SAVAGE SLUGGERS AUTOGRAPH VARIATION':18,'IN CASE OF EMERGENCY AUTOGRAPH VARIATION':17,'DUAL AUTOGRAPHS':18,
 'GOIN YARD AUTOGRAPHS':16,'ABSTRACT AUTOGRAPHS':14,'CONCENTRATION AUTOGRAPH VARIATION':12}
FORMATS=['Hobby','Value SE','Value EA','Mega SE','Mega EA','Fat Pack SE','Fat Pack EA']

def read_cards(path):
 rows=[];raw=[];notes=[];family=None
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==13
  for pn,page in enumerate(pdf.pages,1):
   raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
   for c in page.chars:groups[round(c['top'],1)].append(c)
   for y,cs in sorted(groups.items()):
    line=text(cs)
    if all('Bold' in c['fontname'] for c in cs):
     if line in {'SUBJECT TO CHANGE*','INSERT','AUTOGRAPH'}:notes.append([str(pn),line])
     else:
      assert line in FAMILIES,(pn,line);family=line
     continue
    # Original glyph order keeps each physical cell intact even when a long
    # player or historical team name overlaps the following column.
    a=next(i for i,c in enumerate(cs) if abs(c['x0']-132.62)<.03)
    b=next(i for i,c in enumerate(cs) if abs(c['x0']-269.45)<.03)
    r=next((i for i,c in enumerate(cs) if abs(c['x0']-421.27)<.03),len(cs))
    number,name,team,rookie=[text(part) for part in [cs[:a],cs[a:b],cs[b:r],cs[r:]]]
    assert family and re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+',number) and name and team and rookie in {'','Rookie'},(pn,line)
    rows.append([family,number,name,str(pn),team,rookie])
 assert len(rows)==649 and len({tuple(r[:2]) for r in rows})==640 and sum(r[5]=='Rookie' for r in rows)==233
 assert collections.Counter(r[0] for r in rows)==FAMILIES
 return rows,raw,notes

def build():
 proof=json.loads(PROOF.read_text());sources=proof['sources'];evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=hashlib.sha256(PROOF.read_bytes()).hexdigest())
 cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(s for s in catalog['sets'] if s['slug']==SLUG)
 dp=ROOT/record['tableData'];data=json.loads(dp.read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
 sha=acquire(proof['checklistUrl'],path);rows,raw,notes=read_cards(path)
 op=path.with_name(SLUG+'-odds.pdf');oh=acquire(proof['oddsUrl'],op);original,formats,odds_raw,issues=physical_odds_pdf(op)
 assert (sha,oh)==(proof['checklistSha256'],proof['oddsSha256']) and len(original)==80 and formats==FORMATS and not issues
 assert acquire(proof['productOddsUrl'],path.with_name(SLUG+'-product-odds.pdf'))==oh
 aliases={f.title():f for f in FAMILIES};aliases.update({'Base':'BASE CARDS',
  'Base Card Autograps':'BASE CARDS I AUTOGRAPH VARIATION','Base Card Autographs':'BASE CARDS I AUTOGRAPH VARIATION',
  'Base Chrome Autographs':'CHROME BASE CARDS AUTOGRAPH VARIATION',
  'Concentration Autographs':'CONCENTRATION AUTOGRAPH VARIATION',
  'In Case of Emergency Autographs':'IN CASE OF EMERGENCY AUTOGRAPH VARIATION',
  'Savage Sluggers Autographs':'SAVAGE SLUGGERS AUTOGRAPH VARIATION',"Goin' Yard Autographs":'GOIN YARD AUTOGRAPHS'})
 odds=[]
 for item in original:
  prefix=next((a for a in sorted(aliases,key=len,reverse=True) if item['name'].casefold()==a.casefold() or item['name'].casefold().startswith(a.casefold()+' ')),None)
  assert prefix,item['name'];odds.append(dict(item,family=aliases[prefix],familyBase=item['name'].casefold()==prefix.casefold()))
 assert {o['family'] for o in odds}==set(FAMILIES)
 note=('All 649 physical subject rows / 640 family-card identities across 14 sections are reconciled to original Name/Team/Rookie cell origins. '
  'All 200 base numbers, 233 printed Rookie marks and both signers on nine dual cards remain intact, including trademarks, historical teams and original spellings. '
  'All 80 odds categories retain seven original Hobby/Value/Mega/Fat Pack columns and null cells. The source names no ratio unit. '
  'Base Card Autograps remains literal, with exact paper/chrome/insert autograph aliases. '
  'The checked official product text publishes no numeric parallel ladder. Store February 18, 2026 availability and Product Year 2026 are separate from the 2025 checklist title. '
  'General release date and exhaustive parallel numbering remain unverified.')
 data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,rawPages=raw,sourceDocumentNotes=notes,
  unclassifiedLines=[],source=proof['checklistUrl'],sha256=sha,dedicatedParser=PARSER,importKind='pdf',coverageComplete=True,sectionColumn=0,
  odds=odds,formats=formats,officialOddsTable=original,officialOddsFormats=formats,officialOddsHeader=['Cards',*formats],
  oddsSource=proof['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=issues,oddsParser='scripts/official_odds_layout.py',
  formatNamesPublished=True,oddsUnitsPublished=False,parallelSpecifications=[],
  publishedSpecifications=[dict(name='Manufacturer product fields',headers=['Published field','Published value','Scope'],rows=proof['productFields'],source=sources['product'],worksheet='Store metadata and box/case contents; not parallel numbering or category odds',**evidence)],
  supplementaryOddsSources=[dict(url=proof['productOddsUrl'],sha256=oh,qualification='Fresh product-linked bytes match landing/global odds.')],
  sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
 dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
 record.update(sourcePage=sources['landing'],rowCount=649,sections=14,sha256=sha,dedicatedParser=PARSER,coverageComplete=True,odds=80,formats=7,
  verified=proof['observed'],dataAudit=note,catalogEvidence=note,oddsParser='scripts/official_odds_layout.py',oddsImportIssues=0,
  sourceObservation=dict(file=evidence['evidenceFile'],sha256=evidence['evidenceSha256'],source=sources['product']))
 cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());inventory=[record if r['slug']==SLUG else r for r in inventory] if any(r['slug']==SLUG for r in inventory) else inventory+[record]
 ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=[]
 registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Remaining numbering and source scope',gap=' '.join(proof['remainingGaps']),source=sources['landing'],**evidence)]
 rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 dates=ROOT/'data/release-dates.json';release=json.loads(dates.read_text());assert not any(e['slug']==SLUG for e in release['dates'])
 release['unresolved']=[e for e in release['unresolved'] if e['slug']!=SLUG]+[dict(slug=SLUG,gap='Official store availability is February 18, 2026; an explicit general release-date statement remains unverified.',sources=[dict(url=sources['product'],statement='Available From Feb 18, 2026; Product Year 2026, printed title 2025.',method='Fresh official product web read')])]
 dates.write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n')
 print('Stadium Club Baseball: 649 subjects / 640 identities, 233 Rookie marks, nine complete duals and 80 literal odds across seven formats; numbering and release gaps retained.')

if __name__=='__main__':build()
