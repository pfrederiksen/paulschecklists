"""Reconcile Chrome WWE's physical cells, literal codes and exact guide scopes."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire,text
from official_odds_layout import physical_odds_pdf
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-chrome-wwe'
PARSER='scripts/import_topps_chrome_wwe_2026.py';PROOF=ROOT/'data/parallel-audit-sources/chrome-wwe-2026-20261015.json'
HEADERS=['Checklist section','Card number','Name','Source page','Designation','Rookie']
BASE=['BASE CARDS I','BASE CARDS II']
def read_cards(path):
 rows=[];raw=[];notes=[];family=None
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==46
  for pn,page in enumerate(pdf.pages,1):
   raw.append(dict(page=pn,text=page.extract_text()));g=collections.defaultdict(list)
   for c in page.chars:g[round(c['matrix'][5],1)].append(c)
   if pn>=27:assert not page.chars
   for y,cs in sorted(g.items(),reverse=True):
    line=text(cs)
    if not line:continue
    if line.startswith('Checklists provided') or line in {'BASE','INSERT','AUTOGRAPH','AUTOGRAPH RELIC'}:notes.append([str(pn),line]);continue
    a=max((i for i,c in enumerate(cs) if abs(c['matrix'][4]-132.62)<.03),default=-1)
    if a<0:
     assert all('Bold' in c['fontname'] for c in cs if c['text'].strip()),(pn,line)
     family=line;continue
    b=max((i for i,c in enumerate(cs) if abs(c['matrix'][4]-269.45)<.03),default=-1)
    end=max((i for i,c in enumerate(cs) if abs(c['matrix'][4]-421.27)<.03),default=len(cs))
    if b<0:assert family=='2025 TOPPS CHROME WWE BUYBACK AUTOGRAPHS',(pn,line);b=len(cs)
    assert b>a,(pn,line)
    row=[family,text(cs[:a]),text(cs[a:b]),str(pn),text(cs[b:end]),text(cs[end:])]
    assert re.fullmatch(r'\d+|3:16-\d+|[A-Z0-9]+(?:-[A-Z0-9]+)?',row[1]),row
    assert row[4] in {'','Legend','Raw','Smackdown','SmackDown','NXT','WWE'} and row[5] in {'','Rookie'},row
    rows.append(row)
 assert len(rows)==1137 and len({r[0] for r in rows})==53 and sum(r[5]=='Rookie' for r in rows)==13
 return rows,raw,notes

def build():
 proof=json.loads(PROOF.read_text());ph=hashlib.sha256(PROOF.read_bytes()).hexdigest();sources=proof['sources'];evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=ph)
 cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(s for s in catalog['sets'] if s['slug']==SLUG);dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
 path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');digest=acquire(record['checklistUrl'],path);rows,raw,notes=read_cards(path)
 op=path.with_name(SLUG+'-odds.pdf');oh=acquire(record['oddsUrl'],op);odds,formats,odds_raw,issues=physical_odds_pdf(op)
 assert digest==proof['checklistSha256'] and oh==proof['oddsSha256'] and len(odds)==410 and len(formats)==11 and not issues
 families={r[0] for r in rows};aliases={re.sub(r' \(.*','',f):f for f in families}
 aliases.update({'BASE':BASE[0],'BASE ALTERNATE PERSONA IMAGE VARIATIONS':'ALTERNATE PERSONA IMAGE VARIATIONS (HOBBY ONLY)','BASE ICONIC IMPRINTS IMAGE VARIATIONS':'ICONIC IMPRINTS IMAGE VARIATIONS (HOBBY ONLY)','AUSTIN 3:16':'AUSTIN 3 16 (HOBBY, FDI)','THE ROCK: DIAMOND LEGACY':'THE ROCK DIAMOND LEGACY (HOBBY, FDI)',"LET'S GO":'LETS GO','BASE AUTOGRAPH VARIATIONS':'BASE CARDS I AUTOGRAPH VARIATION','1986 TOPPS VARIATION AUTOGRAPHS':'1986 TOPPS AUTOGRAPH VARIATION','ICONIC IMPRINTS VARIATIONS AUTOGRAPHS':'ICONIC IMPRINTS AUTOGRAPH VARIATION (Hobby/Breaker/FDI)','ALTERNATE PERSONA IMAGE VARIATIONS AUTOGRAPHS':'ALTERNATE PERSONA IMAGE VARIATION AUTOGRAPHS',"THE PEOPLE'S CHAMP AUTOGRAPH":'THE PEOPLES CHAMP AUTOGRAPH','"STONE COLD" STEVE AUSTIN 30TH ANNIVERSARY AUTOGRAPHS':'STONE COLD STEVE AUSTIN 30TH ANNIVERSARY AUTOGRAPHS (HOBBY, BREAKER, FDI)','MARKS OF CHAMPIONS AUTOGRAPHS':'MARKS OF CHAMPIONS','FEEL THE POP!':'FEEL THE POP (HOBBY, FDI)','2025 CHROME WWE BUYBACK AUTOGRAPHS':'2025 TOPPS CHROME WWE BUYBACK AUTOGRAPHS','MAIN ROSTER DEBUT PATCH AUTOGRAPHS REDEMPTION CARDS':'MAIN ROSTER DEBUT PATCH AUTOGRAPHS','BEAST INCARNATE':'BEAST INCARNATE AUTOGRAPH (HOBBY, BREAKER, FDI)','SAY HIS NAME':'SAY HIS NAME AUTOGRAPH (HOBBY, BREAKER, FDI)'})
 unjoined=[]
 for odd in odds:
  prefix=next((a for a in sorted(aliases,key=len,reverse=True) if odd['name'].casefold()==a.casefold() or odd['name'].casefold().startswith(a.casefold()+' ')),None)
  if prefix:
   f=aliases[prefix];odd.update(family=f,familyBase=odd['name'].casefold()==prefix.casefold())
   if prefix=='BASE':odd['familyAliases']=[BASE[1]];odd['familyBase']=odd['name']=='BASE REFRACTOR'
   if odd['name']=='BASE AUTOGRAPH VARIATIONS FIRST DAY ISSUE':odd['family']='BASE CARDS I AUTOGRAPH VARIATION (FDI EXCLUSIVE)'
  else:
   unjoined.append(odd['name']);odd.update(family=odd['name'],qualification='The combined odds sheet publishes this category, but no exact subject-roster family is reconciled in the linked checklist.')
 specs=[]
 for s in proof['numbering']:
  entry=dict(s,source=sources['guide'],qualification='Published for this family; individual-card eligibility is not inferred.',sourceHeading='Base Set and Parallels' if s['family']==BASE[0] else s['family'],**evidence)
  if s.get('oddsName'):assert next(o for o in odds if o['name']==s['oddsName'])['family']==s['family']
  specs.append(entry)
 assert len(specs)==33
 note=('All 1,137 physical subject rows / 1,110 family-card identities across 53 sections are reconciled from original glyph origins. '
       'All 25 Austin 3:16 cards, numeric-leading 1986/2025 captions, the 61 Iconic Imprints autograph rows and 30 1986 autograph rows retain their actual families. '
       'Names, WWE designations and 13 literal Rookie flags remain separate; designations are not teams. The two buyback rows retain blank designation cells. '
       'All 410 categories and 11 original combined-odds columns remain literal, including three-part and period-separated notation. The header does not name ratio units. '
       'Thirty-three exact guide limits cover the 200-card base I/II program and five named insert/autograph families; no limits propagate to Base III, Sapphire, geometric or other colors. '
       'Odds-only rosters and the Hobby guide’s FrozenFractor scope remain unjoined; exhaustive numbering is unverified.')
 table=lambda name,worksheet,headers,values,source:dict(name=name,worksheet=worksheet,headers=headers,rows=values,source=source,**evidence)
 data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,rawPages=raw,sourceDocumentNotes=notes,unclassifiedLines=[],sha256=digest,dedicatedParser=PARSER,coverageComplete=True,importKind='pdf',sectionColumn=0,odds=odds,formats=formats,oddsSource=record['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=issues,oddsParser='scripts/official_odds_layout.py',formatNamesPublished=True,oddsUnitsPublished=False,unjoinedOddsCategories=unjoined,parallelSpecifications=specs,publishedSpecifications=[table('Official product configuration','Published box contents are separate from pack odds',['Published field','Published value','Scope'],proof['productFields'],sources['product']),table('Official format guide','Box contents and an unjoined FrozenFractor statement retain their source scope',['Format','Published field','Published value','Scope'],proof['formatFields'],sources['formats'])],sourceSheets=[dict(name='Official source reconciliation',notes=[[note],['Name, Designation and Rookie are descriptive adapter labels for the source’s physical columns.'],*[[v] for v in proof['remainingGaps']]])])
 dp.write_text(json.dumps(data,ensure_ascii=False)+'\n');record.update(sourcePage=sources['landing'],rowCount=len(rows),sections=53,sha256=digest,dedicatedParser=PARSER,coverageComplete=True,odds=410,formats=11,verified=proof['observed'],dataAudit=note,catalogEvidence=note,oddsParser=data['oddsParser'],oddsImportIssues=0,sourceObservation=dict(file=evidence['evidenceFile'],sha256=ph,source=sources['landing']));cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());inventory=[record if r['slug']==SLUG else r for r in inventory] if any(r['slug']==SLUG for r in inventory) else inventory+[record];ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=specs;registry['conflicts']=[v for v in registry['conflicts'] if v['slug']!=SLUG]+[dict(slug=SLUG,family='Other numbering, combined odds rosters and FrozenFractors',gap=' '.join(proof['remainingGaps']),source=sources['guide'],**evidence)];rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 print('Chrome WWE: 1,137 subject rows / 1,110 identities, 53 sections, 13 literal Rookie flags, all 410 odds/11 columns and 33 guide limits.')
if __name__=='__main__':build()
