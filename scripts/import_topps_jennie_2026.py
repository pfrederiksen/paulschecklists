"""Reconcile every Jennie physical card/odds cell and exact product specification."""
import collections, hashlib, json, re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire
ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2026-topps-chrome-x-jennie';PARSER='scripts/import_topps_jennie_2026.py'
PROOF=ROOT/'data/parallel-audit-sources/jennie-2026-20261016.json';FORMAT='Odds (Per Pack)'
FAMILIES={'BASE':30,'CHROMIUM CLOSE-UPS INSERT':10,'MONOCHROME MEMENTOS INSERT':10,'RUBY SHORT PRINTS':2,'RUBY SUPER SHORT PRINT':1,'CONCERT RELICS':1,'BASE AUTOGRAPH VARIATIONS':10,'RUBY SP AUTOGRAPH VARIATIONS':2,'CONCERT AUTOGRAPH-RELICS':1,'RUBY SSP AUTOGRAPH VARIATION':1}
PREFIXES={'BASE CARDS':'BASE','CHROMIUM CLOSE-UPS':'CHROMIUM CLOSE-UPS INSERT','MONOCHROME MEMENTOS':'MONOCHROME MEMENTOS INSERT','RUBY SHORT PRINTS':'RUBY SHORT PRINTS','RUBY SUPER SHORT PRINTS':'RUBY SUPER SHORT PRINT','CONCERT RELICS':'CONCERT RELICS','BASE AUTOGRAPHS':'BASE AUTOGRAPH VARIATIONS','RUBY SP AUTOGRAPHS':'RUBY SP AUTOGRAPH VARIATIONS','AUTOGRAPH RELIC':'CONCERT AUTOGRAPH-RELICS','RUBY SSP AUTOGRAPHS':'RUBY SSP AUTOGRAPH VARIATION'}
clean=lambda chars:' '.join(''.join(c['text'] for c in chars).split())
def lines(page):
 groups=collections.defaultdict(list)
 for c in page.chars:groups[round(c['matrix'][5],1)].append(c)
 return [cs for _,cs in sorted(groups.items(),reverse=True)]
def read_cards(path):
 rows=[];raw=[];notes=[];family=None
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==3
  for pn,p in enumerate(pdf.pages,1):
   raw.append(dict(page=pn,text=p.extract_text()))
   for cs in lines(p):
    t=clean(cs)
    if t in FAMILIES:family=t;continue
    if t.startswith(('Checklists provided','product at the time','2026 Topps Chrome x Jennie')):notes.append([str(pn),t]);continue
    assert family,(pn,t)
    number=clean([c for c in cs if c['x0']<150]);subject=clean([c for c in cs if c['x0']>=150])
    assert re.fullmatch(r'\d+(?:-A)?|CC\d+|MM\d+|RSP\d(?:-A)?|RSSP(?:-A)?|C-(?:R|AR)',number),(pn,t)
    assert subject.startswith('Jennie') and not any('Bold' in c['fontname'] for c in cs),(pn,t)
    rows.append([family,number,subject,str(pn)])
 assert collections.Counter(r[0] for r in rows)==FAMILIES and len(rows)==68
 return rows,raw,notes

def read_odds(path):
 odds=[];raw=[]
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==2
  for pn,p in enumerate(pdf.pages,1):
   raw.append(dict(page=pn,text=p.extract_text()))
   for cs in lines(p):
    t=clean(cs)
    if t=='COMPONENTOdds (Per Pack)':continue
    starts=[i for i,c in enumerate(cs) if c['text'].strip() and abs(c['matrix'][4]-305.81)<.02]
    assert len(starts)==1,(pn,t);idx=starts[0];name=clean(cs[:idx]);value=clean(cs[idx:])
    assert re.fullmatch(r'1:[\d,]+',value) and name,(pn,name,value)
    prefix=next(k for k in sorted(PREFIXES,key=len,reverse=True) if name==k or name.startswith(k+' '))
    odds.append(dict(name=name,values={FORMAT:value},page=pn,family=PREFIXES[prefix],familyBase=name==prefix))
 assert len(odds)==58
 return odds,raw

