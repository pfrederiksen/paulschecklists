"""Preserve Inception Basketball's original subject cells and scoped guide terms."""
import collections, hashlib, json, re
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire, text
from official_odds_layout import physical_odds_pdf

ROOT=Path(__file__).resolve().parents[1]; SLUG='topps-bowman-2025-26-topps-inception-basketball'
PARSER='scripts/import_topps_inception_basketball_2025.py'
PROOF=ROOT/'data/parallel-audit-sources/inception-basketball-2025-26-20261016.json'
HEADERS=['Checklist section','Card number','Name','Source page','Team','Rookie']
FAMILIES={'BASE CARDS':100,'ROOKIE AUTOGRAPHS':40,'ROOKIE AUTOGRAPHS HORIZONTAL VARIATIONS':20,
 'DAWN OF GREATNESS AUTOGRAPHS':20,'INCEPTION SILVER SIGNINGS':20,'FOUNTAIN OF YOUTH SIGNATURES':27,
 'RISE TO FAME SIGNATURES':24,'PERSISTANT MARKS':18,'ROOKIE JUMBO RELIC AUTOGRAPHS':39,
 'FRANCHISE FUNDAMENTAL RELIC AUTOGRAPHS':32,'DUAL ROOKIE RELIC AUTOGRAPHS':20,
 'ROOKIE RELIC BOOKLET AUTOGRAPHS':40,'NBA FIRST MILESTONE AUTOGRAPH RELICS':33,
 'NBA FIRST MILESTONE RELICS':5,'LAUNCH':20,'ENDGAME':10,'SPLASHDOWN':20}

def read_cards(path):
 rows=[];raw=[];notes=[];family=None
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==11
  for pn,page in enumerate(pdf.pages,1):
   raw.append(dict(page=pn,text=page.extract_text()));groups=collections.defaultdict(list)
   for c in page.chars:groups[round(c['top'],1)].append(c)
   for y,cs in sorted(groups.items()):
    line=text(cs)
    if pn==1 and y<98:notes.append([str(pn),line]);continue
    if all('Bold' in c['fontname'] for c in cs):
     if line in {'BASE','AUTOGRAPH','AUTOGRAPH RELIC','RELIC','INSERT'}:notes.append([str(pn),line])
     else:
      assert line in FAMILIES,(pn,line);family=line
     continue
    a=next(i for i,c in enumerate(cs) if abs(c['x0']-132.62)<.03)
    b=next(i for i,c in enumerate(cs) if abs(c['x0']-269.45)<.03)
    r=next((i for i,c in enumerate(cs) if abs(c['x0']-421.27)<.03),len(cs))
    number,name,team,rookie=[text(part) for part in [cs[:a],cs[a:b],cs[b:r],cs[r:]]]
    assert family and re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+',number) and name and team and rookie in {'','Rookie'},(pn,line)
    rows.append([family,number,name,str(pn),team,rookie])
 assert len(rows)==488 and len({tuple(r[:2]) for r in rows})==458
 assert collections.Counter(r[0] for r in rows)==FAMILIES and sum(r[5]=='Rookie' for r in rows)==268
 return rows,raw,notes

