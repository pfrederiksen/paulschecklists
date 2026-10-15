"""Import every published sheet of officially linked Leaf Google CSV checklists.
Keep original headers, source rows, notes and card-specific color limits. No odds
or subject roles are inferred from box contents or unnamed cells.
"""
import csv,hashlib,io,json,re,subprocess,concurrent.futures
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ARCHIVE=ROOT/'data/official-leaf';ARCHIVE.mkdir(exist_ok=True)
PARSER='scripts/import_leaf_csv.py'
def read(url):
 return subprocess.run(['curl','-sLf','--retry','2','--max-time','50',url],capture_output=True,check=True).stdout

def run(record):
 r=dict(record);slug=r['slug'];url=r['checklistUrl'];base=url.split('/pub?')[0];publication=base+'/pubhtml'
 try:
  page=read(publication);(ARCHIVE/(slug+'-publication.html')).write_bytes(page)
  tabs=re.findall(r'items\.push\(\{name:\s*("(?:[^"\\]|\\.)*"),.*?gid:\s*"(-?\d+)"',page.decode(),re.S)
  if not tabs:raise ValueError('Cannot reconcile the published worksheet index')
  collected=[];original_headers=[];sheets=[];annotations=[]
  for name,gid in tabs:
   name=json.loads(name);sheeturl=url+'&gid='+gid;blob=read(sheeturl);archive=ARCHIVE/f'{slug}-{gid}.csv';archive.write_bytes(blob)
   parsed=list(csv.reader(io.StringIO(blob.decode('utf-8-sig'),newline='')))
   if not parsed:raise ValueError('Empty published CSV sheet')
   rawheaders=parsed.pop(0);headers=[]
   for i,h in enumerate(rawheaders):
    label=h if h else f'Unlabelled source column {i+1}'
    if rawheaders.count(h)>1:label+=f' [column {i+1}]'
    headers.append(label)
    if label not in original_headers:original_headers.append(label)
   if any(len(row)!=len(headers) for row in parsed):raise ValueError('Original CSV column width mismatch')
   populated=[(rn,row) for rn,row in enumerate(parsed,2) if any(row)]
   field=lambda row,names:next((row[i] for i,h in enumerate(rawheaders) if h.strip().lower() in names),'')
   for rn,row in populated:
    section=field(row,{'subset','card set','section'}) or name
    number=field(row,{'checklist','card number','card #','card no.'})
    subject=field(row,{'name','name_oscar','names','player','athlete','subject'})
    if not subject:subject=' · '.join(f'{h}: {v}' for h,v in zip(headers,row) if v)
    collected.append((section,number,subject,name,str(rn),dict(zip(headers,row))))
    if not number and not field(row,{'name','name_oscar','names','player','athlete','subject'}):annotations.append({'worksheet':name,'sourceRow':rn,'cells':row})
   sheets.append({'name':name,'gid':gid,'source':sheeturl,'headers':headers,'rawHeaders':rawheaders,'rowCount':len(populated),'sourceExport':str(archive.relative_to(ROOT)),'sha256':hashlib.sha256(blob).hexdigest()})
  rows=[[a,b,c,d,e,*[f.get(h,'') for h in original_headers]] for a,b,c,d,e,f in collected]
  if len(rows)<5:raise ValueError('Insufficient published checklist rows')
  specs=[]
  for family in dict.fromkeys(e[0] for e in collected):
   specs.append({'name':family,'headers':original_headers,'rows':[[e[5].get(h,'') for h in original_headers] for e in collected if e[0]==family]})
  fingerprint=hashlib.sha256(json.dumps([{'gid':sheet['gid'],'sha256':sheet['sha256']} for sheet in sheets],sort_keys=True).encode()).hexdigest()
  payload={'checklistFingerprint':fingerprint,'title':r['title'],'source':url,'sha256':sheets[0]['sha256'],'publicationSource':publication,'publicationSha256':hashlib.sha256(page).hexdigest(),'sourceSheets':sheets,'headers':['Checklist section','Card number','Player / subjects','Source worksheet','Source row',*original_headers],'rows':rows,'sectionColumn':0,'publishedSpecifications':specs,'sourceAnnotations':annotations,'importKind':'leaf-csv','dedicatedParser':PARSER,'coverageComplete':True}
  path=f'data/imports/{slug}.json';(ROOT/path).write_text(json.dumps(payload,ensure_ascii=False)+'\n')
  audit=f'All {len(rows):,} populated rows across {len(sheets)} officially published CSV worksheet(s) are retained, with original columns, card identifiers, notes and card-specific foil/color values. Published sheet coverage is reconciled; no pack odds, team roles or release dates are inferred.'
  r.update(status='Source table',tableData=path,rowCount=len(rows),sections=len(set(row[0] for row in rows)),parallelData=True,publishedOdds=False,importKind='leaf-csv',dedicatedParser=PARSER,sha256=payload['sha256'],coverageComplete=True,verified=date.today().isoformat(),dataAudit=audit)
  r['catalogEvidence']+=' '+audit
  if len({entry[5].get('Set','') for entry in collected if entry[5].get('Set','') and not entry[5].get('Set','').startswith('*')})>1:r['catalogEvidence']+=' The published worksheet also labels some rows with other Set values; those identities and redemption/status fields remain literal in original card details.';r.pop('importIssue',None)
  print(r['title'],len(rows),'rows',len(sheets),'sheets',original_headers,flush=True)
 except Exception as exc:
  r.update(status='Official source',importIssue=f'Official CSV import pending: {exc}',coverageComplete=False)
  print(r['title'],'pending',str(exc),flush=True)
 return r
if __name__=='__main__':
 p=ROOT/'data/set-catalog.json';catalog=json.loads(p.read_text());known={r['slug']:r for r in catalog['sets']};inventory=json.loads((ROOT/'data/leaf-official-catalog.json').read_text())
 sources=[r for r in inventory if ('output=csv' in r['checklistUrl'] or 'format=csv' in r['checklistUrl']) and (r['slug'] not in known or known[r['slug']].get('dedicatedParser')==PARSER)]
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(run,sources))
 by={r['slug']:r for r in results};catalog['sets']=[by.pop(r['slug'],r) for r in catalog['sets']]+list(by.values());p.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 print('Official Leaf CSV sources reconciled:',len(results),flush=True)
