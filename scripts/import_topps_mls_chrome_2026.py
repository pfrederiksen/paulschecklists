"""Retain MLS 2026 physical subjects, centered dual IDs and exact family captions."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire,text
from official_odds_layout import physical_odds_pdf
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-topps-chrome-major-league-soccer-2026'
PARSER='scripts/import_topps_mls_chrome_2026.py';PROOF=ROOT/'data/parallel-audit-sources/mls-chrome-2026-20261016.json'
HEADERS=['Checklist section','Card number','Name','Source page','Team','Rookie','National pairing country (card)','Printed card number','Published configuration (family)','Card-specific guide specification']
DUALS={'CHROME DUAL AUTOGRAPHS','NATIONAL PAIRINGS DUAL AUTOGRAPHS'}
def read_cards(path):
 subjects=[];pairs=[];configs={};raw=[];notes=[];family=None;config=''
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==13
  for pn,page in enumerate(pdf.pages,1):
   raw.append(dict(page=pn,text=page.extract_text()));g=collections.defaultdict(list)
   for c in page.chars:g[round(c['matrix'][5],1)].append(c)
   for y,cs in sorted(g.items(),reverse=True):
    line=text(cs)
    if not line:continue
    if line.startswith(('Checklists provided','product at the time')) or line in {'BASE','INSERT','AUTOGRAPH','AUTOGRAPH-RELIC'}:notes.append([str(pn),line]);continue
    if line.startswith('EXCLUSIVE TO '):configs[family]=line;config=line;continue
    a=max((i for i,c in enumerate(cs) if abs(c['matrix'][4]-132.62)<.03),default=-1)
    if a<0:
     if all('Bold' in c['fontname'] for c in cs if c['text'].strip()):family=line;config='';continue
     assert family in DUALS,(pn,line)
     number=text([c for c in cs if c['matrix'][4]<130]);country=text([c for c in cs if c['matrix'][4]>=421.25]);assert re.fullmatch(r'(?:DA|NPDA)-[A-Z]+',number),(pn,line)
     pairs.append(dict(page=pn,baseline=y,cardNumber=number,country=country,family=family));continue
    b=max((i for i,c in enumerate(cs) if abs(c['matrix'][4]-269.45)<.03),default=-1)
    end=max((i for i,c in enumerate(cs) if abs(c['matrix'][4]-421.27)<.03),default=len(cs))
    if b<0:assert family in {'TOPPS X SESAME STREET','MLS TROPHY'},(pn,line);b=len(cs)
    assert b>a,(pn,line)
    number=text(cs[:a]);name=text(cs[a:b]);team=text(cs[b:end]);rookie=text(cs[end:])
    assert rookie in {'','Rookie'},(pn,line)
    if number:assert re.fullmatch(r'\d+|[A-Z0-9]+-[A-Z0-9]+',number),(pn,line)
    else:assert family in DUALS,(pn,line)
    subjects.append(dict(family=family,number=number,name=name,page=pn,team=team,rookie=rookie,baseline=y,printed=number,country='',config=config))
 for pair in pairs:
  match=[i for i,r in enumerate(subjects) if r['page']==pair['page'] and r['family']==pair['family'] and abs(r['baseline']-pair['baseline'])<7]
  assert len(match)==2 and match[1]==match[0]+1,(pair,match)
  for i in match:
   assert not subjects[i]['number'];subjects[i]['number']=pair['cardNumber'];subjects[i]['country']=pair['country']
  pair['subjectRows']=match
 assert len(subjects)==593 and len(pairs)==17 and all(r['number'] for r in subjects)
 rows=[[r['family'],r['number'],r['name'],str(r['page']),r['team'],r['rookie'],r['country'],r['printed'],r['config'],''] for r in subjects]
 assert len({r[0] for r in rows})==21 and sum(r[5]=='Rookie' for r in rows)==149
 return rows,raw,notes,pairs,configs

def build():
 proof=json.loads(PROOF.read_text());ph=hashlib.sha256(PROOF.read_bytes()).hexdigest();sources=proof['sources'];evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=ph)
 cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(s for s in catalog['sets'] if s['slug']==SLUG);dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
 path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');digest=acquire(record['checklistUrl'],path);rows,raw,notes,pairs,configs=read_cards(path)
 op=path.with_name(SLUG+'-odds.pdf');oh=acquire(record['oddsUrl'],op);odds,formats,odds_raw,issues=physical_odds_pdf(op)
 assert digest==proof['checklistSha256'] and oh==proof['oddsSha256'] and len(odds)==139 and formats==['Hobby','Value','Mania'] and not issues
 families={r[0] for r in rows}
 for odd in odds:
  candidates=[f for f in families if odd['name'].casefold()==f.casefold() or odd['name'].casefold().startswith(f.casefold()+' ')];assert candidates,odd['name']
  family=max(candidates,key=len);odd.update(family=family,familyBase=odd['name'].casefold()==family.casefold())
 specs=[dict(family='MLS TROPHY',name='Superfractor',numbering='1/1',oddsName='MLS Trophy Superfractor',source=sources['formats'],sourceHeading='Topps Chrome MLS 2026 Hobby Box',qualification='Published for this family; individual-card eligibility is not inferred.',**evidence)]
 for example in proof['cardSpecific']:
  matching=[r for r in rows if r[0]==example['family'] and r[1]==example['cardNumber']];assert {r[2] for r in matching}==set(example['subjects']),example
  for r in matching:r[9]=example['statement']+' Official source: '+sources['guide']
 note=('All 593 physical subject rows / 576 family-card identities across 21 sections are reconciled. '
       'Thirty-four dual-autograph subjects join their 17 vertically centered printed IDs by physical row boxes; six national-pairing countries remain card-level fields, distinct from each signer’s club. '
       'All 149 literal Rookie marks, source club spellings, six blank team cells and 14 family-level configuration captions remain intact. Configuration subtitles are not checklist families. '
       'All 139 categories and three original Hobby/Value/Mania odds columns are literal, including 3:1 and 6:1; the PDF does not name ratio units. '
       'The exact MLS Trophy Superfractor 1/1 guide join is imported. David Beckham base 173 Superfractor 1/1 and DA-MH Black’s 10-copy limit remain card-specific, with no family-wide ladder inferred. '
       'The official format guide explicitly verifies September 10 street date. Other numbering and exhaustive parallel coverage remain unverified.')
 table=lambda name,worksheet,headers,values,source:dict(name=name,worksheet=worksheet,headers=headers,rows=values,source=source,**evidence)
 data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS[:6],originalSubjectRows=[[r[0],r[7],r[2],r[3],r[4],r[5]] for r in rows],pairedSourceCards=pairs,sourceConfigurations=configs,rawPages=raw,sourceDocumentNotes=notes,unclassifiedLines=[],sha256=digest,dedicatedParser=PARSER,coverageComplete=True,importKind='pdf',sectionColumn=0,odds=odds,formats=formats,oddsSource=record['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=issues,oddsParser='scripts/official_odds_layout.py',formatNamesPublished=True,oddsUnitsPublished=False,parallelSpecifications=specs,publishedSpecifications=[table('Manufacturer product fields','Box contents and store availability retain their source units',['Published field','Published value','Scope'],proof['productFields'],sources['product']),table('Official guide examples','Published examples remain restricted to these exact card identities',['Checklist family','Card number','Subjects','Parallel','Published statement','Scope'],[[e['family'],e['cardNumber'],' / '.join(e['subjects']),e['parallel'],e['statement'],e['scope']] for e in proof['cardSpecific']],sources['guide']),table('Official format guide','Box and case statements are not pack probabilities',['Format','Published field','Published value','Scope'],proof['formatFields'],sources['formats'])],sourceSheets=[dict(name='Official source reconciliation',notes=[[note],['Card number groups the physically paired signers; Printed card number preserves their blank baseline cells. National pairing country is the separately centered card-level source cell. Source column headings are descriptive adapter labels.'],*[[v] for v in proof['remainingGaps']]])])
 dp.write_text(json.dumps(data,ensure_ascii=False)+'\n');record.update(sourcePage=sources['landing'],rowCount=593,sections=21,sha256=digest,dedicatedParser=PARSER,coverageComplete=True,odds=139,formats=3,verified=proof['observed'],dataAudit=note,catalogEvidence=note,oddsParser=data['oddsParser'],oddsImportIssues=0,sourceObservation=dict(file=evidence['evidenceFile'],sha256=ph,source=sources['landing']));cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());inventory=[record if r['slug']==SLUG else r for r in inventory] if any(r['slug']==SLUG for r in inventory) else inventory+[record];ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=specs;registry['conflicts']=[v for v in registry['conflicts'] if v['slug']!=SLUG]+[dict(slug=SLUG,family='Other numbering, card-specific guide examples and box contents',gap=' '.join(proof['remainingGaps']),source=sources['guide'],**evidence)];rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 print('MLS Chrome 2026: 593 subjects / 576 identities, all 17 physical signer pairs, 21 sections, 149 Rookie marks, 139 odds / three formats and exact MLS Trophy 1/1.')
if __name__=='__main__':build()
