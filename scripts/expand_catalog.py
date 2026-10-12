"""Build source-backed pages without guessing release dates or card/odds data."""
import json,re,html,subprocess,concurrent.futures,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1]
slug=lambda t:re.sub('[^a-z0-9]+','-',t.lower()).strip('-')
previous={r['slug']:r for r in json.loads((root/'data/set-catalog.json').read_text())['sets']} if (root/'data/set-catalog.json').exists() else {}
records=[]
for r in json.loads((root/'data/topps-official-catalog.json').read_text()):
 title=r['title'];sport=next((s for term,s in [('Tennis','tennis'),('Baseball','baseball'),('Basketball','basketball'),('Football','football'),('UFC','ufc'),('WWE','wrestling'),('Formula','racing'),('Olympic','olympics'),('Soccer','soccer'),('UEFA','soccer'),('Premier League','soccer'),('Manchester','soccer')] if term in title),'multi-sport')
 records.append({'title':title,'manufacturer':'Topps / Bowman','sport':sport,'year':re.search(r'20\d\d(?:[-/]\d{2,4})?',title).group(0),'sourcePage':'https://www.topps.com/pages/checklists','checklistUrl':r['url'],'releaseStatus':'Unverified','releaseDate':None,'catalogEvidence':'Listed in Topps’ 2026 checklist catalog; this is not a verified release date.'})
if (root/'data/topps-product-official-catalog.json').exists():records+=json.loads((root/'data/topps-product-official-catalog.json').read_text())
records+=json.loads((root/'data/upperdeck-official-catalog.json').read_text())
if (root/'data/panini-official-catalog.json').exists():records+=json.loads((root/'data/panini-official-catalog.json').read_text())
if (root/'data/leaf-official-catalog.json').exists():records+=json.loads((root/'data/leaf-official-catalog.json').read_text())
for r in json.loads((root/'data/wildcard-official-catalog.json').read_text()):
 records.append({'title':r['t'],'manufacturer':'Wild Card','sport':r['s'].lower(),'year':r['y'],'sourcePage':'https://wildcardinc.com/checklists/','checklistUrl':'https://wildcardinc.com/checklists/'+r['f'],'releaseStatus':'Unverified','releaseDate':None,'catalogEvidence':'Manufacturer catalog month: '+(r.get('mo') or 'not specified')+'. Exact release date has not been verified.'})
# Panini's dynamically selected catalog is not exposed in a complete static listing.
records.append({'title':'FIFA World Cup 2026 Adrenalyn XL','manufacturer':'Panini','sport':'soccer','year':'2026','sourcePage':'https://www.panini.fr/media/paniniFiles/005461-checklist.pdf','checklistUrl':'https://www.panini.fr/media/paniniFiles/005461-checklist.pdf','releaseStatus':'Unverified','releaseDate':None})
for r in records:
 r['slug']=slug(r['manufacturer']+' '+r['title']);r['page']='sets/'+r['slug']+'.html';r['status']='Official source';r['verified']='2026-10-11'
 if 'Allen & Ginter Baseball' in r['title']:r.update(page='allen-ginter-2026.html',status='Searchable',sections=39,odds=97,formats=3,releaseStatus='Released')
 if r['title']=='2026 Bowman Football':r.update(page='bowman-football-2026.html',status='Searchable',sections=47,odds=521,formats=6,releaseStatus='Released')
(root/'data/imports').mkdir(exist_ok=True)
def import_table(r):
 if r['slug'] in previous and previous[r['slug']].get('tableData'):
  old=previous[r['slug']]
  if old['checklistUrl']==r['checklistUrl']:return {**r,**old}
 if r['manufacturer'] not in ['Upper Deck','Wild Card']:return r
 try:
  result=subprocess.run(['curl','-sLf','--max-time','20',r['checklistUrl']],capture_output=True,check=True);source=result.stdout.decode()
  tables=re.findall(r'<table\b[^>]*>(.*?)</table>',source,re.S|re.I)
  def clean(s):return html.unescape(re.sub('<[^>]+>',' ',s)).strip()
  for table in tables:
   rows=re.findall(r'<tr\b[^>]*>(.*?)</tr>',table,re.S|re.I);parsed=[];headers=[]
   for row in rows:
    vals=[' '.join(clean(v).split()) for v in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>',row,re.S|re.I)]
    if not vals:continue
    if '<th' in row.lower() and not headers:headers=vals
    else:parsed.append(vals)
   if headers and len(headers)>=3 and len(parsed)>5 and any(re.search(r'card|player|description|decription|name|number',h,re.I) for h in headers):
    # Keep every original column; do not infer universal parallels or numeric odds.
    assert all(len(row)==len(headers) for row in parsed)
    payload={'title':r['title'],'headers':headers,'rows':parsed,'source':r['checklistUrl'],'sha256':hashlib.sha256(result.stdout).hexdigest()}
    (root/'data/imports'/f"{r['slug']}.json").write_text(json.dumps(payload,ensure_ascii=False)+'\n');r.update(status='Source table',rowCount=len(parsed),tableData='data/imports/'+r['slug']+'.json');break
 except Exception as e:r['importIssue']=str(e)
 return r
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:records=list(pool.map(import_table,records))
(root/'data/set-catalog.json').write_text(json.dumps({'verified':'2026-10-11','sets':records,'coverage':{'complete':False,'notes':'Coverage is still being audited across manufacturers. Checklist publication does not establish a release date. Panini and Leaf require additional discovery; no claim of exhaustive 2026 releases is made.'}},ensure_ascii=False,indent=2)+'\n')
print(len(records),'official-source sets;',sum(r['status']=='Source table' for r in records),'structured source tables;',sum(r['status']=='Searchable' for r in records),'full interactive imports')
