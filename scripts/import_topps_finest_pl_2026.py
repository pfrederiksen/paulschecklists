"""Reconcile Finest PL physical columns, annotations and signer continuations."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire,text
from official_odds_layout import physical_odds_pdf
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-topps-finest-premier-league-2026'
PARSER='scripts/import_topps_finest_pl_2026.py';PROOF=ROOT/'data/parallel-audit-sources/finest-pl-2026-20261016.json'
FORMAT='Published odds (format not named)'
HEADERS=['Checklist section','Card number','Name','Source page','Team','Rookie','Published annotation','Printed card number','Card-specific guide specification']
def read_cards(path):
 rows=[];notes=[];raw=[];family=None;last=None;cont=[]
 with pdfplumber.open(path) as p:
  assert len(p.pages)==16
  for pn,page in enumerate(p.pages,1):
   raw.append(dict(page=pn,text=page.extract_text()));g=collections.defaultdict(list)
   for c in page.chars:g[round(c['matrix'][5],1)].append(c)
   for y,cs in sorted(g.items(),reverse=True):
    line=text(cs)
    if not line:continue
    if line.startswith(('Checklists provided','product at the time')) or line in {'BASE','INSERT','AUTOGRAPH'}:notes.append([str(pn),line]);continue
    a=max((i for i,c in enumerate(cs) if abs(c['matrix'][4]-183)<.02),default=-1)
    if a<0:
     assert all('Bold' in c['fontname'] for c in cs if c['text'].strip()),(pn,line)
     family=line;last=None;continue
    b=max((i for i,c in enumerate(cs) if abs(c['matrix'][4]-324)<.02),default=-1);c=max((i for i,c in enumerate(cs) if abs(c['matrix'][4]-467)<.02),default=len(cs))
    if b<0:assert family=='FINEST FANS',(pn,line);b=len(cs)
    assert b>a,(pn,line)
    number=text(cs[:a]);printed=number;name=text(cs[a:b]);team=text(cs[b:c]);rookie=text(cs[c:]);assert rookie in {'','Rookie','On-Card'},(pn,line)
    if number:assert re.fullmatch(r'\d+|[A-Z0-9]+-[A-Z0-9]+',number),(pn,line);last=number
    else:assert family=='FINEST PARTNERSHIPS' and last,(pn,line);number=last;cont.append(dict(row=len(rows),page=pn,cardNumber=number))
    rows.append([family,number,name,str(pn),team,rookie if rookie=='Rookie' else '',rookie,printed,''])
 assert len(rows)==767 and len(cont)==15 and len({r[0] for r in rows})==23 and sum(r[5]=='Rookie' for r in rows)==156
 return rows,raw,notes,cont

def build():
 proof=json.loads(PROOF.read_text());ph=hashlib.sha256(PROOF.read_bytes()).hexdigest();sources=proof['sources'];evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=ph)
 cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(s for s in catalog['sets'] if s['slug']==SLUG);dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
 path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');digest=acquire(record['checklistUrl'],path);rows,raw,notes,cont=read_cards(path)
 op=path.with_name(SLUG+'-odds.pdf');oh=acquire(record['oddsUrl'],op);original,formats,odds_raw,issues=physical_odds_pdf(op)
 assert digest==proof['checklistSha256'] and oh==proof['oddsSha256'] and len(original)==115 and formats==['PL FINEST 2026'] and not issues
 families={r[0] for r in rows};aliases={f:f for f in families}
 aliases.update({'COMMON BASE CARD':'BASE COMMON','UNCOMMON BASE CARD':'BASE UNCOMMON','RARE BASE CARD':'BASE RARE','SWERVE - FUSION VARIATION':'SWERVE FUSION VARIATION','FINEST PARTNERSHIPS - DUAL AUTOGRAPHS':'FINEST PARTNERSHIPS','ARRIVALS - AUTOGRAPH EDITION':'ARRIVALS AUTOGRAPH EDITION','MAIN ATTRACTION - AUTOGRAPH EDITION':'MAIN ATTRACTION AUTOGRAPH EDITION'})
 odds=[];unjoined=[]
 for original_odd in original:
  odd=dict(original_odd,values={FORMAT:original_odd['values'][formats[0]]});prefix=next((a for a in sorted(aliases,key=len,reverse=True) if odd['name'].casefold()==a.casefold() or odd['name'].casefold().startswith(a.casefold()+' ')),None)
  if prefix:odd.update(family=aliases[prefix],familyBase=odd['name'].casefold() in {prefix.casefold(),(prefix+' BASE').casefold()})
  else:
   assert odd['name'].startswith(('COMMON INSERTS (FIVE THEMES)','FINEST SEASONS - 1996/97')),odd['name']
   odd['family']='COMMON INSERTS (FIVE THEMES)' if odd['name'].startswith('COMMON INSERTS') else 'FINEST SEASONS - 1996/97'
   odd['qualification']='The five common themes are not named in the odds source; no exact roster join is inferred.' if odd['name'].startswith('COMMON INSERTS') else 'The odds sheet prints 1996/97, while the checklist and guide print 1995/96; the year mismatch remains unreconciled.'
   unjoined.append(odd['name'])
  odds.append(odd)
 assert len(unjoined)==13
 for example in proof['cardSpecific']:
  matching=[r for r in rows if r[0]==example['family'] and r[1]==example['cardNumber']];assert {r[2] for r in matching}==set(example['subjects'])
  for r in matching:r[8]=example['statement']+' Official source: '+sources['chase']
 note=('All 767 physical subject rows / 752 family-card identities across 23 sections are reconciled. '
       'Fifteen second signers retain their preceding printed partnership code for grouping and their original blank code cells. '
       'All 300 base numbers remain split into Common, Uncommon and Rare; (xB) EXPECTED BRILLIANCE is its own 40-card program. '
       'Names, original club spellings, Charlize Theron’s blank club and 156 literal Rookie marks are preserved. LeBron James’s On-Card annotation is separate from Rookie. '
       'All 115 odds values retain their original PL FINEST 2026 product-title column; the sheet names neither format nor ratio unit. '
       'The six common-insert group rows remain unjoined because the five themes are unnamed; seven 1996/97 odds rows remain separate from the checklist’s 1995/96 program. '
       'Only the named FP-SM 1/1 dual example and FS-IW five-copy red example receive card-specific guide statements, with no inferred parallel names or family-wide serial limits. '
       'April 23 store availability is not a verified general release date. Other numbering and exhaustive parallel coverage remain unverified.')
 table=lambda name,worksheet,headers,values,source:dict(name=name,worksheet=worksheet,headers=headers,rows=values,source=source,**evidence)
 data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=['Checklist section','Printed card number','Name','Source page','Team','Published annotation'],originalSubjectRows=[[r[0],r[7],r[2],r[3],r[4],r[6]] for r in rows],sourceContinuationRows=cont,rawPages=raw,sourceDocumentNotes=notes,unclassifiedLines=[],sha256=digest,dedicatedParser=PARSER,coverageComplete=True,importKind='pdf',sectionColumn=0,odds=odds,formats=[FORMAT],oddsSource=record['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=issues,oddsParser='scripts/official_odds_layout.py',officialOddsTable=original,officialOddsFormats=formats,officialOddsHeader=['Card',formats[0]],formatHeaderIsProductTitle=True,formatNamesPublished=False,oddsUnitsPublished=False,unjoinedOddsCategories=unjoined,parallelSpecifications=[],publishedSpecifications=[table('Manufacturer product fields','Box contents and store availability retain their original scope',['Published field','Published value','Scope'],proof['productFields'],sources['product']),table('Official guide examples','Only these exact card identities receive the printed limits',['Checklist family','Card number','Subjects','Published statement','Scope'],[[e['family'],e['cardNumber'],' / '.join(e['subjects']),e['statement'],e['scope']] for e in proof['cardSpecific']],sources['chase']),table('Official guide qualifications','Tier names and named metal variants do not establish print limits',['Published field','Published value','Scope'],proof['guideFields'],sources['guide'])],sourceSheets=[dict(name='Official source reconciliation',notes=[[note],['Source headings are descriptive adapter labels. Published annotation preserves both Rookie and On-Card; the Rookie filter uses only literal Rookie marks.'],*[[g] for g in proof['remainingGaps']]])])
 dp.write_text(json.dumps(data,ensure_ascii=False)+'\n');record.update(sourcePage=sources['landing'],rowCount=767,sections=23,sha256=digest,dedicatedParser=PARSER,coverageComplete=True,odds=115,formats=1,verified=proof['observed'],dataAudit=note,catalogEvidence=note,oddsParser=data['oddsParser'],oddsImportIssues=0,sourceObservation=dict(file=evidence['evidenceFile'],sha256=ph,source=sources['landing']));cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());inventory=[record if r['slug']==SLUG else r for r in inventory] if any(r['slug']==SLUG for r in inventory) else inventory+[record];ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=[];registry['conflicts']=[v for v in registry['conflicts'] if v['slug']!=SLUG]+[dict(slug=SLUG,family='Unnamed five-theme insert group, Seasons year and card-specific guide examples',gap=' '.join(proof['remainingGaps']),source=sources['chase'],**evidence)];rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 print('Finest Premier League: 767 subjects / 752 identities, all 15 second signers, 23 sections, 156 Rookie marks and 115 literal odds. Product title is not a format; two guide examples remain card-specific.')
if __name__=='__main__':build()
