"""Import original Neon Marvel glyph columns and all literal ruled odds cells."""
import collections,hashlib,json,re
from pathlib import Path
import pdfplumber
import import_official_catalog as generic
ROOT=generic.ROOT;SLUG='topps-bowman-2026-topps-neon-marvel';PARSER='scripts/import_topps_marvel_neon_2026.py'
PROOF=ROOT/'data/parallel-audit-sources/marvel-neon-2026-product-guides-20261020.json'
HEADERS=['Checklist section','Card number','Name','Unlabelled text column 2','Source page']
UMBRELLAS={'BASE VARIATIONS','INSERT','CASE HITS','LENTICULAR','AUTOGRAPH','BOX TOPPERS'}
def parse_cards(path):
 rows=[];raw=[];family=None
 with pdfplumber.open(path) as pdf:
  for pn,page in enumerate(pdf.pages,1):
   raw.append({'page':pn,'text':page.extract_text() or ''});groups=collections.defaultdict(list)
   for c in page.chars:groups[round(c['matrix'][5],2)].append(c)
   for y,cs in sorted(groups.items(),reverse=True):
    text=lambda chars:''.join(c['text'] for c in chars).strip()
    if pn==1 and y>730:continue
    if all('Bold' in c['fontname'] for c in cs):
     if text(cs) not in UMBRELLAS:family=text(cs)
     continue
    if family=='SKETCH CARD ARTISTS':rows.append([family,'',text(cs),'',str(pn)]);continue
    ni=next((i for i,c in enumerate(cs) if abs(c['x0']-132.62)<.03),None);assert ni is not None,(pn,y,text(cs))
    number=text(cs[:ni]);assert re.fullmatch(r'\d+|[A-Z0-9]+-[A-Z0-9-]+',number),(pn,y,text(cs))
    ai=next((i for i,c in enumerate(cs) if i>ni and abs(c['x0']-269.45)<.03),len(cs))
    rows.append([family,number,text(cs[ni:ai]),text(cs[ai:]),str(pn)])
 assert len(rows)==866 and sum(bool(r[1]) for r in rows)==730
 assert len({tuple(r[:2]) for r in rows if r[1]})==710 and len({r[0] for r in rows})==20
 return rows,raw
def parse_odds(path):
 odds=[];raw=[];formats=None
 with pdfplumber.open(path) as pdf:
  for pn,page in enumerate(pdf.pages,1):
   raw.append({'page':pn,'text':page.extract_text() or ''});tables=page.find_tables();assert len(tables)==1
   table=tables[0].extract();assert table[0][0]=='Card'
   if formats is None:formats=table[0][1:]
   else:assert formats==table[0][1:]
   for row in table[1:]:
    assert len(row)==6 and all(v=='-' or re.fullmatch(r'[\d,X]+:[\d,X]+',v) or v=='-\n1:832' for v in row[1:]),row
    odds.append({'name':' '.join(row[0].split()),'values':dict(zip(formats,[None if v=='-' else v for v in row[1:]])),'page':pn})
 assert len(odds)==133 and formats==['HOBBY','VALUE BOX','MEGA BOX','SUPER BOX BONUS PACK','SUPER BOX']
 aliases={'BASE CARDS SUPER BOX DESIGN':'BASE SUPER BOX DESIGN VARIATION','BASE CARDS':'BASE','CHROME NEON ETCH BASE':'CHROME NEON ETCH BASE VARIATION','MARVEL RIVALS BASE IMAGE VARIATION':'MARVEL RIVALS IMAGE VARIATION SHORT PRINT','1-UP':'1 UP','FRIENDLY NEIGHBORHOOD SPIDER-MAN':'FRIENDLY NEIGHBORHOOD SPIDER MAN','GIANT-SIZED BOOKLET AUTOS':'GIANT SIZED BOOKLET AUTOGRAPHS','MANGA MADNESS AUTOS':'MANGA MADNESS AUTOGRAPH VARIATION','NEIGHBORHOOD SPIDER-MAN AUTOS':'FRIENDLY NEIGHBORHOOD SPIDER MAN VOICE ACTOR AUTOS','SKETCH CARDS':'Sketch Cards (artist eligibility unverified)'}
 for o in odds:
  if o['name']=='MARVEL SNAP XL GOLD FOIL':
   assert o['values']['SUPER BOX']=='-\n1:832'
   o['qualification']='The original SUPER BOX cell contains a dash above 1:832. Both are retained; no single value is selected.'
  prefix=next((a for a in sorted(aliases,key=len,reverse=True) if o['name']==a or o['name'].startswith(a+' ')),None)
  if prefix:o.update(family=aliases[prefix],familyBase=o['name']==prefix)
 return odds,formats,raw
