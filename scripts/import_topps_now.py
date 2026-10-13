"""Import observed official Topps NOW product snapshots; never imply archive completeness.
Refresh data/catalog-sources/topps-now-products.txt using official web reads first.
The direct Topps endpoint currently denies automated downloads. Snapshots are retained
as evidence; re-running this parser alone does not constitute a fresh source check.
"""
import re,json,hashlib,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE='https://www.topps.com/collections/topps-now'
ARCHIVE=SOURCE+'-archive'
raw=(ROOT/'data/catalog-sources/topps-now-products.txt').read_text()
starts=list(re.finditer(r'^[^\n]*\((https://www\.topps\.com/products/[^)]+)\)\n',raw,re.M))
products={}
for i,m in enumerate(starts):
 block=raw[m.start():starts[i+1].start() if i+1<len(starts) else len(raw)]
 lines=[x.strip() for x in re.split(r'L\d+(?:@P\d+)?:\s*',block)[1:]]
 lines=[re.sub(r'\ue200cite\ue202[^\ue201]*\ue201','',x).strip() for x in lines]
 title=next((x.removeprefix('## ') for x in lines if x.startswith('## ') and ' - Card ' in x),None)
 if not title:continue
 match=re.fullmatch(r'(.+?) - (20\d\d(?:-\d\d)? .+?NOW®.*?) - Card ([A-Za-z0-9-]+)(?: - PR: ([\d,]+))?',title)
 if not match:raise ValueError('Unrecognized official product title: '+title)
 name,series,number,pr=match.groups();fields={}
 for line in lines:
  if '  | ' in line:
   key,value=line.split('  | ',1);fields[key.strip()]=value.splitlines()[0].strip()
 sale=re.search(r'Product is available from ([A-Za-z]+ \d{1,2}, \d{4}) and expires on ([A-Za-z]+ \d{1,2}, \d{4})', '\n'.join(lines))
 if sale:
  fields.setdefault('Available From',sale[1]);fields.setdefault('Available Until',sale[2])
 if fields.get('Subjects'):name=fields['Subjects']
 pr=pr or fields.get('Print Run','')
 if pr and not re.fullmatch(r'[\d,]+',pr):raise ValueError('Unrecognized print run '+pr)
 # Preserve the literal source overview, including per-card thresholds and qualifiers.
 begin=next((j for j,x in enumerate(lines) if x=='Overview'),None)
 end=next((j for j,x in enumerate(lines) if x=='Specs'),len(lines))
 overview='\n'.join(lines[begin+1:end]) if begin is not None else ''
 # Publish concise factual specifications, not the store's marketing copy.
 look_for=[x.removeprefix('* ') for x in lines[begin+1:end] if x.startswith('* ') and not x.startswith('*Parallels')] if begin is not None else []
 tiers=[x for x in lines[begin+1:end] if re.match(r'^[\d,]+\+ Print Run:',x)] if begin is not None else []
 factual=[]
 if look_for:factual.append('Published card types: '+ '; '.join(look_for))
 if '*Parallels or other non-base' in overview:factual.append('A non-base card replaces the ordered base card; allocation depends on total orders. Numeric pack odds are not published.')
 factual.extend(tiers)
 overview='\n'.join(factual)
 parallel_start=next((j for j,x in enumerate(lines) if x=='Parallels:'),None)
 parallels=[]
 if parallel_start is not None:
  for line in lines[parallel_start+1:]:
   if not line:continue
   if not re.match(r'^/\d+\s+|^1/1\s+',line):break
   parallels.append(line)
 key=(series,number)
 evidence={'url':m[1],'sha256':hashlib.sha256('\n'.join(lines).encode()).hexdigest(),'observed':datetime.datetime.fromtimestamp((ROOT/'data/catalog-sources/topps-now-products.txt').stat().st_mtime).date().isoformat(),'title':title,'fields':fields,'overview':overview}
 p={'series':series,'number':number,'name':name,'printRun':pr,'saleFrom':fields.get('Available From',''),'saleUntil':fields.get('Available Until',''),'parallels':parallels,'terms':overview,'source':m[1],'evidence':evidence}
 if key in products:
  old=products[key]
  assert old['name']==name,(old,p)
  if old['printRun'] and not pr:continue
 products[key]=p
