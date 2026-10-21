"""Retain explicitly unpopulated official Panini exports without inventing cards."""
import csv, hashlib, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HEADERS=['SPORT','YEAR','BRAND','PROGRAM','CARD SET','ATHLETE','TEAM','POSITION','CARD NUMBER','SEQUENCE']
SOURCE='https://www.paniniamerica.net/checklist.html'
def export_state(headers,rows):
 if headers!=HEADERS:raise ValueError('Unexpected official CSV columns')
 if not rows:return 'header-only'
 if len(rows)==1 and len(rows[0])==10 and rows[0][5:]==['Default','No Team','Miscellaneous','1','']:
  return 'placeholder-only'
 return 'populated'
def import_pending(path):
 proof_path=Path(path);proof=json.loads(proof_path.read_text());assert proof['sourceKind']=='official-browser-csv-exports'
 reference={'file':str(proof_path.relative_to(ROOT)),'sha256':hashlib.sha256(proof_path.read_bytes()).hexdigest(),'source':SOURCE,'method':proof['method']}
 catalog_path=ROOT/'data/set-catalog.json';inventory_path=ROOT/'data/panini-official-catalog.json';catalog=json.loads(catalog_path.read_text());inventory=json.loads(inventory_path.read_text())
 for observed in proof['exports']:
  selection=observed['sourceSelection'];raw=(ROOT/observed['sourceExport']).read_bytes();assert hashlib.sha256(raw).hexdigest()==observed['sha256']
  parsed=list(csv.reader(raw.decode('utf-8-sig').splitlines()));state=export_state(parsed[0],parsed[1:]);assert state==observed['exportState'] and state!='populated'
  assert observed['verifiedRosterRows']==0
  title=f"{selection['year']} Panini {selection['program']} {selection['sport']}";slug='panini-'+re.sub('[^a-z0-9]+','-',title.lower()).strip('-')
  previous=next((x for x in catalog['sets'] if x['slug']==slug),None)
  if previous and previous.get('tableData'):
   print('Preserved successfully imported roster: '+slug)
   continue
  if state=='placeholder-only':
   assert parsed[1][:4]==[selection[k] for k in ['sport','year','brand','program']]
   gap='The official CSV contains only one Default / No Team / Miscellaneous / card 1 placeholder row; a published subject roster and verified card identities are not available. The literal row is retained as source evidence, not imported as a verified card.'
  else:gap='The official CSV is header-only; no card rows or subjects are published in this export.'
  note='Source-only checklist: '+gap+' The manufacturer lists this program under '+selection['sport']+' with source year '+selection['year']+'. Product year and first checklist observation do not establish a calendar release date. Parallel numbering, print runs and pack odds remain unavailable; full product-guide and release reconciliation remain pending.'
  record={'title':title,'slug':slug,'page':'sets/'+slug+'.html','manufacturer':'Panini','sport':selection['sport'].lower(),'year':selection['year'],'sourcePage':SOURCE,'checklistUrl':SOURCE,'releaseStatus':'Unverified','releaseDate':None,'verified':proof['observed'],'checklistFirstObserved':proof['observed'],'status':'Official source','importKind':'panini-source-only','dedicatedParser':'scripts/import_panini_pending.py','coverageComplete':False,'rosterPublished':False,'parallelData':False,'publishedOdds':False,'sourceExport':observed['sourceExport'],'sha256':observed['sha256'],'sourceSelection':selection,'sourceObservation':reference,'sourceExportState':state,'importIssue':gap,'catalogEvidence':note,'dataAudit':note}
  record['description']='Source-only: the official export '+('contains a Default placeholder, so card identities and subject rosters remain unverified.' if state=='placeholder-only' else 'contains only column headers; a verified card roster remains pending.')
  for collection in [catalog['sets'],inventory]:
   match=next((i for i,r in enumerate(collection) if r['slug']==slug),None)
   if match is None:collection.append(record)
   else:collection[match]=record
  print(title+': source-only, '+state)
 catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n');inventory_path.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':
 for name in sys.argv[1:]:import_pending(Path(name).resolve())
