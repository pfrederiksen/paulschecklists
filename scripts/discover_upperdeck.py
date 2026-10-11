import json,re,html,urllib.request,concurrent.futures
from pathlib import Path
root=Path(__file__).resolve().parents[1]
posts=json.loads((root/'data/catalog-sources/ud-2026.json').read_text())
records=[]
for p in posts:
 categories=[s.removeprefix('checklist-category-') for s in p['class_list'] if s.startswith('checklist-category-')]
 if not categories or categories==['entertainment']:continue
 sport=next((x for x in categories if x!='entertainment'),None)
 if sport:records.append({'title':html.unescape(p['title']['rendered']).removesuffix(' Checklist'),'manufacturer':'Upper Deck','sport':sport,'sourcePage':p['link'],'checklistPublished':p['date'][:10],'releaseStatus':'Unverified','releaseDate':None,'year':re.search(r'20\d\d(?:[-/]\d{2,4})?',p['title']['rendered']).group(0) if re.search(r'20\d\d',p['title']['rendered']) else 'Unspecified'})
def fetch(r):
 try:
  with urllib.request.urlopen(r['sourcePage'],timeout=20) as response:s=response.read().decode()
  urls=re.findall(r'href=["\']([^"\']+\.(?:pdf|xlsx?|csv)(?:\?[^"\']*)?)["\']',s,re.I)
  urls=[html.unescape(u) for u in urls if not any(x in u.lower() for x in ['privacy','dealer','form','application'])]
  r['checklistUrl']=urls[0] if urls else r['sourcePage'];r['documentUrls']=list(dict.fromkeys(urls))
 except Exception as e:r['checklistUrl']=r['sourcePage'];r['fetchError']=str(e)
 return r
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:records=list(pool.map(fetch,records))
(root/'data/upperdeck-official-catalog.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
print('Upper Deck:',len(records),'sports checklist pages;',sum(bool(r.get('documentUrls')) for r in records),'with direct document URLs')
