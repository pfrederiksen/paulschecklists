"""Import observed official Topps NOW product snapshots; never imply archive completeness.
Refresh data/catalog-sources/topps-now-products.txt using official web reads first.
The direct Topps endpoint currently denies automated downloads. Snapshots are retained
as evidence; re-running this parser alone does not constitute a fresh source check.
"""
import re,json,hashlib,datetime
from pathlib import Path
from urllib.parse import urlparse,unquote
ROOT=Path(__file__).resolve().parents[1]
SOURCE='https://www.topps.com/collections/topps-now'
ARCHIVE=SOURCE+'-archive'
store=ROOT/'data/topps-now-observations.json'
previous=json.loads(store.read_text()) if store.exists() else []
us_product_keys={unquote(urlparse(p['source']).path):(p['series'],p['number']) for p in previous if p['source'].startswith('https://www.topps.com/products/')}
snapshot=ROOT/'data/catalog-sources/topps-now-products.txt'
documents=sorted([p for p in [snapshot,*list((ROOT/'data/catalog-sources').glob('topps-now-backfill-*.txt')),*list((ROOT/'data/catalog-sources').glob('topps-now-backfill-browser-*.json'))] if p.exists()],key=lambda p:p.stat().st_mtime)
blocks=[]
def preserve_missing_fields(product, old):
 """Carry forward published facts together with their original evidence."""
 for field in ['printRun','saleFrom','saleUntil','parallels','terms']:
  if not product[field] and old[field]:
   product[field]=old[field]
   proof=old.get('fieldEvidence',{}).get(field,old['evidence'])
   if field=='printRun':
    proof=next((e for e in old.get('archiveEvidence',[]) if re.search(r'PR:\s*[\d,]+',e['title'])),proof)
   if proof['sha256']!=product['evidence']['sha256']:
    product.setdefault('fieldEvidence',{})[field]=proof
 return product
for document in documents:
 if document.suffix=='.json':
  observed=json.loads(document.read_text())
  assert observed['sourceKind']=='official-browser-product'
  for product in observed['products']:
   assert product['lines'] and product['url'].startswith('https://www.topps.com/products/')
   # These lines are retained accessibility text read on the official page,
   # not facts reconstructed from a URL or an archive ordering.
   raw=product['lines'][0]+' ('+product['url']+')\n'+'\n'.join('L'+str(i)+': '+line for i,line in enumerate(product['lines']))+'\n'
   blocks.append((product['url'],raw,document))
  continue
 raw=document.read_text();starts=list(re.finditer(r'^[^\n]*\((https://(?:www|uk|uk-next|fr)\.topps\.com/products/[^)]+)\)\n',raw,re.M))
 for i,m in enumerate(starts):blocks.append((m[1],raw[m.start():starts[i+1].start() if i+1<len(starts) else len(raw)],document))
