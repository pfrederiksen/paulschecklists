"""Reconcile October checklist additions and product-linked Sapphire odds."""
import collections,hashlib,json,re,subprocess
from datetime import date
from pathlib import Path
import pdfplumber
from import_official_catalog import odds_pdf
ROOT=Path(__file__).resolve().parents[1]
PARSER='scripts/import_topps_october_backfills.py'
SAPPHIRE='topps-bowman-2025-topps-chrome-football-sapphire'
BOWMAN='topps-bowman-2026-bowman-u-best-football'
BASKETBALL='topps-bowman-2026-27-topps-flagship-basketball'
DISNEY='topps-bowman-2026-topps-mint-disney'
CONFIG={
 SAPPHIRE:dict(title='2025 Topps Chrome® Football Sapphire',year='2025',sport='football',origins=[132.62,269.45,421.27],columns=['Name','Team','Rookie'],pages=15,skip=105,count=740,sections=14,proof='football-sapphire-2025-product-20261014.json',source='https://www.topps.com/pages/topps-chrome-football-sapphire',url='https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2025_Chrome_Football_Sapphire_Checklist_042926.pdf?v=1778615660'),
 BOWMAN:dict(title='2026 Bowman U Best Football',year='2026',sport='football',origins=[133.32,351.96],columns=['Name','Team'],pages=29,skip=100,count=756,sections=22,proof='bowman-u-best-2026-guide-20261014.json',source='https://www.topps.com/pages/bowman-u-best-football',url='https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_Bowman_U_Best_FB_Checklist.pdf?v=1791206274'),
 BASKETBALL:dict(title='2026-27 Topps Flagship Basketball',year='2026-27',sport='basketball',origins=[128,257,400],columns=['Name','Team','Rookie'],pages=57,skip=100,count=3254,sections=64,proof='flagship-basketball-2026-guide-20261014.json',source='https://www.topps.com/pages/topps-flagship-basketball',url='https://cdn.shopify.com/s/files/1/0662/9749/5709/files/Copy_of_2026-27_Topps_Flagship_Basketball_Checklist_10-9-26.xls_-_Compatibility_Mode.pdf?v=1791570579'),
 DISNEY:dict(title='2026 Topps Mint Disney',year='2026',sport='disney',origins=[95.64,246.36,366.24],columns=['Name','Official text column 2','Official text column 3'],pages=10,skip=100,count=442,sections=15,proof='mint-disney-2026-product-20261014.json',source='https://www.topps.com/pages/topps-mint-disney',url='https://cdn.shopify.com/s/files/1/0662/9749/5709/files/26DSNM_Mint_Disney_CHECKLIST_FINAL_a5705acd-5d63-43f2-b4f6-ce1f457e2deb.pdf?v=1792171539'),
}
OUTER={'BASE','INSERT','INSERTS','AUTOGRAPH','AUTOGRAPHS','RELIC','RELICS','AUTOGRAPH RELIC','SKETCH'}
ARTISTS='SKETCH CARDS & MINTED SKETCH CARDS - ARTISTS'
def acquire(url,path):
 tmp=path.with_suffix('.part');subprocess.run(['curl','-sLf','--retry','2','--max-time','45',url,'-o',str(tmp)],check=True)
 tmp.replace(path);return hashlib.sha256(path.read_bytes()).hexdigest()
