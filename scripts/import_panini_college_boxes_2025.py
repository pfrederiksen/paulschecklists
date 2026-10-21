"""Physical official Texas/Ohio checklists; printed placeholders and units remain literal."""
import json,hashlib,urllib.request,io
from pathlib import Path
import pdfplumber,re,collections
FAMILIES=['College Contenders','Legendary Contenders','School Colors','Campus Legends','Prizm','Prizm Student Orientation','Prizm Fearless','Prizm Fireworks','Prizm Trophy Hunting','On Campus','Profiles','Color Blast','Thunder','Private Signings Cracked Ice','College Ties Dual Autograph','NIL Autograph']
def ohio_parse(path):
 rows=[];guides=[];raw=[];notes=[];family=None;last=None
 with pdfplumber.open(io.BytesIO(path) if isinstance(path,bytes) else path) as doc:
  assert len(doc.pages)==4
  for pn,page in enumerate(doc.pages,1):
   text=page.extract_text();raw.append({'page':pn,'text':text})
   for line in text.splitlines():
    head=re.sub(r' \(\d+-\d+\)$','',line)
    if head in FAMILIES:family=head;last=None;continue
    if line.startswith('2025 Panini Ohio State NIL - ') or line=='Parallels:':continue
    if line=='0':notes.append({'page':pn,'text':line,'qualification':'Standalone printed source value without card number or subject; no card identity inferred.'});continue
    if family and line.startswith(family+' '):guides.append({'family':family,'literal':line,'page':pn});continue
    m=re.fullmatch(r'(\d+|[A-Z]+(?:-\d+)?|-) (.+?)(?: (SP|SSP))?',line)
    if m:
     number,subject,mark=m.groups();qualification='Printed placeholder; card number and subject unresolved; no sequential number inferred.' if number=='-' else ''
     rows.append([family,number,subject,mark or '',str(pn),family,qualification]);last=number;continue
    assert family=='College Ties Dual Autograph' and last is not None,(pn,family,line)
    rows.append([family,last,line,'',str(pn),family,'Second printed signer on the same card.'])
 return rows,guides,raw,notes
def texas_parse(path):
 rows=[];columns=[];headings=[];family=None;heading=None
 with pdfplumber.open(io.BytesIO(path) if isinstance(path,bytes) else path) as doc:
  assert len(doc.pages)==2
  for pn,page in enumerate(doc.pages,1):
   assert (page.width,page.height)==(720,576)
   for l,r in [(30,195),(195,360),(360,525),(525,690)]:
    text=page.crop((l,75,r,545 if pn==1 or l==30 else 510)).extract_text();columns.append({'page':pn,'left':l,'right':r,'text':text})
    for line in text.splitlines():
     if re.fullmatch(r'[A-Z ]+',line):
      heading=line;family=line+(' · page 2' if line=='SCHOOL COLORS' and pn==2 else '');headings.append({'family':family,'printedHeading':line,'page':pn});continue
     m=re.fullmatch(r'[\uf0a3□]\s*(\S+)\s+(.+?)(?:\s+(SSP|SP))?',line);assert m,(pn,l,line)
     number,subject,mark=m.groups();assert family is not None
     rows.append([family,number,subject,mark or '',str(pn),heading,''])
 return rows,columns,headings