products={};unparsed=[];unverified_print_runs=[]
for url,block,document in blocks:
 lines=[x.strip() for x in re.split(r'L\d+(?:@P\d+)?:\s*',block)[1:]]
 lines=[re.sub(r'\ue200cite\ue202[^\ue201]*\ue201','',x).strip() for x in lines]
 titles=[x for x in lines if (' - Card ' in x or ' - Sticker # ' in x) and re.search(r' - 20\d\d.*NOW®',x)]
 title=next((x.removeprefix('## ') for x in titles if x.startswith('## ')),titles[0] if titles else None)
 if not title:continue
 match=re.fullmatch(r'(.+?) - (20\d\d(?:-\d\d)? .+?NOW®.*?) - (?:Card |Sticker # )([A-Za-z0-9-]+?)(?: \([^)]*\))?(?: Pack)?\s*(?:-?\s*PR:\s*([\d,]+))?(?: Pack)?',title)
 unlabelled_suffix=None
 if not match:
  # An explicit Card number remains usable when an unlabelled numeric
  # suffix follows it. That suffix is not a published print-run claim.
  suffix_match=re.fullmatch(r'(.+?) - (20\d\d(?:-\d\d)? .+?NOW®.*?) - Card ([A-Za-z0-9-]+?) - ([\d,]+)',title)
  if suffix_match:
   name,series,number,unlabelled_suffix=suffix_match.groups();pr=None
   unverified_print_runs.append({'url':url,'title':title,'series':series,'number':number,'unlabelledValue':unlabelled_suffix,'gap':'The official title does not label this numeric suffix as a print run; no print run is assigned from it.'})
 if not match and unlabelled_suffix is None:
  unparsed.append({'url':url,'title':title,'gap':'Official title lacks a validated number or has conflicting/unrecognized numbering or print-run text; preserve the gap instead of inferring from the URL.'})
  continue
 if match:name,series,number,pr=match.groups()
 number=number.rstrip('-');fields={}
 if not number:
  unparsed.append({'url':url,'title':title,'gap':'Card number is blank in the official product title.'});continue
 for line in lines:
  if '  | ' in line:
   key,value=line.split('  | ',1);fields[key.strip()]=value.splitlines()[0].strip()
 for original,normalized in [('Disponible À Partir De','Available From'),("Disponible Jusqu'à",'Available Until'),('Sujets','Subjects')]:
  if original in fields:fields.setdefault(normalized,fields[original])
 sale=re.search(r'Product is available from ([A-Za-z]+ \d{1,2}, \d{4}) and expires on ([A-Za-z]+ \d{1,2}, \d{4})', '\n'.join(lines))
 if sale:
  fields.setdefault('Available From',sale[1]);fields.setdefault('Available Until',sale[2])
 else:
  sale_start=re.search(r'^Product is available from ([A-Za-z]+ \d{1,2}, \d{4})$', '\n'.join(lines),re.M)
  if sale_start:fields.setdefault('Available From',sale_start[1])
 if fields.get('Subjects'):name=fields['Subjects']
 pr=pr or fields.get('Print Run','')
 if pr and not re.fullmatch(r'[\d,]+',pr):raise ValueError('Unrecognized print run '+pr)
 # Preserve the literal source overview, including per-card thresholds and qualifiers.
 begin=next((j for j,x in enumerate(lines) if x=='Overview'),None)
 end=next((j for j,x in enumerate(lines) if x=='Specs'),len(lines))
 overview='\n'.join(lines[begin+1:end]) if begin is not None else ''
 # Publish concise factual specifications, not the store's marketing copy.
 parallel_heading=next((j for j,x in enumerate(lines) if x.startswith('Parallels:') or x in {'Parallels :','Parallèles :'}),end)
 look_for=[x.removeprefix('* ') for x in lines[begin+1:min(end,parallel_heading)] if (x.startswith('* ') or re.match(r'^/\d+\s+.*(?:Redemption|Card)',x)) and not x.startswith('*Parallels')] if begin is not None else []
 tiers=[x for x in lines[begin+1:end] if re.match(r'^[\d,]+\+ Print Run:',x)] if begin is not None else []
 factual=[]
 if look_for:factual.append(('Published sticker types: ' if ' - Sticker # ' in title else 'Published card types: ')+ '; '.join(look_for))
 if '*Parallels or other non-base' in overview:
  unit='sticker' if 'non-base sticker' in overview else 'card'
  factual.append(f'A non-base {unit} replaces the ordered base {unit}; allocation depends on total orders. Numeric pack odds are not published.')
 factual.extend(tiers)
 if unlabelled_suffix is not None:
  factual.append(f'Official title ends with unlabelled value {unlabelled_suffix}; its meaning is unverified and no print run is assigned from it.')
 if urlparse(url).hostname=='fr.topps.com':
  factual.extend(x for x in lines[begin+1:end] if x.startswith('*Les cartes parallèles') or x.startswith('Tirage de '))
 overview='\n'.join(factual)
 parallel_start=next((j for j,x in enumerate(lines) if x in {'Parallels:','Parallels :','Parallèles :'}),None)
 parallels=[]
 if parallel_start is not None:
  for line in lines[parallel_start+1:]:
   if not line:continue
   if not re.match(r'^/\d+\s+|^1/1\s+',line):break
   parallels.append(line)
 else:
  inline=next((line.removeprefix('Parallels:').strip() for line in lines if line.startswith('Parallels:')),None)
  if inline:
   parallels=[part.strip() for part in re.split(r'(?=/(?:\d+)\s|1/1\s)',inline) if re.match(r'^/\d+\s|^1/1\s',part.strip())]
  elif document.suffix=='.json' or urlparse(url).hostname=='fr.topps.com':
   # Browser accessibility can omit a visual Parallels heading. Retain
   # the literal named foil/ice parallels; redemption-card limits are
   # separate Look for terms and must not become parallel names.
   parallels=[x.removeprefix('* ').strip() for x in lines[begin+1:end] if re.match(r'^/\d+\s+',x.removeprefix('* ')) and ('Foil' in x or 'FoilFractor' in x or 'Ice Parallel' in x or urlparse(url).hostname=='fr.topps.com' and re.search(r'Feuille|foil',x,re.I))]
 key=(series,number)
 if urlparse(url).hostname!='www.topps.com' and us_product_keys.get(unquote(urlparse(url).path),key)!=key:
  unparsed.append({'url':url,'title':title,'gap':'Regional product series or card number conflicts with the retained U.S. archive identity for the same product path; do not merge its dates or create a duplicate card.'})
  continue
 evidence={'url':url,'sha256':hashlib.sha256('\n'.join(lines).encode()).hexdigest(),'observed':datetime.datetime.fromtimestamp(document.stat().st_mtime).date().isoformat(),'title':title,'fields':fields,'overview':overview}
 if unlabelled_suffix is not None:evidence['unlabelledTitleSuffix']=unlabelled_suffix
 if document.suffix=='.json':evidence.update(sourceKind='official-browser-product',snapshotFile=str(document.relative_to(ROOT)))
 p={'series':series,'number':number,'name':name,'printRun':pr,'saleFrom':fields.get('Available From',''),'saleUntil':fields.get('Available Until',''),'parallels':parallels,'terms':overview,'source':url,'evidence':evidence}
 if key in products:
  old=products[key]
  # Official Subjects cells supersede abbreviated product titles.
  if old['name']!=name and not fields.get('Subjects'):p['name']=old['name']
  if old['printRun'] and not pr:
   if not any(p[f] and not old[f] for f in ['saleFrom','saleUntil','parallels','terms']):continue
  preserve_missing_fields(p,old)
 products[key]=p
