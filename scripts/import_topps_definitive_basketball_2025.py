"""Retain Definitive's physical subjects, teams, flags and exact guide scopes."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire,text
from official_odds_layout import physical_odds_pdf
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-26-topps-definitive-basketball';PARSER='scripts/import_topps_definitive_basketball_2025.py'
PROOF=ROOT/'data/parallel-audit-sources/definitive-basketball-2025-26-20261016.json'
FAMILIES={'DEFINITIVE AUTOGRAPH RELICS':86,'DEFINITIVE ROOKIE PATCH AUTOGRAPHS':42,'AUTHENTIC RELIC AUTOGRAPHS':32,'OPENING ACT ROOKIE RELIC AUTOGRAPHS':20,'DEFINABLE RELIC AUTOGRAPHS':22,'ROOKIE DEFINING GAMES RELIC AUTOGRAPH':2,'DEFINITIVE MARKERS AUTOGRAPHS':19,'DEFINITIVE MOMENTS COLLECTION AUTOGRAPHS':30,'DUAL ROOKIE AUTOGRAPHS':30,'TRIPLE ROOKIE AUTOGRAPHS':15,'DUAL AUTOGRAPHS':20,'TRIPLE AUTOGRAPHS':15,'LEGENDARY AUTOGRAPH COLLECTION':15,'DECISIVE SIGNATURES':30,'DEFINITIVE ROOKIES AUTOGRAPHS':30,'DEFINITIVE AUTOGRAPHS':40,'DEFINING IMAGES AUTOGRAPHS':30,'DEFINITIVE SIGNS':30,'NOBLE INK':39,'FRAMED LEGENDS AUTOGRAPH COLLECTION':30,'FRAMED ROOKIES AUTOGRAPH COLLECTION':40,'FRAMED VETERANS AUTOGRAPH COLLECTION':29,'DEFINITIVE PATCH COLLECTION':56,'DEFINITIVE ROOKIE PATCH COLLECTION':38,'DEFINITIVE RELIC COLLECTION':100,'DEFINITIVE NAMEPLATE I':100,'DEFINITIVE NAMEPLATE II':84}
def read_cards(path):
 rows=[];raw=[];notes=[];family=None
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==15
  for pn,page in enumerate(pdf.pages,1):
   raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
   for c in page.chars:groups[round(c['top'],1)].append(c)
   for y,cs in sorted(groups.items()):
    line=text(cs)
    if pn==1 and y<102:notes.append([str(pn),line]);continue
    if all('Bold' in c['fontname'] for c in cs):
     if line not in {'AUTOGRAPH RELIC','AUTOGRAPH','RELIC'}:assert line in FAMILIES,(pn,line);family=line
     continue
    assert family,(pn,line)
    a=next(i for i,c in enumerate(cs) if abs(c['x0']-129.26)<.02);b=next(i for i,c in enumerate(cs) if abs(c['x0']-243.05)<.02);c=next((i for i,c in enumerate(cs) if abs(c['x0']-383.47)<.02),len(cs))
    number,name,team,mark=[text(part) for part in [cs[:a],cs[a:b],cs[b:c],cs[c:]]]
    assert re.fullmatch(r'[A-Z]+-[A-Za-z0-9]+',number) and name and team and mark in {'','Rookie'},(pn,line)
    rows.append([family,number,name,str(pn),team,mark])
 assert len(rows)==1024 and collections.Counter(r[0] for r in rows)==FAMILIES and sum(r[5]=='Rookie' for r in rows)==298
 assert len({tuple(r[:2]) for r in rows})==979
 return rows,raw,notes

def build():
 proof=json.loads(PROOF.read_text());sources=proof['sources'];ph=hashlib.sha256(PROOF.read_bytes()).hexdigest();evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=ph)
 cp=ROOT/'data/set-catalog.json';cat=json.loads(cp.read_text());record=next(s for s in cat['sets'] if s['slug']==SLUG);dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
 path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');digest=acquire(record['checklistUrl'],path);rows,raw,notes=read_cards(path)
 op=path.with_name(SLUG+'-odds.pdf');oh=acquire(record['oddsUrl'],op);original,formats,odds_raw,issues=physical_odds_pdf(op)
 assert digest==proof['checklistSha256'] and oh==proof['oddsSha256'] and len(original)==141 and formats==['HOBBY','FDI'] and not issues
 aliases={f:f for f in FAMILIES};aliases.update({'DEFINITIVE NAMEPLATE ONE':'DEFINITIVE NAMEPLATE I','DEFINITIVE NAMEPLATE TWO':'DEFINITIVE NAMEPLATE II','ROOKIE DEFINING GAMES RELIC AUTOGRAPH REDEMPTION':'ROOKIE DEFINING GAMES RELIC AUTOGRAPH'})
 odds=[]
 for item in original:
  prefix=next((a for a in sorted(aliases,key=len,reverse=True) if item['name']==a or item['name'].startswith(a+' ')),None);assert prefix,item['name']
  odds.append(dict(item,family=aliases[prefix],familyBase=item['name']==prefix))
 note=('All 1,024 physical subject rows / 979 family-card identities across 27 original families retain separate Name/Team cells and 298 literal Rookie marks. '
       'The production disclaimer is source text, not a card. Repeated dual/triple signer codes, accents and original historical team assignments remain intact. '
       'All 141 odds categories retain both original HOBBY and FDI columns, including null FDI Gold cells and the FDI-only Rookie Patch First Day Issue row. '
       'The source does not name a ratio unit, so no pack rate is inferred. Five exact Gold 1/1 family joins and both 1/1 Nameplate programs retain official product scope. '
       'Card-specific guide and pull-report examples remain separate from family limits; unnamed intermediate colors and the Triple Autographs /10 family statement remain qualified. '
       'Guide publication, preorder configuration and indexed availability do not establish a general release date. Exhaustive parallel numbering remains unconfirmed.')
 table=lambda name,headers,values,source:dict(name=name,worksheet='Official Definitive product guides',headers=headers,rows=values,source=source,**evidence)
 specs=[table(t['name'],t['headers'],t['rows'],sources[t['sourceKey']]) for t in proof['tables']]
 data.update(headers=['Checklist section','Card number','Name','Source page','Team','Rookie'],rows=rows,originalSubjectHeaders=['Checklist section','Card number','Name','Source page','Team','Rookie'],originalSubjectRows=rows,source=record['checklistUrl'],sha256=digest,rawPages=raw,sourceDocumentNotes=notes,unclassifiedLines=[],importKind='pdf',sectionColumn=0,dedicatedParser=PARSER,coverageComplete=True,odds=odds,formats=formats,oddsSource=record['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=issues,oddsParser='scripts/official_odds_layout.py',officialOddsTable=original,officialOddsFormats=formats,officialOddsHeader=['Card',*formats],formatNamesPublished=True,oddsUnitsPublished=False,parallelSpecifications=[],publishedSpecifications=specs,sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
 dp.write_text(json.dumps(data,ensure_ascii=False)+'\n');record.update(sourcePage=sources['landing'],rowCount=1024,sections=27,sha256=digest,dedicatedParser=PARSER,coverageComplete=True,odds=141,formats=2,oddsParser=data['oddsParser'],oddsImportIssues=0,verified=proof['observed'],dataAudit=note,catalogEvidence=note,sourceObservation=dict(file=evidence['evidenceFile'],sha256=ph,source=sources['guide']));assert record['releaseDate'] is None
 cp.write_text(json.dumps(cat,ensure_ascii=False,indent=2)+'\n')
 ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());inventory=[record if r['slug']==SLUG else r for r in inventory] if any(r['slug']==SLUG for r in inventory) else inventory+[record];ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=[dict(**s,source=sources['landing'],**evidence) for s in proof['approvedSpecifications']];registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Remaining parallel numbering and release-date evidence',gap=' '.join(proof['remainingGaps']),source=sources['guide'],**evidence)];rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 print('Definitive Basketball: 1,024 original rows / 979 identities / 27 families, 298 Rookie marks and 141 HOBBY/FDI odds; seven exact 1/1 joins with other examples qualified.')
if __name__=='__main__':build()
