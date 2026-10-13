"""Import official Leaf workbooks, preserving sheets, headers, rows and numbering."""
import json,re,hashlib,urllib.request,io
from pathlib import Path
import openpyxl
ROOT=Path(__file__).resolve().parents[1]
def import_workbook(record,blob):
 workbook=openpyxl.load_workbook(io.BytesIO(blob),data_only=True)
 headers=['Checklist section','Card number','Player / subjects','Source worksheet','Source row']; originals=[]; records=[];specs=[];sheet_sources=[]
 for sheet in workbook:
  values=list(sheet.values); header_index=next(i for i,row in enumerate(values) if all(h in row for h in ['Subset','Name','Checklist']));raw_headers=values[header_index]
  sheet_sources.append({'name':sheet.title,'headers':[h for h in raw_headers if h is not None],'notes':[[v for v in row if v is not None] for row in values[:header_index]],'rowCount':sum(1 for row in values[header_index+1:] if any(v is not None for v in row))})
  annotation_rows=[];data_start=header_index+1
  while data_start<len(values) and not any(values[data_start][:4]) and any(v is not None for v in values[data_start]):
   annotation_rows.append(list(values[data_start]));data_start+=1
  sheet_sources[-1]['headerAnnotations']=annotation_rows;sheet_sources[-1]['rowCount']=sum(1 for row in values[data_start:] if any(v is not None for v in row))
  columns=[]
  for i,h in enumerate(raw_headers):
   if h is None:continue
   label=str(h);annotations=[str(row[i]) for row in annotation_rows if row[i] is not None]
   if annotations:label+=' · '+' / '.join(annotations)
   if list(raw_headers).count(h)>1:label+=f' [column {i+1}]'
   columns.append((i,label))
  names=[h for _,h in columns];assert len(names)==len(set(names)),sheet.title
  for _,h in columns:
   if h not in originals:originals.append(h)
  for row_number,row in enumerate(values[data_start:],data_start+1):
   if not any(v is not None for v in row):continue
   fields={h:row[i] for i,h in columns}
   if not fields.get('Subset') or not fields.get('Name') or not fields.get('Checklist'):raise ValueError(f'Unclassified nonblank row {sheet.title}:{row_number}')
   assert all(row[i] is None for i,h in enumerate(raw_headers) if h is None),'Unlabelled source value'
   records.append((sheet.title,row_number,fields))
  colors=[h for h in names if h not in ['Set','Subset','Name','Checklist','Foil','MEM','BASE','City Designation','Redemption Status','Note']]
  for subset in dict.fromkeys(f['Subset'] for sn,rn,f in records if sn==sheet.title):
   unique={}
   for sn,rn,f in records:
    if sn==sheet.title and f['Subset']==subset:
     vals=[f.get('Foil',''),*[f.get(c) for c in colors],f.get('MEM',''),f.get('BASE','')];unique[json.dumps(vals)]=vals
   specs.append({'name':subset,'worksheet':sheet.title,'headers':['Foil',*colors,'MEM','BASE'],'rows':list(unique.values())})
 headers+=originals
 def cell(v):return '' if v is None else str(v)
 rows=[[cell(f['Subset']),cell(f['Checklist']),cell(f['Name']),sn,str(rn),*[cell(f.get(h)) for h in originals]] for sn,rn,f in records]
 payload={'title':record['title'],'headers':headers,'rows':rows,'source':record['checklistUrl'],'sha256':hashlib.sha256(blob).hexdigest(),'importKind':'xlsx','sectionColumn':0,'publishedSpecifications':specs,'sourceSheets':sheet_sources}
 for row,(sn,rn,fields) in zip(rows,records):
  assert row[5:]==[cell(fields.get(h)) for h in originals]
 path='data/imports/'+record['slug']+'.json';(ROOT/path).write_text(json.dumps(payload,ensure_ascii=False)+'\n')
 record.update(tableData=path,status='Source table',importKind='xlsx',parallelData=True,publishedOdds=False,rowCount=len(rows),sections=len(set(r[0] for r in rows)),sha256=payload['sha256'],dataAudit='All nonblank workbook rows and labelled fields preserved; numbering is not pack odds.')
 return record
if __name__=='__main__':
 catalog=json.loads((ROOT/'data/set-catalog.json').read_text());records=json.loads((ROOT/'data/leaf-official-catalog.json').read_text())
 for record in records:
  old=next((s for s in catalog['sets'] if s['slug']==record['slug']),None)
  if old and old.get('dedicatedParser')=='scripts/import_leaf_entertainment.py' and old['checklistUrl']==record['checklistUrl']:
   print(record['title'],'preserved dedicated entertainment import',flush=True);continue
  result=dict(record)
  try:
   if not record['checklistUrl'].split('?')[0].endswith('.xlsx'):raise ValueError('Official document format needs a dedicated parser')
   blob=urllib.request.urlopen(record['checklistUrl'],timeout=45).read();cache=ROOT/'data/catalog-sources/downloads';cache.mkdir(parents=True,exist_ok=True);(cache/(record['slug']+'.xlsx')).write_bytes(blob)
   result=import_workbook(record,blob)
  except Exception as e:
   result={**(old or {}),**record,'importIssue':str(e)[:220]}
   if old and old.get('tableData'):result['status']=old['status']
  catalog['sets']=[s for s in catalog['sets'] if s['slug']!=result['slug']]+[result];print(result['title'],result.get('rowCount',0),'rows',result.get('importIssue',''),flush=True)
 (ROOT/'data/set-catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