# Archive titles are official observations too. They can fill card numbers and
# printed runs when a product renderer returns only its loading shell. They do
# not supply sale dates, parallel eligibility or distribution terms.
archive_index=ROOT/'data/topps-now-archive-index.json'
if archive_index.exists():
 archive=json.loads(archive_index.read_text())
 for page in archive['pages']:
  for line in page['lines']:
   title=line.split(', Value:',1)[0]
   title=re.sub(r'^(?:\d+ link )','',title)
   title=re.sub(r' (?:Look for .*?|Sold out)(?: Sold out)?$','',title)
   match=re.fullmatch(r'(.+?) - (20\d\d(?:-\d\d)? .+?NOW®.*?) - (?:Card |Sticker # )([A-Za-z0-9-]+?)(?: \([^)]*\))?(?: Pack)?\s*(?:-?\s*PR:\s*([\d,]+))?(?: Pack)?',title)
   if not match:continue
   name,series,number,pr=match.groups();number=number.rstrip('-');key=(series,number)
   if not number:continue
   link=re.search(r', Value: (topps\.com/products/\S+)',line)
   source='https://www.'+link[1] if link else (page.get('url') or ARCHIVE)
   evidence={'url':source,'sha256':hashlib.sha256(title.encode()).hexdigest(),'observed':archive['observed'],'title':title,'fields':{},'overview':'','sourceKind':'official-archive-title'}
   p={'series':series,'number':number,'name':name,'printRun':pr or '', 'saleFrom':'','saleUntil':'','parallels':[],'terms':'','source':source,'evidence':evidence}
   if key not in products:products[key]=p