def read_cards(path,slug,cfg):
 rows=[];raw=[];section=None;unassigned=[]
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==cfg['pages']
  for pn,page in enumerate(pdf.pages,1):
   raw.append({'page':pn,'text':page.extract_text() or ''})
   # Group nearby baselines without sorting glyphs across overlapping cells.
   bands=[]
   for c in sorted(page.chars,key=lambda c:c['top']):
    if not bands or c['top']-bands[-1][0]>2:bands.append((c['top'],[]))
    bands[-1][1].append(c)
   for y,band in bands:
    if pn==1 and y<cfg['skip']:continue
    ids={id(c) for c in band};chars=[c for c in page.chars if id(c) in ids]
    text=''.join(c['text'] for c in chars).strip()
    if slug==BOWMAN and pn>16:
     assert text.strip('® ')==''
     if text:unassigned.append({'page':pn,'top':round(y,2),'text':text,'note':'Unattached trademark glyph; not a subject or inferred rookie flag.'})
     continue
    if slug==DISNEY and section==ARTISTS:
     # Artist cells have no printed card numbers, including all-uppercase
     # names and names whose letters happen to cross a table column origin.
     ordered=sorted(chars,key=lambda c:c['x0']);name=''
     for i,c in enumerate(ordered):
      if i and c['x0']-ordered[i-1]['x1']>2.5 and not name.endswith(' '):name+=' '
      name+=c['text']
     rows.append([section,'',name.strip(),'','',str(pn)]);continue
    # Some bold headings cross the exact Name origin (e.g. STARS OF NBA).
    # They remain complete captions, including numeric 1981/1990 prefixes.
    if chars and all('Bold' in c['fontname'] for c in chars):
     assert text==text.upper(),(pn,y,text)
     if text not in OUTER:section=text
     continue
    starts=[]
    for col,x in enumerate(cfg['origins'],1):
     matches=[i for i,c in enumerate(chars) if abs(c['x0']-x)<.03 or slug==DISNEY and col==2 and abs(c['x0']-246.304)<.005]
     if matches:starts.append((max(matches),col))
    assert starts and starts[0][1]==1,(slug,pn,y,text)
    cells=[''.join(c['text'] for c in chars[:starts[0][0]]).strip()]+['']*len(cfg['origins'])
    assert re.fullmatch(r'[A-Z0-9&-]*',cells[0]) and section,(slug,pn,y,cells)
    for j,(idx,col) in enumerate(starts):
     end=starts[j+1][0] if j+1<len(starts) else len(chars)
     cells[col]=''.join(c['text'] for c in chars[idx:end]).strip()
    if 'Rookie' in cfg['columns']:assert cells[-1] in ['', 'Rookie']
    rows.append([section,*cells,str(pn)])
 assert len(rows)==cfg['count'],(slug,len(rows))
 assert len({r[0] for r in rows})==cfg['sections'],(slug,len({r[0] for r in rows}))
 return rows,raw,unassigned

def proof_table(name,headers,rows,proof,source):
 return {'name':name,'worksheet':'Official guide; retain source units and scope','headers':headers,'rows':rows,'evidenceFile':str(proof.relative_to(ROOT)),'evidenceSha256':hashlib.sha256(proof.read_bytes()).hexdigest(),'source':source}
def bowman_card_examples(rows,sha):
 proof=ROOT/'data/parallel-audit-sources/bowman-u-best-football-2026-20261016-candidate.json'
 facts=json.loads(proof.read_text());assert facts['checklistSha256']==sha
 tables=[]
 for example in facts['examples']:
  identity=example['checklistIdentity']
  expected=[identity[k] for k in ['family','cardNumber','subject','team','sourcePage']]
  assert rows.count(expected)==1,expected
  tables.append(proof_table(identity['family'],['Card number','Subject','Parallel / variation','Published statement','Qualification','Official source'],[[identity['cardNumber'],identity['subject'],example['parallel'] or 'Not named in guide',example['publishedStatement'],example['qualification'],facts['source']]],proof,facts['source']))
 assert sum(r[0]=='CAMPUS CRESTS' for r in rows)==34
 return tables