assert len(products)>=40,'Incomplete snapshot; do not overwrite prior observations'
store=ROOT/'data/topps-now-observations.json'
previous=json.loads(store.read_text()) if store.exists() else []
merged={(p['series'],p['number']):p for p in previous};merged.update(products)
products=sorted(merged.values(),key=lambda p:(p['series'],not p['number'].isdigit(),int(p['number']) if p['number'].isdigit() else p['number']))
store.write_text(json.dumps(products,ensure_ascii=False,indent=2)+'\n')
headers=['Checklist section','Card number','Player / subjects','Published print run','Available From','Available Until','Published parallels','Official distribution terms','Official product URL']
def publish(slug,title,items,sport,year):
 rows=[[p['series'],p['number'],p['name'],p['printRun'],p['saleFrom'],p['saleUntil'],'; '.join(p['parallels']),p['terms'],p['source']] for p in items]
 specs=[]
 for series in dict.fromkeys(p['series'] for p in items):
  specrows=[[p['number'],p['name'],value,p['source']] for p in items if p['series']==series for value in p['parallels']]
  if specrows:specs.append({'name':series,'worksheet':'Official product pages · applies only to the specified card','headers':['Card number','Subject','Published parallel','Official product URL'],'rows':specrows})
 fingerprint=hashlib.sha256(json.dumps([(p['source'],p['evidence']['sha256']) for p in items],ensure_ascii=False).encode()).hexdigest()
 path='data/imports/'+slug+'.json'
 payload={'title':title,'headers':headers,'rows':rows,'source':ARCHIVE,'sha256':fingerprint,'importKind':'topps-now','sectionColumn':0,'metricColumn':3,'metricLabel':'PRINT RUN','publishedSpecifications':specs,'sourceProducts':[p['evidence'] for p in items],'coverageComplete':False}
 (ROOT/path).write_text(json.dumps(payload,ensure_ascii=False)+'\n')
 return {'title':title,'slug':slug,'page':'sets/'+slug+'.html','manufacturer':'Topps / Bowman','sport':sport,'year':year,'sourcePage':SOURCE,'checklistUrl':ARCHIVE,'tableData':path,'status':'Source table','importKind':'topps-now','dedicatedParser':'scripts/import_topps_now.py','ongoingSeries':True,'coverageComplete':False,'releaseStatus':'Ongoing','releaseDate':None,'rowCount':len(rows),'sections':len(set(r[0] for r in rows)),'parallelData':bool(specs),'publishedOdds':False,'sha256':fingerprint,'verified':max(p['evidence']['observed'] for p in items),'catalogEvidence':'Partial archive: observed active listings and the first official archive page only. Earlier cards and other NOW series remain to be imported; pagination is currently inaccessible. Original sale dates, published print runs, per-card parallels and distribution terms are retained. Blank print runs mean not published in the observed source. Print runs are not pack odds.','dataAudit':'Each imported number, subject, date, print run and parallel is reconciled to retained official product text; duplicate archive listings merge by series and card number.'}
records=[publish('topps-now-2026','2026 Topps NOW & Bowman NOW',products,'multi-sport','2026')]
for series in dict.fromkeys(p['series'] for p in products):
 year=re.match(r'20\d\d(?:-\d\d)?',series)[0]
 sport='wrestling' if 'WWE' in series else 'baseball' if 'MLB' in series else 'soccer' if 'MLS' in series else 'football' if any(x in series for x in ['NFL','Football']) else 'multi-sport'
 records.append(publish('topps-now-'+re.sub('[^a-z0-9]+','-',series.lower()).strip('-'),series,[p for p in products if p['series']==series],sport,year))
(ROOT/'data/topps-now-official-catalog.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
p=ROOT/'data/set-catalog.json';catalog=json.loads(p.read_text());new={r['slug']:r for r in records};catalog['sets']=[r for r in catalog['sets'] if r['slug'] not in new]+records;p.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
print('Imported',len(products),'observed cards;',sum(bool(p['printRun']) for p in products),'published print runs;',len(records),'shared pages')