assert len(products)>=40 or not documents,'Incomplete snapshot; do not overwrite prior observations'
merged={(p['series'],p['number']):p for p in previous if p['number']}
for key,p in products.items():
 if key in merged:
  old=merged[key]
  if p['evidence'].get('sourceKind')=='official-archive-title' and old['evidence'].get('sourceKind')!='official-archive-title':
   if not old['printRun'] and p['printRun']:old['printRun']=p['printRun'];old.setdefault('archiveEvidence',[]).append(p['evidence'])
   continue
  preserve_missing_fields(p,old)
 merged[key]=p
assert merged,'No official observations available; refresh snapshots before importing'
products=sorted(merged.values(),key=lambda p:(p['series'],not p['number'].isdigit(),int(p['number']) if p['number'].isdigit() else p['number']))
def official_sale_date(value):
 if not value:return None
 japanese=re.fullmatch(r'(\d{4})年(\d{1,2})月(\d{1,2})日',value)
 if japanese:return datetime.date(*map(int,japanese.groups())).isoformat()
 text=re.sub(r'\bde\b','',value.lower()).replace('.','').replace(',','').split()
 if len(text)!=3:return None
 months={'jan':1,'january':1,'januar':1,'janvier':1,'gen':1,'ene':1,'feb':2,'february':2,'februar':2,'mar':3,'march':3,'märz':3,'apr':4,'april':4,'abr':4,'may':5,'mai':5,'mag':5,'jun':6,'june':6,'juni':6,'juin':6,'giu':6,'jul':7,'july':7,'juli':7,'juil':7,'lug':7,'aug':8,'august':8,'ago':8,'sep':9,'sept':9,'september':9,'set':9,'oct':10,'october':10,'okt':10,'nov':11,'november':11,'dec':12,'december':12,'dez':12}
 month,day,year=(text[0],text[1],text[2]) if text[0] in months else (text[1],text[0],text[2])
 if month not in months:return None
 return datetime.date(int(year),months[month],int(day)).isoformat()
for product in products:product['saleFromISO']=official_sale_date(product['saleFrom'])
store.write_text(json.dumps(products,ensure_ascii=False,indent=2)+'\n')
cutoff='2026-01-01'
pending=[{'series':p['series'],'number':p['number'],'url':p['source'],'saleFrom':p['saleFrom'],'gap':'Official sale date not yet verified; excluded from the calendar-year backfill.'} for p in products if not p['saleFromISO']]
excluded=[{'series':p['series'],'number':p['number'],'saleFromISO':p['saleFromISO'],'url':p['source']} for p in products if p['saleFromISO'] and p['saleFromISO']<cutoff]
(ROOT/'data/topps-now-import-gaps.json').write_text(json.dumps({'coverageComplete':False,'backfillStart':cutoff,'unparsedNumberedTitles':unparsed,'unverifiedPrintRuns':unverified_print_runs,'pendingSaleDates':pending,'excludedBeforeCutoff':excluded,'archivePaginationScanComplete':bool(archive.get('paginationScanComplete')) if archive_index.exists() else False,'remaining':'Missing product URLs, unverified sale dates, renderer-only product pages, non-numbered bundles and entertainment products still require reconciliation.'},ensure_ascii=False,indent=2)+'\n')
products=[p for p in products if p['saleFromISO'] and p['saleFromISO']>=cutoff]
headers=['Checklist section','Card number','Player / subjects','Published print run','Available From','Available Until','Published parallels','Official distribution terms','Official product URL']
def publish(slug,title,items,sport,year):
 rows=[[p['series'],p['number'],p['name'],p['printRun'],p['saleFrom'],p['saleUntil'],'; '.join(p['parallels']),p['terms'],p['source']] for p in items]
 specs=[]
 for series in dict.fromkeys(p['series'] for p in items):
  specrows=[[p['number'],p['name'],value,p['source']] for p in items if p['series']==series for value in p['parallels']]
  if specrows:specs.append({'name':series,'worksheet':'Official product pages · applies only to the specified card','headers':['Card number','Subject','Published parallel','Official product URL'],'rows':specrows})
 fingerprints=[(p['source'],p['evidence']['sha256'],*[(field,proof['url'],proof['sha256']) for field,proof in sorted(p.get('fieldEvidence',{}).items())]) for p in items]
 fingerprint=hashlib.sha256(json.dumps(fingerprints,ensure_ascii=False).encode()).hexdigest()
 path='data/imports/'+slug+'.json'
 payload={'title':title,'headers':headers,'rows':rows,'source':ARCHIVE,'sha256':fingerprint,'importKind':'topps-now','sectionColumn':0,'metricColumn':3,'metricLabel':'PRINT RUN','publishedSpecifications':specs,'sourceProducts':[p['evidence'] for p in items],'coverageComplete':False}
 supplementary=[{'series':p['series'],'number':p['number'],'field':field,'value':p[field],'evidence':proof} for p in items for field,proof in sorted(p.get('fieldEvidence',{}).items())]
 if supplementary:payload['supplementarySourceProducts']=supplementary
 (ROOT/path).write_text(json.dumps(payload,ensure_ascii=False)+'\n')
 return {'title':title,'slug':slug,'page':'sets/'+slug+'.html','manufacturer':'Topps / Bowman','sport':sport,'year':year,'sourcePage':SOURCE,'checklistUrl':ARCHIVE,'tableData':path,'status':'Source table','importKind':'topps-now','dedicatedParser':'scripts/import_topps_now.py','ongoingSeries':True,'coverageComplete':False,'releaseStatus':'Ongoing','releaseDate':None,'rowCount':len(rows),'rosterPublished':bool(rows),'backfillStart':cutoff,'sections':len(set(r[0] for r in rows)),'parallelData':bool(specs),'publishedOdds':False,'sha256':fingerprint,'verified':max((p['evidence']['observed'] for p in items),default=datetime.date.today().isoformat()),'catalogEvidence':'Partial calendar-year archive: only entries with a verified official sale date on or after January 1, 2026 are included. Entries without a verified sale date remain pending. Official active products, individual product pages and captured pages of the Product Year 2026 archive supply the evidence. All 95 archive pages have been visited; individual entries and product details still require reconciliation, and some product pages return only a loading shell. Archive-only observations retain the printed number, subject and print run; dates and parallel terms appear only where verified on the product page. Non-numbered bundles and entertainment products need separate reconciliation. Product year and season labels do not establish a calendar-year release date. Blank print runs mean not published in the observed source. Print runs are not pack odds.','dataAudit':'Each imported number, subject, date, print run and parallel is reconciled to retained official product text; duplicate archive listings merge by series and card number.'}