def build(slugs=None):
 cp=ROOT/'data/set-catalog.json';catalog=json.loads(cp.read_text());known={s['slug']:s for s in catalog['sets']};replacements={}
 for slug,cfg in CONFIG.items():
  if slugs is not None and slug not in slugs:continue
  path=ROOT/'data/catalog-sources/downloads'/(slug+'.pdf');sha=acquire(cfg['url'],path)
  rows,raw,unassigned=read_cards(path,slug,cfg)
  record=known.get(slug,{'title':cfg['title'],'manufacturer':'Topps / Bowman','sport':cfg['sport'],'year':cfg['year'],'slug':slug,'page':'sets/'+slug+'.html','verified':'2026-10-14'})
  dp=ROOT/'data/imports'/(slug+'.json');data=json.loads(dp.read_text()) if dp.exists() else {}
  proof=ROOT/'data/parallel-audit-sources'/cfg['proof'];facts=json.loads(proof.read_text());source=facts['source'];specs=[]
  if slug==SAPPHIRE:
   op=path.with_name(slug+'-odds.pdf');osh=acquire(facts['oddsUrl'],op)
   full,formats,oraw,issues=odds_pdf(op);scope=facts['oddsScope']
   assert len(full)==505 and len(formats)==14 and not issues and scope in formats
   # Exact, audited family joins preserve distinct veteran and rookie odds.
   aliases={'BASE IMAGE VARIATION':'BASE CARDS IMAGE VARIATION','BASE':'BASE CARDS','ROOKIE IMAGE VARIATION':'ROOKIES IMAGE VARIATION','ROOKIE VARIATION AUTOGRAPHS':'ROOKIES AUTOGRAPH VARIATION','SAPPHIRE SELECTIONS AUTOGRAPHS':'SAPPHIRE SELECTION AUTOGRAPHS'}
   families={r[0] for r in rows};aliases.update({f:f for f in families if f not in aliases})
   odds=[]
   for odd in full:
    if odd['values'][scope] is None:continue
    prefix=next((p for p in sorted(aliases,key=len,reverse=True) if odd['name']==p or odd['name'].startswith(p+' ')),None)
    assert prefix,odd['name']
    odd.update(family=aliases[prefix],familyBase=odd['name'] in [prefix,prefix+' SAPPHIRE'])
    odds.append({**odd,'values':{scope:odd['values'][scope]}})
   assert len(odds)==55 and {o['family'] for o in odds}==families
   # Retain all original labels and values; joins add metadata only.
   data.update(odds=odds,formats=[scope],officialOddsTable=full,officialOddsFormats=formats,oddsScope=scope,oddsSource=facts['oddsUrl'],oddsSha256=osh,oddsRawPages=oraw,oddsIssues=[],oddsParser='scripts/official_odds_layout.py')
   record.update(oddsUrl=facts['oddsUrl'],odds=55,formats=1,oddsImportIssues=0,oddsParser=data['oddsParser'])
   note='All 740 printed subject rows and 14 sections reconciled, including 300 Base Cards, 100 Rookie rows, 252 printed Rookie marks and all repeated dual signers. The year-leading 1990 autograph heading is a caption. Only the 55 published Sapphire-column odds are displayed; all 505 categories and 14 original columns are retained. Exhaustive parallel-numbering review and calendar release date remain unverified.'
  elif slug==BOWMAN:
   specs=[proof_table('Hobby box configuration (contents, not pack odds)',['Published field','Published value','Official source'],[[*r,source] for r in facts['configuration']],proof,source)]
   specs.extend(bowman_card_examples(rows,sha))
   note='All 756 physical subject rows across 22 sections reconciled, representing 676 distinct family/card-number pairs; repeated dual, quad and six-signer rows remain separate. All 100 base numbers and original school spellings are retained. Trailing pages contain only unattached trademark glyphs, preserved separately. No rookie field is published. Five guide-scoped base limits and box contents are imported; no pack-odds PDF verified and the full parallel inventory remains pending.'
   record['description']='A 100-card college football base set, school and mascot inserts, and autographs with up to six printed signers. Published base parallel limits and Hobby box contents are available; pack odds and the full parallel audit remain pending.'
   note+=' The October 16 collector guide’s three named print-limit examples are reconciled only to base 16, BOA-KT and BM-OSU; no serial marking or family-wide limits are inferred.'
  elif slug==BASKETBALL:
   specs=[proof_table('Box configurations (contents, not pack odds)',['Published format','Published configuration','Official source'],[[*r,source] for r in facts['configuration']],proof,source),proof_table('Guide-described parallel programs',['Published program','Published limit','Source qualification','Official source'],[[*r,source] for r in facts['parallelPrograms']],proof,source)]
   note='All 3,254 physical subject rows across 64 sections reconciled, retaining 300 base numbers, all 45 printed base Rookie marks and 60 numbered Fanatics Authentic Redemption entries. Bold headings that cross the Name origin remain captions. Printed team assignments and repeated signers remain unchanged. The guide describes 40 base rookies, while the PDF marks 45; the PDF flags are retained. Box contents and qualified guide specifications are not pack odds; exhaustive parallel reconciliation is pending.'
   record['description']='A 300-card NBA base checklist with 45 printed rookie flags, Blackout and image variations, inserts, autographs and relics. Browse original player and team fields, plus the manufacturer’s box configurations; pack odds remain unavailable.'
  else:
   note='All 374 numbered Disney entries and 68 unnumbered sketch artists are reconciled, retaining actor/character/property text columns and the full sketch-artist roster, including mixed Japanese/Latin names. Paper and Chrome base tiers remain separate; apparent printed spellings, case and clipped property text are preserved. Only the product-page Platinum starting numbering is imported; pack odds and exhaustive parallel-numbering reconciliation remain pending.'
   record['description']='Four paper base tiers and their separate Chrome variations, Minted Posters, Minted in Magic, actor autographs and an unnumbered sketch-artist roster. Published Platinum starting numbering is available; pack odds and further parallel limits remain pending.'
  data.update(title=cfg['title'],headers=['Checklist section','Card number',*cfg['columns'],'Source page'],rows=rows,rawPages=raw,unassignedPhysicalText=unassigned,unclassifiedLines=[],source=cfg['url'],sha256=sha,sectionColumn=0,importKind='topps-grid-pdf',dedicatedParser=PARSER,publishedSpecifications=specs,productConfigurationEvidence={'file':str(proof.relative_to(ROOT)),'sha256':hashlib.sha256(proof.read_bytes()).hexdigest(),'source':source},sourceSheets=[{'name':'Official source reconciliation','notes':[[note]]}])
  if slug==DISNEY:
   alternate_proof=ROOT/'data/parallel-audit-sources/mint-disney-global-alternate-20261019.json'
   alternate=json.loads(alternate_proof.read_text())['facts']
   alternate_path=path.with_name(slug+'-global-alternate.pdf')
   assert acquire(alternate['globalUrl'],alternate_path)==alternate['globalSha256']
   alternate_rows,_,_=read_cards(alternate_path,slug,cfg)
   differences=[dict(rowIndex=i,primary=a,globalAlternate=b) for i,(a,b) in enumerate(zip(rows,alternate_rows)) if a!=b]
   assert len(alternate_rows)==len(rows)==442 and differences==alternate['differences']
   assert sha==alternate['primarySha256'] and cfg['url']==alternate['primaryUrl']
   data['sourceVariantReview']=dict(file=str(alternate_proof.relative_to(ROOT)),sha256=hashlib.sha256(alternate_proof.read_bytes()).hexdigest())
   data['sourceVariantDifferences']=differences
   data['sourceSheets'].append(dict(name='Official global/product checklist variants',notes=[
    ['The product page still links this imported primary PDF. The current global checklist index links a different PDF with the same 442 rows and 15 sections. Both are retained without silently resolving their text differences.'],
    ['MINTED IN MAGIC MM-PL Pluto: the primary prints Mickey & Friends; the global alternate prints Mickey and Friends.'],
    ['CS-CN Clarence Nash: the primary heading prints CLARENCE NASH DONALD DUCK CUT SIGNATURE; the global alternate heading prints CLEARANCE NASH DONALD DUCK CUT SIGNATURE.'],
    ['No other original card/name/property/artist cells differ in the complete physical-column comparison.']]))
   record['additionalSources']=[dict(label='Official global checklist variant',url=alternate['globalUrl'])]
   record['globalCatalogUrl']=alternate['globalUrl']
  dp.write_text(json.dumps(data,ensure_ascii=False)+'\n')
  record.update(verified=date.today().isoformat(),sourcePage=cfg['source'],checklistUrl=cfg['url'],status='Source table',tableData=str(dp.relative_to(ROOT)),rowCount=len(rows),sections=cfg['sections'],sha256=sha,importKind=data['importKind'],dedicatedParser=PARSER,catalogEvidence=note,dataAudit=note)
  if 'releaseDate' in facts:record.update(releaseStatus='Upcoming',releaseDate=facts['releaseDate'],releaseEvidence=source)
  else:record.update(releaseStatus='Unverified',releaseDate=None)
  replacements[slug]=record
  print(cfg['title'],len(rows),'physical rows,',cfg['sections'],'sections')
 for name in ['set-catalog.json','topps-product-official-catalog.json']:
  p=ROOT/'data'/name;c=json.loads(p.read_text());items=c['sets'] if isinstance(c,dict) else c;present={s['slug'] for s in items}
  items[:]=[replacements.get(s['slug'],s) for s in items];items.extend(s for slug,s in replacements.items() if slug not in present)
  p.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
 # Keep the manufacturer discovery inventory in sync without removing old sets.
 p=ROOT/'data/topps-official-catalog.json';inventory=json.loads(p.read_text())
 for slug,cfg in CONFIG.items():
  if not any(r['url']==cfg['url'] for r in inventory):inventory.append({'id':slug,'title':cfg['title'],'url':cfg['url']})
 p.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 p=ROOT/'data/topps-official-odds.json';registry=json.loads(p.read_text())
 if SAPPHIRE in replacements and not any(r['title']==CONFIG[SAPPHIRE]['title'] for r in registry):registry.append({'title':CONFIG[SAPPHIRE]['title'],'url':replacements[SAPPHIRE]['oddsUrl'],'sourcePage':CONFIG[SAPPHIRE]['source'],'scope':'6394 - NFL- CHROME 2025 SAPPHIRE HOBBY DISTRIBUTOR'})
 p.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--slug',choices=CONFIG,action='append')
 build(parser.parse_args().slug)