ROOT=Path(__file__).resolve().parents[1]
SOURCES={
 'texas':{'slug':'panini-2025-panini-texas-box-set-entertainment','url':'https://assets.paniniamerica.net/checklist/2025%20UT%20Checklist.pdf','sha256':'16c57483d56387e3806c6394f0cda743a55fb3f680319e663ef3ef8a7a3cc8df','title':'2025 Panini University of Texas NIL'},
 'ohio':{'slug':'panini-2025-panini-ohio-state-box-set-entertainment','url':'https://assets.paniniamerica.net/checklist/2/0/2025_ohio_state_media_checklist.pdf','sha256':'67f48053c0142eb44e1458dd033efaf4498058deb1ee043a9807273600c95c9b','title':'2025 Panini Ohio State NIL'}
}
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def main():
 catalog_path=ROOT/'data/set-catalog.json';inventory_path=ROOT/'data/panini-official-catalog.json';catalog=json.loads(catalog_path.read_text());inventory=json.loads(inventory_path.read_text())
 proof_path=ROOT/'data/official-panini/college-boxes-pdf-observations-20261021-1700.json';oldproof=json.loads(proof_path.read_text()) if proof_path.exists() else None
 proof={'observed':'2026-10-21','sourceKind':'official-product-linked-pdf','method':'Fresh official product-page links, original PDF fetches and physical text parsing; rendered first pages checked visually. Four-column Texas text preserves source order and repeated captions; Ohio retains original single-column rows, literal numbering/qualifiers and multi-signer continuations. No OCR-derived facts.','sources':[]}
 results={}
 for key,source in SOURCES.items():
  raw=urllib.request.urlopen(source['url'],timeout=40).read();sha=hashlib.sha256(raw).hexdigest();assert sha==source['sha256'],'Review revised PDF before replacing retained evidence'
  pdf='data/official-panini/'+source['slug']+'.pdf';(ROOT/pdf).write_bytes(raw)
  if key=='texas':rows,columns,headings=texas_parse(raw);guides=[];notes=[];assert len(rows)==219 and len(headings)==16
  else:rows,guides,columns,notes=ohio_parse(raw);headings=[{'family':x,'printedHeading':x} for x in FAMILIES];assert len(rows)==243 and len(guides)==119
  ui=(oldproof and next(x['productPage'] for x in oldproof['sources'] if x['key']==key)) or json.loads(Path('/tmp/panini-'+key+'-product-20261021-1700.json').read_text())
  proof['sources'].append({'key':key,'url':source['url'],'file':pdf,'sha256':sha,'bytes':len(raw),'rows':len(rows),'families':len(set(r[0] for r in rows)),'productPage':ui,'guideRows':guides,'notes':notes})
  results[key]=(rows,columns,headings,guides,notes,ui)
 if oldproof:assert proof==oldproof,'Revised reviewed evidence requires reconciliation'
 else:write(proof_path,proof)
 evidence={'file':str(proof_path.relative_to(ROOT)),'sha256':hashlib.sha256(proof_path.read_bytes()).hexdigest(),'source':'Official product-linked PDF'}
 scope_path=ROOT/'data/parallel-audit-sources/panini-college-boxes-2025-20261021-1700.json'
 scope={'observed':'2026-10-21','sourceObservation':evidence,'source':SOURCES['ohio']['url'],'review':'Every literal Ohio guide term reconciled against the physical PDF; only unambiguous printed # to digits become structured limits. Exact printed families retained. Autograph eligibility by individual subject remains unverified; no pack odds inferred. Texas SP/SSP marks and box averages supply no numeric ladder.','literalGuideRows':results['ohio'][3],'unresolvedNumbering':[g for g in results['ohio'][3] if '# to None/' in g['literal']],'exhaustiveParallelEligibilityComplete':False}
 if scope_path.exists():assert json.loads(scope_path.read_text())==scope
 else:write(scope_path,scope)
 guide_evidence={'file':str(scope_path.relative_to(ROOT)),'sha256':hashlib.sha256(scope_path.read_bytes()).hexdigest()}
 registry_path=ROOT/'data/parallel-specifications.json';registry=json.loads(registry_path.read_text())
 for key,source in SOURCES.items():
  rows,columns,headings,guides,notes,ui=results[key];slug=source['slug'];prior=next(r for r in catalog['sets'] if r['slug']==slug)
  csv_evidence=prior.get('headerOnlyCsvEvidence') or {'file':prior['sourceObservation']['file'],'sha256':prior['sourceObservation']['sha256'],'sourceExport':prior['sourceExport'],'exportSha256':prior['sha256']}
  if key=='texas':
   note='All 219 physical subject rows / 16 sections are imported from the official Texas PDF, including both printed SCHOOL COLORS programs, missing Prizm number 3, repeated autograph codes and both signers printed on every College Ties row. The second SCHOOL COLORS caption is distinguished by source page, not renamed from inference. All 18 SP and 18 SSP marks are literal; neither supplies serial numbering or pack odds. The source YEAR 2025 / Entertainment / Score selector is retained separately from the PDF title and product classification. Original header-only CSV remains retained. A general release date, numeric serial ladder and exhaustive parallel eligibility remain unverified.'
  else:
   note='All 243 physical subject/source rows / 16 sections and all 119 literal family guide terms are imported. Three printed dash placeholders remain explicit unresolved number/subject fields; no missing 49 or TH-8 is inferred. The standalone printed 0 has no card identity and is retained as source context. All ten College Ties duals retain both signers. Fifteen malformed # to None/... autograph terms are retained literally without selecting a serial limit. Only 68 unambiguous printed # to values are mapped, within their exact named families; autograph eligibility is not inferred from the base roster. The PDF title says 2025 and its printed 7/23/25 is a document date, while the store heading says 2024-25 and its URL says 2025-26; this product-year conflict is unresolved. General release date and exhaustive guide reconciliation remain unverified. The header-only CSV and original Entertainment / Score selector remain retained.'
  specs=[];mapped=[]
  for family in dict.fromkeys(x['family'] for x in guides):
   entries=[]
   for g in [x for x in guides if x['family']==family]:
    literal=g['literal'];name=literal[len(family)+1:];m=re.search(r'\(# to ([^)]+)\)',name);numbering=m[1] if m else None
    label=re.sub(r' \(# to [^)]+\)','',name);qual='Hobby Exclusive' if '- Hobby Exclusive' in label else 'Retail Exclusive' if '- Retail Exclusive' in label else 'Format not stated';label=re.sub(r' - (?:Hobby|Retail) Exclusive$','',label)
    malformed=numbering is not None and not numbering.isdigit();qualification='Malformed literal numbering; no selected numeric serial limit.' if malformed else 'Named family only; individual-card autograph/parallel eligibility not inferred.'
    entries.append([label,'# to '+numbering if numbering else 'Not published',qual,literal,str(g['page']),qualification])
    if numbering and numbering.isdigit():mapped.append({'family':family,'name':label,'numbering':'# to '+numbering,'qualification':qualification+' '+qual+'. Original printed term: '+literal,'sourceHeading':family,'source':source['url'],'evidenceFile':guide_evidence['file'],'evidenceSha256':guide_evidence['sha256']})
   specs.append({'name':family,'headers':['Published parallel','Literal numbering','Published format qualifier','Original specification','Source page','Scope / qualifier'],'rows':entries,'source':source['url'],'evidenceFile':evidence['file'],'evidenceSha256':evidence['sha256']})
  if key=='ohio':assert len(mapped)==68;registry['sets'][slug]=mapped
  elif slug in registry['sets']:raise ValueError('Texas PDF has no numeric ladder')
  context=[['Product title',source['title'],'Original PDF title; not a release date',ui['url']]]
  if key=='texas':
   context += [[field,value,scope,ui['url']] for field,value,scope in [
    ('Cards per pack','6','Hobby configuration'),('Packs per box','6','Hobby configuration'),('Boxes per case','20','Hobby configuration'),
    ('Autographs','2 per box, on average','Hobby box average; not pack odds'),('Prizm Camo','1 per box, on average','Hobby box average; no card-specific eligibility inferred'),('Diamond Plate','1 per box, on average','Hobby box average; no card-specific eligibility inferred'),('Panini Parallels','2 per box, on average','Hobby box average; no serial limit stated'),
    ('Profiles / Thunder','Hobby exclusive SSP inserts','Product-level statement; no numeric odds or serial limit')]]
  else:
   context += [[field,value,scope,ui['url']] for field,value,scope in [
    ('Store title','2024-25 Panini The Ohio State University NIL','Conflicts with 2025 PDF title and 2025-26 store URL; unresolved'),
    ('Cards per pack','4','Retail Blaster configuration'),('Packs per box','6','Retail Blaster configuration'),('Boxes per case','20','Retail Blaster configuration'),('Exclusive parallels','3 per box, on average','Retail Blaster box average; not pack odds'),
    ('Red, White, and Blue / Donuts / Neon Green','Retail Blaster exclusive','Product-level statement; exact family labels and limits come only from the PDF')]]
  specs.append({'name':'Manufacturer context: '+key,'headers':['Field','Value','Scope / qualifier','Official source'],'rows':context,'source':ui['url'],'evidenceFile':evidence['file'],'evidenceSha256':evidence['sha256']})
  if key=='ohio':
   article_path=ROOT/'data/parallel-audit-sources/ohio-state-announcement-20261021-1700.json';article=json.loads(article_path.read_text())
   assert hashlib.sha256(json.dumps(article['facts'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==article['factsSha256']
   specs.append({'name':'Manufacturer context: Ohio State announcement','headers':['Field','Value','Scope / qualifier','Official source'],'rows':[[*r,article['source']] for r in article['facts']],'source':article['source'],'evidenceFile':str(article_path.relative_to(ROOT)),'evidenceSha256':hashlib.sha256(article_path.read_bytes()).hexdigest()})
  payload={'title':source['title'],'source':source['url'],'sha256':source['sha256'],'importKind':'panini-pdf','dedicatedParser':'scripts/import_panini_college_boxes_2025.py','headers':['Checklist section','Card number','Player / subjects','Published SP / SSP mark','Source page','Original heading','Source qualification'],'rows':rows,'sectionColumn':0,'coverageComplete':key=='texas','sourceObservation':evidence,'headerOnlyCsvEvidence':csv_evidence,'rawColumns' if key=='texas' else 'rawPages':columns,'printedHeadings':headings,'publishedSpecifications':specs,'sourceNotes':notes,'sourceSheets':[{'name':'Official source reconciliation','notes':[[note]],'source':ui['url']}]}
  dest='data/imports/'+slug+'.json';(ROOT/dest).write_text(json.dumps(payload,ensure_ascii=False)+'\n')
  record={'title':source['title'],'slug':slug,'page':'sets/'+slug+'.html','manufacturer':'Panini','sport':'multi-sport','year':'2025','sourceYear':'2025','sourceSelection':prior['sourceSelection'],'sourcePage':ui['url'],'checklistUrl':source['url'],'releaseStatus':'Unverified','releaseDate':None,'verified':'2026-10-21','checklistFirstObserved':'2026-10-21','status':'Source table','tableData':dest,'rowCount':len(rows),'sections':16,'parallelData':key=='ohio','publishedOdds':False,'importKind':'panini-pdf','dedicatedParser':payload['dedicatedParser'],'sha256':source['sha256'],'coverageComplete':key=='texas','sourceObservation':evidence,'headerOnlyCsvEvidence':csv_evidence,'catalogEvidence':note,'dataAudit':note}
  for collection in [catalog['sets'],inventory]:collection[next(i for i,r in enumerate(collection) if r['slug']==slug)]=record
  print(source['title'],len(rows),'physical rows;',len(guides),'literal terms;',len(mapped),'exact-family numeric mappings')
 write(catalog_path,catalog);write(inventory_path,inventory);write(registry_path,registry)
if __name__=='__main__':main()
