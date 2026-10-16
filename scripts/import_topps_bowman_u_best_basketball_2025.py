"""Reconcile Bowman U Best's physical player/school cells and continuation rows."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire,text
from official_odds_layout import physical_odds_pdf
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2025-26-bowman-university-best-basketball'
PARSER='scripts/import_topps_bowman_u_best_basketball_2025.py';PROOF=ROOT/'data/parallel-audit-sources/bowman-u-best-basketball-2025-26-20261015.json'
HEADERS=['Checklist section','Card number','Name','Source page','Team','Printed card number']
FAMILIES={'BASE CARDS','TONE SETTERS','BOWMAN MASTERPIECES','BREAKING BARRIERS','LETS GO','TOP BILLING','BIG ENERGY','BEST OF 2025 AUTOGRAPHS','GREATNESS AWAITS AUTOGRAPHS','ISO SIGNATURES','COACHES INK','DUAL AUTOGRAPHS REFRACTOR','TRIPLE AUTOGRAPHS REFRACTOR','PROSPECT JUMBO RELIC AUTOGRAPHS','PROSPECT DUAL RELIC AUTOGRAPHS','LET IT RAIN RELIC AUTOGRAPHS','GAME GRAPHS'}

def read_cards(path):
 rows=[];raw=[];notes=[];family=None;last=None;continuations=[]
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==13
  for pn,page in enumerate(pdf.pages,1):
   raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
   for c in page.chars:groups[round(c['matrix'][5],1)].append(c)
   for y,cs in sorted(groups.items(),reverse=True):
    line=text(cs)
    if not line:continue
    if pn==1 and y>730:notes.append([str(pn),line]);continue
    if line in FAMILIES:family=line;last=None;continue
    if line in {'INSERT','AUTOGRAPH','AUTOGRAPH RELIC'}:notes.append([str(pn),line]);continue
    # Original glyph draw order preserves player/school cells, even when long
    # player names overlap the next cell or a card code has no separating space.
    a=max((i for i,c in enumerate(cs) if abs(c['matrix'][4]-133.34)<.03),default=-1)
    b=max((i for i,c in enumerate(cs) if abs(c['matrix'][4]-270.89)<.03),default=-1)
    assert a>=0 and b>a,(pn,line,a,b)
    number=text(cs[:a]);printed=number;name=text(cs[a:b]);team=text(cs[b:])
    if not number:
     assert family in {'DUAL AUTOGRAPHS REFRACTOR','TRIPLE AUTOGRAPHS REFRACTOR'} and last,(pn,line)
     number=last;continuations.append(dict(row=len(rows),page=pn,cardNumber=number))
    else:
     assert re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+|GGBM',number),(pn,line,number)
     last=number
    assert family and name and team,(pn,line)
    rows.append([family,number,name,str(pn),team,printed])
 assert {r[0] for r in rows}==FAMILIES
 return rows,raw,notes,continuations

def build():
 proof=json.loads(PROOF.read_text());ph=hashlib.sha256(PROOF.read_bytes()).hexdigest();sources=proof['sources'];evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=ph)
 cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(s for s in catalog['sets'] if s['slug']==SLUG);dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
 path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');digest=acquire(proof['checklistUrl'],path);rows,raw,notes,continuations=read_cards(path)
 op=path.with_name(SLUG+'-odds.pdf');oh=acquire(proof['oddsUrl'],op);odds,formats,odds_raw,issues=physical_odds_pdf(op)
 assert digest==proof['checklistSha256'] and oh==proof['oddsSha256']
 assert len(rows)==658 and len({tuple(r[:2]) for r in rows})==618 and len(continuations)==40
 assert len(odds)==133 and formats==['Hobby'] and not issues
 aliases={f.title():f for f in FAMILIES}
 aliases.update({'Base':'BASE CARDS',"LET'S GO":'LETS GO','Dual Autos Refractors':'DUAL AUTOGRAPHS REFRACTOR','Triple Autos Refractors':'TRIPLE AUTOGRAPHS REFRACTOR','Prospect Dual Relic Auto':'PROSPECT DUAL RELIC AUTOGRAPHS'})
 refractor_base={'GREATNESS AWAITS AUTOGRAPHS','ISO SIGNATURES','COACHES INK','DUAL AUTOGRAPHS REFRACTOR','TRIPLE AUTOGRAPHS REFRACTOR'}
 for odd in odds:
  prefix=next((a for a in sorted(aliases,key=len,reverse=True) if odd['name'].casefold()==a.casefold() or odd['name'].casefold().startswith(a.casefold()+' ')),None)
  assert prefix,odd['name'];family=aliases[prefix]
  odd.update(family=family,familyBase=odd['name'].casefold()==(prefix+(' Refractor' if family in refractor_base else '')).casefold())
 specs=[dict(family='LETS GO',name='Superfractor',numbering='1/1',oddsName="LET'S GO Superfractor",source=sources['guide'],qualification='Published for this family; individual-card eligibility is not inferred.',sourceHeading='Crossover Chase: Let’s Go',**evidence)]
 assert next(o for o in odds if o['name']==specs[0]['oddsName'])['family']=='LETS GO'
 note=('All 658 physical subject rows / 618 family-card identities across 17 sections are reconciled. '
       'Forty secondary signer rows retain blank printed card-number cells, including continuations across pages; GGBM Brynn McGaughy is a printed alpha-only code. '
       'Name and school cells preserve original glyph draw order, source spellings and team assignments. The PDF publishes no rookie field. '
       'All 133 Hobby odds retain literal values with no stated ratio unit. Only Let’s Go Superfractor 1/1 is joined from the guide; the AJ Dybantsa Blue 150-copy example is card-specific. '
       'Other parallel limits, exhaustive numbering and general release date remain unverified.')
 table=lambda name,worksheet,headers,values,source:dict(name=name,worksheet=worksheet,headers=headers,rows=values,source=source,**evidence)
 data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS[:5],originalSubjectRows=[[r[0],r[5],r[2],r[3],r[4]] for r in rows],sourceContinuationRows=continuations,rawPages=raw,sourceDocumentNotes=notes,unclassifiedLines=[],sha256=digest,dedicatedParser=PARSER,coverageComplete=True,importKind='pdf',sectionColumn=0,odds=odds,formats=formats,oddsSource=proof['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=issues,oddsParser='scripts/official_odds_layout.py',formatNamesPublished=True,oddsUnitsPublished=False,parallelSpecifications=specs,publishedSpecifications=[table('Manufacturer product fields','Store availability and box contents are distinct from release dates and pack odds',['Published field','Published value','Scope'],proof['productFields'],sources['product']),table('Official guide qualifications','Card-specific examples do not number an entire family',['Published field','Published value','Scope'],proof['guideFields'],sources['guide'])],sourceSheets=[dict(name='Official source reconciliation',notes=[[note],['Name and Team are descriptive adapter labels for the unlabelled physical player/school columns. Card number carries the preceding ID for continuation grouping; Printed card number preserves the original blank cell.'],*[[g] for g in proof['remainingGaps']]])])
 dp.write_text(json.dumps(data,ensure_ascii=False)+'\n');record.update(sourcePage=sources['landing'],rowCount=658,sections=17,sha256=digest,dedicatedParser=PARSER,coverageComplete=True,odds=133,formats=1,verified=proof['observed'],dataAudit=note,catalogEvidence=note,oddsParser='scripts/official_odds_layout.py',oddsImportIssues=0,sourceObservation=dict(file=evidence['evidenceFile'],sha256=ph,source=sources['landing']));cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());inventory=[record if r['slug']==SLUG else r for r in inventory] if any(r['slug']==SLUG for r in inventory) else inventory+[record];ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=specs;registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG];registry['conflicts'].append(dict(slug=SLUG,family='Other numbering and card-specific guide example',gap=' '.join(proof['remainingGaps']),source=sources['guide'],**evidence));rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 print('Bowman U Best Basketball: 658 subjects / 618 family-card identities, 40 signer continuations, 133 literal Hobby odds and one exact guide numbering join.')

if __name__=='__main__':build()
