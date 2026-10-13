"""Preserve every populated physical row in official celebrity workbooks.
Unlabelled additions columns remain unlabelled: never infer card numbers or names.
"""
import json,hashlib,io,urllib.request
from pathlib import Path
import openpyxl
ROOT=Path(__file__).resolve().parents[1]
def run(r):
 blob=urllib.request.urlopen(r['checklistUrl'],timeout=45).read();w=openpyxl.load_workbook(io.BytesIO(blob),data_only=True)
 headers=['Checklist section','Card number','Player / subjects','Source worksheet','Source row'];entries=[];originals=[];sheets=[];specs=[]
 cell=lambda v:'' if v is None else str(v)
 for sheet in w:
  rows=list(sheet.values);head=rows[0];annotations=[];start=1
  while start<len(rows) and not any(rows[start][:4]) and any(v is not None for v in rows[start]):annotations.append(rows[start]);start+=1
  columns=[]
  for i,h in enumerate(head):
   label=str(h) if h is not None else f'Unlabelled source column {i+1}'
   extra=[str(a[i]) for a in annotations if a[i] is not None]
   if extra:label+=' · '+' / '.join(extra)
   if head.count(h)>1:label+=f' [column {i+1}]'
   columns.append(label)
   if label not in originals:originals.append(label)
  assert len(set(columns))==len(columns)
  saved=[]
  for rn,row in enumerate(rows[start:],start+1):
   if not any(v is not None for v in row):continue
   fields=dict(zip(columns,map(cell,row)))
   name=fields.get('Name',fields.get('Item',''))
   section=fields.get('Subset') or sheet.title
   # Missing headings are preserved as source descriptions, not inferred subjects.
   if not name:name=' · '.join(f'{h}: {cell(v)}' for h,v in zip(columns,row) if v is not None)
   entries.append((section,fields.get('Checklist',''),name,sheet.title,str(rn),fields));saved.append(list(map(cell,row)))
  sheets.append({'name':sheet.title,'headers':columns,'rawHeaders':list(head),'headerAnnotations':[list(a) for a in annotations],'rowCount':len(saved),'unlabelledColumns':any(h is None for h in head)})
  # Preserve all numbering qualifiers, card identifiers and item statuses in the shared specifications view.
  for family in dict.fromkeys(e[0] for e in entries if e[3]==sheet.title):
   familyrows=[e[5] for e in entries if e[3]==sheet.title and e[0]==family]
   specs.append({'name':family,'worksheet':sheet.title,'headers':columns,'rows':[[f[h] for h in columns] for f in familyrows]})
 rows=[[a,b,c,d,e,*[f.get(h,'') for h in originals]] for a,b,c,d,e,f in entries];headers+=originals
 assert len(rows)==sum(s['rowCount'] for s in sheets)
 payload={'title':r['title'],'headers':headers,'rows':rows,'source':r['checklistUrl'],'sha256':hashlib.sha256(blob).hexdigest(),'importKind':'xlsx','sectionColumn':0,'publishedSpecifications':specs,'sourceSheets':sheets}
 path='data/imports/'+r['slug']+'.json';(ROOT/path).write_text(json.dumps(payload,ensure_ascii=False)+'\n')
 r.update(tableData=path,status='Source table',rowCount=len(rows),sections=len(set(x[0] for x in rows)),importKind='xlsx',dedicatedParser='scripts/import_leaf_entertainment.py',parallelData=True,publishedOdds=False,sha256=payload['sha256'],dataAudit='All populated workbook rows, original physical columns and duplicate-header annotations reconciled. Quantity, numbering and redemption statuses are preserved literally. Unlabelled additions columns are searchable descriptions; card numbers and subject roles are not inferred.')
 r.pop('importIssue',None)
 r['catalogEvidence']+=' Includes original cut-signature or redemption-item rows where published. Any unlabelled source columns remain explicitly unlabelled; numbering is not pack odds.'
 print(r['title'],len(rows),'rows;',[(s['name'],s['rowCount']) for s in sheets]);return r
if __name__=='__main__':
 p=ROOT/'data/set-catalog.json';c=json.loads(p.read_text());inventory=json.loads((ROOT/'data/leaf-official-catalog.json').read_text())
 records=[run(dict(r)) for r in inventory if r['sport']=='celebrity'];by={r['slug']:r for r in records};c['sets']=[by.get(r['slug'],r) for r in c['sets']];p.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
