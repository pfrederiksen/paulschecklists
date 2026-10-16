"""Preserve Winter Olympics caption families, repeated signers and odds cells."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire,text
from official_odds_layout import physical_odds_pdf
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-chrome-u-s-winter-olympics-paralympic-team-hopefuls';PARSER='scripts/import_topps_olympics_2026.py'
PROOF=ROOT/'data/parallel-audit-sources/winter-olympics-2026-20261016.json'
FAMILIES={'BASE CARDS I':100,'BASE CARDS II':100,'BUONGIORNO':20,'FOR PRIDE AND COUNTRY':25,'1986 TOPPS':40,'WINTER BLIZZARD':15,'CHASING THE RINGS':50,'HIDDEN GEMS':5,'LETS GO':24,'HELIX':20,'MILANO CORTINA':1,'BASE CARDS AUTOGRAPH VARIATION':99,'OLYMPIC CHAMPIONS':12,'1986 TOPPS AUTOGRAPH VARIATION':10,'DUAL AUTOGRAPHS':12,'TOPPS DYNASTY AUTOGRAPH PATCH CARDS':15,'TEAM USA MEMORABILIA PIECES':78,'TEAM USA JUMBO MEMORABILIA PIECES':81}
def read_cards(path):
 rows=[];raw=[];family=None
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==15
  for pn,page in enumerate(pdf.pages,1):
   raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
   for c in page.chars:groups[round(c['top'],1)].append(c)
   for y,cs in sorted(groups.items()):
    line=text(cs)
    if all('Bold' in c['fontname'] for c in cs):
     if line not in {'BASE','INSERT','AUTOGRAPH','RELIC','AUTOGRAPH RELIC'}:assert line in FAMILIES,(pn,line);family=line
     continue
    assert family,(pn,line)
    i=next(i for i,c in enumerate(cs) if abs(c['x0']-132.62)<.02);number=text(cs[:i]);name=text(cs[i:])
    assert re.fullmatch(r'\d+|[A-Z0-9]+-[A-Z0-9]+',number) and name,(pn,line)
    rows.append([family,number,name,str(pn)])
 assert len(rows)==707 and collections.Counter(r[0] for r in rows)==FAMILIES
 assert len({tuple(r[:2]) for r in rows})==701
 return rows,raw

def build():
 proof=json.loads(PROOF.read_text());sources=proof['sources'];ph=hashlib.sha256(PROOF.read_bytes()).hexdigest();evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=ph)
 cp=ROOT/'data/set-catalog.json';cat=json.loads(cp.read_text());record=next(s for s in cat['sets'] if s['slug']==SLUG);dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
 path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');digest=acquire(record['checklistUrl'],path);rows,raw=read_cards(path)
 op=path.with_name(SLUG+'-odds.pdf');oh=acquire(record['oddsUrl'],op);original,formats,odds_raw,issues=physical_odds_pdf(op)
 assert digest==proof['checklistSha256'] and oh==proof['oddsSha256'] and len(original)==85 and formats==['Hobby-146','Value Box SE-148','Value Box EA-147'] and not issues
 aliases={f:f for f in FAMILIES};aliases.update({'Base':'BASE CARDS I','Base Card Autograph Variation':'BASE CARDS AUTOGRAPH VARIATION','Olympic Champions Autographs':'OLYMPIC CHAMPIONS','1986 Topps Autographs':'1986 TOPPS AUTOGRAPH VARIATION',"Let's Go":'LETS GO','Dynasty Autograph Patch':'TOPPS DYNASTY AUTOGRAPH PATCH CARDS'})
 odds=[]
 for item in original:
  prefix=next((a for a in sorted(aliases,key=len,reverse=True) if item['name'].casefold()==a.casefold() or item['name'].casefold().startswith(a.casefold()+' ')),None);assert prefix,item['name']
  odd=dict(item,family=aliases[prefix],familyBase=item['name'].casefold()==prefix.casefold())
  if prefix=='Base':odd['familyAliases']=['BASE CARDS II']
  odds.append(odd)
 note=('All 707 physical subject rows / 701 family-card identities across 18 sections are reconciled. '
       'Both 1986 Topps headings are captions, restoring the separate 40-card insert and ten-card autograph programs rather than counting the headings as cards. '
       'Both 100-card base lists remain separate; repeated dual codes retain both subjects. Base card 37 Jack Hughes and card 137 Aaron Pike retain their printed identities. '
       'The source publishes names but no team, athlete-sport or rookie field; none are inferred from Team USA branding. '
       'All 85 odds categories retain three original columns and literal cells, including nulls, Hobby Base Green 01:23:00 and repeated Silver Silver / Gold Gold Dynasty wording. '
       'The sheet does not state a ratio unit; no pack rates are computed. Both base sections share explicitly aliased Base odds. '
       'Pink Refractors /250 remains a qualified product-guide statement without an exact family join; no other colors receive inferred limits. '
       'Product Year 2025 and January 15, 2026 U.S. store availability remain separate from the checklist title and an unverified general release date. Exhaustive parallel numbering remains unconfirmed.')
 table=lambda name,headers,values,source:dict(name=name,worksheet='Official product evidence',headers=headers,rows=values,source=source,**evidence)
 g=proof['guideStatement']
 approved=[dict(family='UNJOINED GUIDE STATEMENT (CHECKLIST FAMILY NOT NAMED)',name=g['parallel'],numbering=g['numbering'],qualification=g['qualification'],source=sources['guide'],sourceHeading='What’s new in 2026',**evidence)]
 specs=[table('Hobby box contents',['Published format','Published configuration','Scope'],[proof['configuration'][0]],sources['hobby']),table('Value box contents',['Published format','Published configuration','Scope'],[proof['configuration'][1]],sources['value'])]
 for label,key,fields in [('Hobby','hobby',proof['storeFields'][0]),('Value','value',proof['storeFields'][1])]:specs.append(table(label+' store fields',['Product title format','SKU','Store Product Year','Available From','Qualification'],[fields],sources[key]))
 data.update(headers=['Checklist section','Card number','Name','Source page'],rows=rows,originalSubjectHeaders=['Checklist section','Card number','Name','Source page'],originalSubjectRows=rows,source=record['checklistUrl'],sha256=digest,rawPages=raw,unclassifiedLines=[],importKind='pdf',sectionColumn=0,dedicatedParser=PARSER,coverageComplete=True,odds=odds,formats=formats,oddsSource=record['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=issues,oddsParser='scripts/official_odds_layout.py',officialOddsTable=original,officialOddsFormats=formats,officialOddsHeader=['Cards',*formats],formatNamesPublished=True,oddsUnitsPublished=False,parallelSpecifications=approved,publishedSpecifications=specs,sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
 dp.write_text(json.dumps(data,ensure_ascii=False)+'\n');record.update(sourcePage=sources['landing'],rowCount=707,sections=18,sha256=digest,dedicatedParser=PARSER,coverageComplete=True,odds=85,formats=3,oddsParser=data['oddsParser'],oddsImportIssues=0,verified=proof['observed'],dataAudit=note,catalogEvidence=note,sourceObservation=dict(file=evidence['evidenceFile'],sha256=ph,source=sources['guide']));assert record['releaseDate'] is None
 cp.write_text(json.dumps(cat,ensure_ascii=False,indent=2)+'\n')
 ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());inventory=[record if r['slug']==SLUG else r for r in inventory] if any(r['slug']==SLUG for r in inventory) else inventory+[record];ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=approved;registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Unjoined Pink /250, other serial limits, ratio units and store availability',gap=' '.join(proof['remainingGaps']),source=sources['guide'],**evidence)];rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 print('Winter Olympics: 707 subject rows / 701 identities, 18 sections and 85 literal three-column odds; Pink /250 remains qualified and unjoined.')
if __name__=='__main__':build()