def build():
 proof=json.loads(PROOF.read_text());sources=proof['sources']
 evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=hashlib.sha256(PROOF.read_bytes()).hexdigest())
 cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());record=next(s for s in catalog['sets'] if s['slug']==SLUG)
 dp=ROOT/record['tableData'];data=json.loads(dp.read_text());path=ROOT/'data/catalog-sources/downloads'/(SLUG+'.pdf')
 sha=acquire(proof['checklistUrl'],path);rows,raw,notes=read_cards(path)
 op=path.with_name(SLUG+'-odds.pdf');oh=acquire(proof['oddsUrl'],op);original,formats,odds_raw,issues=physical_odds_pdf(op)
 assert (sha,oh)==(proof['checklistSha256'],proof['oddsSha256']) and len(original)==91 and formats==['Hobby','FDI'] and not issues
 assert acquire(proof['productOddsUrl'],path.with_name(SLUG+'-product-odds.pdf'))==oh
 aliases={f.title():f for f in FAMILIES};aliases.update({'Base':'BASE CARDS',
  'NBA First Milestone Autograph Relic Redemption':'NBA FIRST MILESTONE AUTOGRAPH RELICS',
  'NBA First Milestone Relic Redemption':'NBA FIRST MILESTONE RELICS'})
 odds=[]
 for item in original:
  prefix=next((a for a in sorted(aliases,key=len,reverse=True) if item['name'].casefold()==a.casefold() or item['name'].casefold().startswith(a.casefold()+' ')),None)
  assert prefix,item['name'];odds.append(dict(item,family=aliases[prefix],familyBase=item['name'].casefold()==prefix.casefold()))
 assert {o['family'] for o in odds}==set(FAMILIES)
 spec=lambda family,name,numbering,odds_name,qualification,heading:dict(family=family,name=name,numbering=numbering,
  **({'oddsName':odds_name} if odds_name else {}),source=sources['guide'],qualification=qualification,sourceHeading=heading,**evidence)
 specs=[spec('BASE CARDS',name,value,None if name=='Holo Gold' else 'Base '+name,
  'Published for this family; individual-card eligibility is not inferred. '+('Guide-only Holo Gold is not joined to the differently named Base Gold Electricity odds.' if name=='Holo Gold' else 'Guide-published base value; never applied to autograph families.'),
  'For Set Builders: Collect the Colorful World of Inception') for name,value in proof['baseGuide'] if name!='Inception']
 for family,name,value,qualification in proof['otherGuide']:
  specs.append(spec(family,name,value,family.title()+' '+name,qualification,'For Autograph Collectors: Discover Dynamic Ink' if family in {'INCEPTION SILVER SIGNINGS','ROOKIE AUTOGRAPHS'} else 'Relics: Rookies & More'))
 assert len(specs)==10 and sum(bool(s.get('oddsName')) for s in specs)==9
 for s in specs:
  if s.get('oddsName'):assert next(o for o in odds if o['name']==s['oddsName'])['family']==s['family']
 table=lambda name,headers,values,source:dict(name=name,headers=headers,rows=values,source=source,
  worksheet='Official source scope and units retained; examples are not universal limits',**evidence)
 published=[table('Manufacturer product fields',['Published field','Published value','Scope'],proof['productFields'],sources['product']),
  table('BASE CARDS',['Parallel / variation','Published statement','Qualification'],[['Inception','Limited to one-of-one','Published one-copy limit; serial marking is not explicitly stated. This is not assigned as serial numbering to the odds row.']],sources['guide']),
  table('DAWN OF GREATNESS AUTOGRAPHS',['Card number','Name','Parallel / variation','Published statement','Qualification'],[[*proof['cardExample'][1:]]],sources['guide']),
  table('NBA FIRST MILESTONE AUTOGRAPH RELICS',['Published statement','Qualification'],[[proof['interviewFields'][0][1],proof['interviewFields'][0][2]]],sources['interview']),
  table('Interview context',['Published field','Published value','Qualification'],proof['interviewFields'][1:],sources['interview'])]
 note=('All 488 physical subject rows / 458 family-card identities and 17 sections are reconciled, including 268 literal Rookie marks. '
  'Original Name/Team/Rookie cells, repeated dual/booklet signers, historical team assignments, Portland Trailblazers and Persistant Marks wording remain intact. '
  'All 91 Hobby/FDI odds retain original literals and nulls with unstated ratio units. Ten exact guide specifications include nine odds joins; Holo Gold /50 remains separate from Gold Electricity. '
  'Base Inception is a qualified one-copy print limit, not inferred serial marking. Cedric Coward DG-CC Blue /25 stays card-specific. '
  'Store July 23 availability and guide/interview publication do not establish an explicit general release date; other numbering and exhaustive parallel coverage remain unverified.')
 data.update(headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,rawPages=raw,sourceDocumentNotes=notes,
  unclassifiedLines=[],source=proof['checklistUrl'],sha256=sha,dedicatedParser=PARSER,importKind='pdf',coverageComplete=True,sectionColumn=0,
  odds=odds,formats=formats,officialOddsTable=original,officialOddsFormats=formats,officialOddsHeader=['Cards',*formats],
  oddsSource=proof['oddsUrl'],oddsSha256=oh,oddsRawPages=odds_raw,oddsIssues=issues,oddsParser='scripts/official_odds_layout.py',
  formatNamesPublished=True,oddsUnitsPublished=False,parallelSpecifications=specs,publishedSpecifications=published,
  supplementaryOddsSources=[dict(url=proof['productOddsUrl'],sha256=oh,qualification='Fresh product-linked bytes match landing/global odds.')],
  sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
 dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
 record.update(sourcePage=sources['landing'],rowCount=488,sections=17,sha256=sha,dedicatedParser=PARSER,coverageComplete=True,odds=91,formats=2,
  verified=proof['observed'],dataAudit=note,catalogEvidence=note,oddsParser='scripts/official_odds_layout.py',oddsImportIssues=0,
  sourceObservation=dict(file=evidence['evidenceFile'],sha256=evidence['evidenceSha256'],source=sources['guide']))
 cp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 ip=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(ip.read_text())
 inventory=[record if r['slug']==SLUG else r for r in inventory] if any(r['slug']==SLUG for r in inventory) else inventory+[record]
 ip.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 rp=ROOT/'data/parallel-specifications.json';registry=json.loads(rp.read_text());registry['sets'][SLUG]=specs
 registry['conflicts']=[c for c in registry['conflicts'] if c['slug']!=SLUG]+[dict(slug=SLUG,family='Unjoined names, card examples and print limits',gap=' '.join(proof['remainingGaps']),source=sources['guide'],**evidence)]
 rp.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 dates=ROOT/'data/release-dates.json';release=json.loads(dates.read_text());assert not any(e['slug']==SLUG for e in release['dates'])
 release['unresolved']=[e for e in release['unresolved'] if e['slug']!=SLUG]+[dict(slug=SLUG,
  gap='July 23 is store availability and guide/interview publication. The interview celebrates release day without explicitly stating a calendar release date; no general date is inferred.',
  sources=[dict(url=sources['product'],statement='Available From Jul 23, 2026; Product Year 2026, printed title 2025-26.',method='Actual official web read'),
   dict(url=sources['interview'],statement='Published Jul 23, 2026; introductory release-day wording has no explicit calendar date.',method='Actual complete official browser read')])]
 dates.write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n')
 print('Inception Basketball: 488 subjects / 458 identities / 268 Rookie marks, 91 literal Hobby/FDI odds, ten exact specifications and a strictly card-specific Coward example.')

if __name__=='__main__':build()