records=[publish('topps-now-2026','2026 Topps NOW & Bowman NOW',products,'multi-sport','2026')]
for series in dict.fromkeys(p['series'] for p in products):
 year=re.match(r'20\d\d(?:-\d\d)?',series)[0]
 sport='tennis' if 'Tennis' in series else 'wrestling' if 'WWE' in series else 'baseball' if any(x in series for x in ['MLB','World Baseball Classic']) else 'hockey' if 'NHL' in series else 'soccer' if any(x in series for x in ['MLS','UCL','UWCL','UECL','UEL','Premier League','Bundesliga','UEFA Nations League','FC Barcelona','Chelsea FC','Liverpool FC','Paris Saint-Germain','Argentina']) else 'basketball' if any(x in series for x in ['NBA','Basketball']) else 'football' if any(x in series for x in ['NFL','Football']) else 'multi-sport'
 records.append(publish('topps-now-'+re.sub('[^a-z0-9]+','-',series.lower()).strip('-'),series,[p for p in products if p['series']==series],sport,year))
previous_inventory=[s for s in json.loads((ROOT/'data/set-catalog.json').read_text())['sets'] if s.get('ongoingSeries')]
for old in previous_inventory:
 if old['slug'] not in {r['slug'] for r in records}:records.append(publish(old['slug'],old['title'],[],old['sport'],old['year']))
(ROOT/'data/topps-now-official-catalog.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
p=ROOT/'data/set-catalog.json';catalog=json.loads(p.read_text());new={r['slug']:r for r in records};existing={r['slug'] for r in catalog['sets']};catalog['sets']=[new.get(r['slug'],r) for r in catalog['sets']]+[r for r in records if r['slug'] not in existing];p.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
print('Imported',len(products),'observed cards;',sum(bool(p['printRun']) for p in products),'published print runs;',len(records),'shared pages')
