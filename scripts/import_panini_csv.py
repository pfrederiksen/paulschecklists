"""Import untouched CSV exports downloaded through Panini's official checklist UI."""
import csv, hashlib, json, re, shutil, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE='https://www.paniniamerica.net/checklist.html'
catalog_path=ROOT/'data/set-catalog.json'
catalog=json.loads(catalog_path.read_text())
inventory_path=ROOT/'data/panini-official-catalog.json'
inventory=json.loads(inventory_path.read_text())
observation_sources=[(p,json.loads(p.read_text())) for p in sorted((ROOT/'data/official-panini').glob('*observations*.json'))]
for filename in sys.argv[1:]:
 source=Path(filename);raw=source.read_bytes()
 reader=csv.reader(raw.decode('utf-8-sig').splitlines());headers=next(reader);original=list(reader)
 assert headers==['SPORT','YEAR','BRAND','PROGRAM','CARD SET','ATHLETE','TEAM','POSITION','CARD NUMBER','SEQUENCE']
 assert original and all(len(row)==len(headers) for row in original)
 sport,year,brand,program=original[0][:4]
 assert all(row[:4]==[sport,year,brand,program] for row in original)
 title=f'{year} Panini {program} {sport}'
 slug='panini-'+re.sub('[^a-z0-9]+','-',title.lower()).strip('-')
 product_year=year
 season=re.search(r' \((\d{2})-(\d{2})\)$',program)
 if season and year.endswith(season[1]):
  product_year=year+'-'+season[2];title=f'{product_year} Panini {program[:season.start()]} {sport}'
 archive=ROOT/'data/official-panini'/f'{slug}.csv';archive.parent.mkdir(exist_ok=True);shutil.copyfile(source,archive)
 digest=hashlib.sha256(raw).hexdigest()
 rows=[[r[4],r[8],r[5],r[9],*r] for r in original]
 specs=[]
 for family in dict.fromkeys(r[4] for r in original):
  values=[[r[8],r[5],r[9]] for r in original if r[4]==family and r[9]]
  if values:specs.append({'name':family,'worksheet':'Official CSV SEQUENCE column; serial numbering is not pack odds','headers':['Card number','Athlete','Published SEQUENCE'],'rows':values})
 payload={'title':title,'source':SOURCE,'sha256':digest,'importKind':'panini-csv','dedicatedParser':'scripts/import_panini_csv.py','headers':['Checklist section','Card number','Player / subjects','Published SEQUENCE',*headers],'rows':rows,'sectionColumn':0,'metricColumn':3,'metricLabel':'NUMBERING','publishedSpecifications':specs,'coverageComplete':True,'rawHeaders':headers,'sourceExport':str(archive.relative_to(ROOT)),'sourceSelection':{'sport':sport,'year':year,'brand':brand,'program':program}}
 path=f'data/imports/{slug}.json'
 audit=f'All {len(rows):,} rows from the official Panini CSV export are retained, including all original columns, literal card-set parallel names and SEQUENCE values. Empty numbering is not an estimate. Pack odds are absent from this export. Product year does not establish a release date.'
 record={'title':title,'slug':slug,'page':f'sets/{slug}.html','manufacturer':'Panini','sport':sport.lower(),'year':year,'sourcePage':SOURCE,'checklistUrl':SOURCE,'releaseStatus':'Unverified','releaseDate':None,'verified':'2026-10-13','status':'Source table','tableData':path,'rowCount':len(rows),'sections':len(set(r[0] for r in rows)),'parallelData':True,'publishedOdds':False,'importKind':'panini-csv','dedicatedParser':'scripts/import_panini_csv.py','sha256':digest,'coverageComplete':True,'sourceExport':str(archive.relative_to(ROOT)),'sourceSelection':payload['sourceSelection'],'catalogEvidence':audit,'dataAudit':audit}
 if product_year!=year:
  record.update(year=product_year,sourceYear=year);payload.update(sourceYear=year,productYear=product_year)
 matched=next(((p,document,o) for p,document in observation_sources for o in document.get('exports',[]) if o['sha256']==digest and o['sourceSelection']==payload['sourceSelection']),None)
 observation=matched[2] if matched else None
 if observation:
  observation_file,observations,_=matched
  evidence={'file':str(observation_file.relative_to(ROOT)),'sha256':hashlib.sha256(observation_file.read_bytes()).hexdigest(),'source':SOURCE,'method':observations['method']}
  payload.update(sourceObservation=evidence,checklistFirstObserved=observations['observed'])
  record.update(verified=observations['observed'],checklistFirstObserved=observations['observed'],sourceObservation=evidence)
  audit+=' This export was observed in the official interface on '+observations['observed']+'; that observation is not a release date. Printed card-set identities naming other products are retained. Full product-guide and calendar-release reconciliation remain pending.'
  payload['sourceSheets']=[{'name':'Official source reconciliation','notes':[[audit]]}]
  record.update(catalogEvidence=audit,dataAudit=audit)
  if program=='EuroLeague Origins (25-26)':
   guide=observations['releaseEvidence'][1]['source']
   payload['publishedSpecifications'].append({'name':'Manufacturer box contents and qualified numbering range','worksheet':'Official June 18, 2026 announcement; averages are not pack odds','headers':['Published field','Published value','Official source'],'rows':[[*r,guide] for r in observations['euroleagueOriginsSpecifications']],'source':guide,'evidenceFile':evidence['file'],'evidenceSha256':evidence['sha256']})
 (ROOT/path).write_text(json.dumps(payload,ensure_ascii=False)+'\n')
 for collection in [catalog['sets'],inventory]:
  collection[:]=[r for r in collection if r['slug']!=slug and not (r.get('dedicatedParser')=='scripts/import_panini_csv.py' and r.get('sourceSelection')==payload['sourceSelection'])];collection.append(record)
 print(title,len(rows),'rows',sum(s['headers']==['Card number','Athlete','Published SEQUENCE'] for s in specs),'numbered families')
catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
inventory_path.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