def build():
 proof=json.loads(PROOF.read_text());evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=hashlib.sha256(PROOF.read_bytes()).hexdigest())
 cp=ROOT/'data/set-catalog.json';cat=json.loads(cp.read_text());record=next(s for s in cat['sets'] if s['slug']==SLUG)
 path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');digest=acquire(record['checklistUrl'],path)
 op=path.with_name(SLUG+'-odds.pdf');oh=acquire(proof['oddsSource'],op)
 assert digest==proof['checklistSha256'] and oh==proof['oddsSha256']
 rows,raw,notes=read_cards(path);odds,odds_raw=read_odds(op)
 specs=[]
 by_name={o['name']:o for o in odds}
 for group in proof['numbering']:
  family=group['family'];prefix=next(k for k,v in PREFIXES.items() if v==family)
  for name,numbering in group['entries']:
   if not numbering:continue
   if family=='BASE':suffix=name.upper()+' PARALLEL'
   elif family.endswith('INSERT'):suffix=name.upper().replace(' REFRACTOR','')+' PARALLEL'
   elif family=='CONCERT RELICS':suffix=name.upper()
   else:suffix=name.upper().replace(' REFRACTOR','')+' PARALLEL'
   full=prefix+' '+suffix
   spec=dict(family=family,name=name,numbering=numbering,source=proof['source'],sourceHeading=group['heading'],qualification='Published for this family; individual-card eligibility is not inferred.',**evidence)
   if full in by_name:spec['oddsName']=full
   else:
    assert family=='CONCERT AUTOGRAPH-RELICS' and name=='Superfractor'
    spec['qualification']='Product Description names Superfractor /1; the odds PDF names Foilfractor instead. No equivalence or shared limit is inferred.'
   specs.append(spec)
 assert len(specs)==51 and sum('oddsName' in s for s in specs)==50
 note=('All 68 physical card entries across ten sections are reconciled, including alphabetic RSSP in RUBY SUPER SHORT PRINT. '
       'Original subject and photoshoot descriptions are preserved; no team or rookie fields are published. '
       'All 58 category ratios are explicitly per pack, without a named format. '
       'The product Description supplies 51 family-scoped numbering specifications: 50 exact odds joins and one separate Superfractor autograph-relic specification. '
       'The odds-only autograph-relic Foilfractor retains its ratio without an inferred /1 limit. '
       'Unnumbered categories stay unnumbered and box contents stay separate from odds. Exhaustive parallel coverage remains unconfirmed.')
 payload=dict(title=record['title'],headers=['Checklist section','Card number','Subject','Source page'],rows=rows,source=record['checklistUrl'],sha256=digest,originalSubjectHeaders=['Checklist section','Card number','Subject','Source page'],originalSubjectRows=rows,rawPages=raw,sourceDocumentNotes=notes,unclassifiedLines=[],importKind='pdf',sectionColumn=0,dedicatedParser=PARSER,coverageComplete=True,odds=odds,formats=[FORMAT],oddsSource=proof['oddsSource'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=[],oddsParser=PARSER,oddsUnitsPublished=True,formatNamesPublished=False,parallelSpecifications=specs,publishedSpecifications=[dict(name='Manufacturer product fields',worksheet='Product Description and Overview',headers=['Published field','Published value'],rows=proof['productFields'],source=proof['source'],**evidence)],sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
 (ROOT/record['tableData']).write_text(json.dumps(payload,ensure_ascii=False)+'\n')
 record.update(rowCount=68,sections=10,odds=58,formats=1,oddsUrl=proof['oddsSource'],sourcePage=proof['landing'],sha256=digest,dedicatedParser=PARSER,oddsParser=PARSER,coverageComplete=True,verified=proof['observed'],dataAudit=note,catalogEvidence=note,sourceObservation=dict(file=evidence['evidenceFile'],sha256=evidence['evidenceSha256'],source=proof['source']))
 cp.write_text(json.dumps(cat,ensure_ascii=False,indent=2)+'\n')
 ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());inventory=[record if r['slug']==SLUG else r for r in inventory] if any(r['slug']==SLUG for r in inventory) else inventory+[record];ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=specs;registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Concert Autograph-Relics / Superfractor versus Foilfractor',gap=' '.join(proof['remainingGaps']),source=proof['source'],**evidence)];rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 print('Jennie: 68 cards / ten sections, 58 literal per-pack odds, 51 numbering specifications / 50 exact odds joins. Superfractor-Foilfractor conflict remains explicit.')
if __name__=='__main__':build()
