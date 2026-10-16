"""Reconcile VeeFriends' glyph columns, artist rosters and eight-column odds."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire,text
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-chrome-veefriends'
PARSER='scripts/import_topps_veefriends_2026.py';PROOF=ROOT/'data/parallel-audit-sources/veefriends-2026-20261015.json'
HEADERS=['Checklist section','Card number','Player / subjects','Source page','Artist Name']
FAMILIES={'BASE CARDS','TOPPS 1986 BASE SET VARIATION','MANGA SPECKLE SET','CHALKBOARD','CONTENT CONDORS','ORIGINAL SKETCH SELECTIONS','NEON LIGHTS','INFINITE SAPPHIRE','VEEFRIENDS VARIANTS','STELLAR HAZE','BALANCE BATTLES','ICONICS','ERUPT','MEGAHEADS','VEEFRIENDS VARIANTS - LAST GLASS STANDING','VEEFRIENDS VARIANTS - GRITTY GHOST','HIDDEN GEMS','COMIC CLIPPINGS','CONTENT CONDORS AUTOGRAPHS','BASE CARDS GARY VEE AUTOGRAPH PARALLEL','BLANK CANVAS SKETCH CARDS','SKETCH CARDS'}
FORMATS=['Hobby','Sapphire','Value Box SE','Value Box EA','Value Box CEE','Mega Box SE','Mega Box EA','Mega Box CEE']

def read_cards(path):
 rows=[];raw=[];notes=[];family=None
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==17
  for pn,page in enumerate(pdf.pages,1):
   raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
   for c in page.chars:groups[round(c['matrix'][5],1)].append(c)
   for y,cs in sorted(groups.items(),reverse=True):
    line=text(cs)
    if not line:continue
    if line in FAMILIES:family=line;continue
    if line in {'BASE','INSERT','RELIC','AUTOGRAPH','SKETCH'} or line.startswith(('Checklists provided','time of production')):notes.append([str(pn),line]);continue
    assert family,(pn,line)
    if family in {'BLANK CANVAS SKETCH CARDS','SKETCH CARDS'}:rows.append([family,'',line,str(pn),line]);continue
    # The original subject origin separates SSA-100 from Zealous Zombie,
    # even though there is no visible inter-column space after that code.
    starts=[i for i,c in enumerate(cs) if abs(c['matrix'][4]-97.56)<.02];assert starts,(pn,line)
    start=max(starts);number=text(cs[:start]);subject=text(cs[start:])
    assert re.fullmatch(r'\d+|[A-Z0-9]+-[A-Z0-9]+',number) and subject,(pn,number,subject)
    rows.append([family,number,subject,str(pn),''])
 assert len(rows)==823 and sum(bool(r[1]) for r in rows)==711 and {r[0] for r in rows}==FAMILIES
 return rows,raw,notes

def read_odds(path):
 odds=[];raw=[];notes=[]
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==12
  # The final page preserves all ten original column-edge fragments. Middle
  # pages omit internal rules; their identical printed headers validate reuse.
  edges=sorted(set(round(line['x0'],4) for line in pdf.pages[-1].lines if abs(line['x0']-line['x1'])<.01))
  assert len(edges)==10 and all(abs(b-a-114.324)<.02 for a,b in zip(edges,edges[1:])),edges
  for pn,page in enumerate(pdf.pages,1):
   raw.append(dict(page=pn,text=page.extract_text()));tables=page.find_tables();assert len(tables)==1
   header=False
   for row in tables[0].rows:
    values=[]
    for a,b in zip(edges,edges[1:]):
     groups=collections.defaultdict(list)
     for c in page.chars:
      if a<=(c['x0']+c['x1'])/2<b and row.bbox[1]<=(c['top']+c['bottom'])/2<row.bbox[3]:groups[round(c['matrix'][5],1)].append(c)
     values.append(' '.join(text(cs) for y,cs in sorted(groups.items(),reverse=True)).strip())
    if not header and values==['Cards',*FORMATS]:header=True;continue
    if not header:
     assert pn==1 and not re.search(r'\d+:\d+', ' '.join(values))
     notes.append([str(pn),' '.join(values)]);continue
    assert values[0] and all(v=='-' or re.fullmatch(r'1:[\d,]+',v) for v in values[1:]),(pn,values)
    odds.append(dict(name=values[0],values=dict(zip(FORMATS,[None if v=='-' else v for v in values[1:]])),page=pn))
   assert header,pn
 assert len(odds)==104
 return odds,raw,notes

def build():
 proof=json.loads(PROOF.read_text());ph=hashlib.sha256(PROOF.read_bytes()).hexdigest();sources=proof['sources'];evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=ph)
 cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(s for s in catalog['sets'] if s['slug']==SLUG);dp=ROOT/record['tableData'];data=json.loads(dp.read_text())
 path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf');digest=acquire(proof['checklistUrl'],path);rows,raw,notes=read_cards(path)
 op=path.with_name(SLUG+'-odds.pdf');oh=acquire(proof['oddsUrl'],op);odds,odds_raw,odds_notes=read_odds(op)
 assert digest==proof['checklistSha256'] and oh==proof['oddsSha256']
 aliases={f.title():f for f in FAMILIES}
 aliases.update({'Base Set':'BASE CARDS','Base Set Gary Vee Autograph Parallel':'BASE CARDS GARY VEE AUTOGRAPH PARALLEL','Topps 1986 Variation':'TOPPS 1986 BASE SET VARIATION','Content Condor Creators':'CONTENT CONDORS','Content Condor Creators Base Autograph':'CONTENT CONDORS AUTOGRAPHS','Content Condor Creators Autograph':'CONTENT CONDORS AUTOGRAPHS','Content Condor On-Card Autograph':'CONTENT CONDORS AUTOGRAPHS','Erupt!':'ERUPT','VeeFriends Variants Gritty Ghost':'VEEFRIENDS VARIANTS - GRITTY GHOST','VeeFriends Variants Last Glass Standing':'VEEFRIENDS VARIANTS - LAST GLASS STANDING','Blank Canvas Art Card':'BLANK CANVAS SKETCH CARDS'})
 for odd in odds:
  prefix=next((a for a in sorted(aliases,key=len,reverse=True) if odd['name'].casefold()==a.casefold() or odd['name'].casefold().startswith(a.casefold()+' ')),None)
  assert prefix,odd['name'];odd.update(family=aliases[prefix],familyBase=odd['name'].casefold()==prefix.casefold())
 specs=[]
 for published in proof['numbering']:
  entry=published.copy();guide=entry.pop('guide');entry.setdefault('qualification','Published for this family; individual-card eligibility is not inferred.');entry.update(source=sources[guide],sourceHeading=entry['family'],**evidence)
  if entry.get('oddsName'):
   match=[o for o in odds if o['name']==entry['oddsName']];assert len(match)==1 and match[0]['family']==entry['family'],entry
  else:assert entry['family']=='BALANCE BATTLES' and entry['name']=='Green Refractor'
  specs.append(entry)
 assert len(specs)==34 and sum('oddsName' in s for s in specs)==33
 note=('All 711 numbered entries and 112 unnumbered artist entries across 22 sections are reconciled using original glyph columns. '
       'Both 200-card base and Gary Vee autograph rosters, all 100 Manga codes including SSA-100 Zealous Zombie, printed CC versus CCA autograph prefixes and source name spellings are preserved. '
       'The 104 odds categories retain eight exact format headings and every physical value; disclaimer text is not a format. '
       'Thirty-three exact guide joins and a specification-only Balance Battles Green Refractor retain family scope; the 1986 limit is a print count, not serial numbering. '
       'Guide-only signer/artist differences, explicit pack versus box/case units and the separately timed Sapphire edition remain qualified. Exhaustive numbering remains incomplete.')
 table=lambda name,worksheet,headers,values,source:dict(name=name,worksheet=worksheet,headers=headers,rows=values,source=source,**evidence)
 cases=[[*r,sources['erupt' if r[0]=='ERUPT' else 'sketch' if r[0]=='ORIGINAL SKETCH SELECTIONS' else 'iconics']] for r in proof['caseAverages']]
 boxes=[[*r,sources['manga' if r[0]=='MANGA SPECKLE SET' else 'neon' if r[0]=='NEON LIGHTS' else 'mega']] for r in proof['boxAverages']]
 data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,rawPages=raw,sourceDocumentNotes=notes,unclassifiedLines=[],sha256=digest,dedicatedParser=PARSER,coverageComplete=True,importKind='pdf',sectionColumn=0,odds=odds,formats=FORMATS,oddsSource=proof['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsSourceNotes=odds_notes,oddsIssues=[],oddsParser=PARSER,formatNamesPublished=True,oddsUnitsPublished=False,parallelSpecifications=specs,publishedSpecifications=[table('Manufacturer product fields','Exact family limits join the corresponding published odds',['Published field','Published value','Scope'],proof['productFields'],sources['landing']),table('Official guide qualifications','Printed PDF rosters remain distinct from guide claims',['Published field','Published value','Scope','Official source'],[[*r,sources[key]] for r,key in zip(proof['guideFields'],['chase','sketch','iconics','sketch','release'])],sources['chase']),table('Brand product configurations','Box contents are not pack odds',['Format','Published contents','Scope'],proof['formats'],sources['brand']),table('Brand variant pack odds','These five statements explicitly name packs; they do not establish units for other PDF ratios',['Family','Variant','Hobby packs','Mega packs','Value packs'],proof['variantPackOdds'],sources['variants']),table('Brand case averages','Published averages retain case units; no pack conversion',['Family','Parallel','Published average','Official source'],cases,sources['brand']),table('Brand pack and box averages','Original source units retained without conversion',['Family','Format','Published average','Official source'],boxes,sources['brand'])],sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
 dp.write_text(json.dumps(data,ensure_ascii=False)+'\n');record.update(sourcePage=sources['landing'],rowCount=len(rows),sections=22,sha256=digest,dedicatedParser=PARSER,coverageComplete=True,odds=104,formats=8,verified=proof['observed'],dataAudit=note,catalogEvidence=note,oddsParser=PARSER,oddsImportIssues=0,sourceObservation=dict(file=evidence['evidenceFile'],sha256=ph,source=sources['landing']));cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text());ip.write_text(json.dumps([r for r in inventory if r['slug']!=SLUG]+[record],ensure_ascii=False,indent=2)+'\n')
 rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=specs;registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG];registry['conflicts'].append(dict(slug=SLUG,family='Unjoined guide claims, specification-only Green and source units',gap=' '.join(proof['remainingGaps']),source=sources['landing'],**evidence));rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 print('VeeFriends: 711 numbered entries, 112 artist entries, 22 families, all 104 odds/eight formats, 33 exact specification joins and one guide-only Green parallel.')

if __name__=='__main__':build()