def build():
 proof=json.loads(PROOF.read_text());facts=proof['facts'];assert hashlib.sha256(json.dumps(facts,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==proof['factsSha256']
 evidence=dict(evidenceFile=str(PROOF.relative_to(ROOT)),evidenceSha256=hashlib.sha256(PROOF.read_bytes()).hexdigest())
 record=dict(title='2026 Topps Neon Marvel',manufacturer='Topps / Bowman',sport='marvel',year='2026',slug=SLUG,page='sets/'+SLUG+'.html',sourcePage=facts['product'],checklistUrl=proof['checklistUrl'],oddsUrl=proof['oddsUrl'],releaseStatus='Unverified',releaseDate=None)
 # Register the product-only official documents for generic discovery refreshes.
 for file,key,url in [('data/entertainment-topps-catalog.json','url',proof['checklistUrl']),('data/entertainment-topps-odds.json','url',proof['oddsUrl'])]:
  p=ROOT/file;items=json.loads(p.read_text())
  if not any(r.get(key)==url for r in items):items.append(dict(title=record['title'],url=url,sourcePage=facts['product'],sourceKind='official-product-only-document'))
  p.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
 generic.ODDS[generic.norm(record['title'])]={'title':record['title'],'url':proof['oddsUrl']}
 if not (ROOT/'data/imports'/(SLUG+'.json')).exists():generic.run(dict(record))
 cp=generic.CACHE/(SLUG+'.pdf');op=generic.CACHE/(SLUG+'-odds.pdf')
 cb=generic.fetch(proof['checklistUrl'],cp);ob=generic.fetch(proof['oddsUrl'],op)
 assert hashlib.sha256(cb).hexdigest()==proof['checklistSha256'] and hashlib.sha256(ob).hexdigest()==proof['oddsSha256']
 rows,raw=parse_cards(cp);odds,formats,oraw=parse_odds(op)
 spec=dict(family='BASE',name='FoilFractor',numbering='1/1',oddsName='BASE CARDS FOILFRACTOR',source=facts['guide'],qualification='The collector guide names one-of-one FoilFractors in its Base Set section. No other family inherits this limit.',**evidence)
 tables=[dict(name=f,worksheet='Official collector guide',headers=['Card number','Published subject','Published quantity','Qualification'],rows=[[n,s,v,q]],source=facts['guide'],**evidence) for f,n,s,v,q in facts['cardSpecificExamples']]
 note=('All 730 numbered physical subjects / 710 family-card identities and 136 unnumbered artists are retained across 20 families. Original unlabelled text columns change meaning by family and are not reinterpreted as teams. Repeated 1 UP and Marquee Motion subjects remain separate. All 133 odds categories and five exact headings are preserved, including three 1:XX placeholders, the original dash plus 1:832 cell and Super Box Bonus Pack 5:1. No ratio unit is printed, so no pack rate is calculated. Only the base FoilFractor 1/1 is mapped. Guide five-copy Spider-Man and ten-copy Chrome Silver Surfer examples have no named parallel or serial marking. Calendar release and exhaustive numbering remain unverified.')
 data=dict(title=record['title'],headers=HEADERS,rows=rows,originalSubjectHeaders=HEADERS,originalSubjectRows=rows,source=proof['checklistUrl'],sha256=proof['checklistSha256'],rawPages=raw,importKind='pdf',sectionColumn=0,dedicatedParser=PARSER,coverageComplete=True,odds=odds,formats=formats,oddsSource=proof['oddsUrl'],oddsSha256=proof['oddsSha256'],oddsRawPages=oraw,oddsIssues=[],officialOddsTable=[dict(o) for o in odds],officialOddsFormats=formats,officialOddsHeader=['Card',*formats],formatNamesPublished=True,oddsUnitsPublished=False,parallelSpecifications=[],publishedSpecifications=tables,sourceSheets=[dict(name='Official source reconciliation',notes=[[note],*[[g] for g in proof['remainingGaps']]])])
 path='data/imports/'+SLUG+'.json';(ROOT/path).write_text(json.dumps(data,ensure_ascii=False)+'\n')
 record.update(tableData=path,status='Source table',importKind='pdf',dedicatedParser=PARSER,rowCount=866,sections=20,odds=133,formats=5,parallelData=True,publishedOdds=True,coverageComplete=True,sha256=proof['checklistSha256'],verified=proof['observed'],dataAudit=note,catalogEvidence=note,sourceObservation=dict(file=evidence['evidenceFile'],sha256=evidence['evidenceSha256'],source=facts['guide']),additionalSources=[{'label':'Official collector guide','url':facts['guide']},{'label':'Official product history','url':facts['history']}])
 p=ROOT/'data/set-catalog.json';catalog=json.loads(p.read_text());catalog['sets']=[r for r in catalog['sets'] if r['slug']!=SLUG]+[record];p.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 p=ROOT/'data/topps-product-official-catalog.json';items=json.loads(p.read_text());items=[r for r in items if r['slug']!=SLUG]+[record];p.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
 p=ROOT/'data/parallel-specifications.json';registry=json.loads(p.read_text());registry['sets'][SLUG]=[spec];registry['conflicts']=[r for r in registry['conflicts'] if r['slug']!=SLUG]+[dict(slug=SLUG,family='Other numbering, card-specific quantities and placeholder odds',gap=' '.join(proof['remainingGaps']),source=facts['guide'],**evidence)];p.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
 print('Neon Marvel: 730 numbered subjects / 710 identities, 136 artists, 20 families, 133 literal five-column odds, three 1:XX placeholders and one exact base 1/1 join.')
if __name__=='__main__':build()
