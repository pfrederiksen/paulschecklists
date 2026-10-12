"""Import official PDFs and embedded manufacturer JSON without inventing missing fields."""
import json,re,subprocess,hashlib,concurrent.futures,unicodedata,html
from pathlib import Path
import pdfplumber
ROOT=Path(__file__).resolve().parents[1];CACHE=ROOT/'data/catalog-sources/downloads';CACHE.mkdir(parents=True,exist_ok=True)
def norm(s):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',s).lower().replace('®',''))
ODDS={norm(r['title']):r for r in json.loads((ROOT/'data/topps-official-odds.json').read_text())}
def fetch(url,path):
 marker=path.with_suffix(path.suffix+'.url')
 if not path.exists() or not marker.exists() or marker.read_text()!=url:
  temporary=path.with_suffix(path.suffix+'.part')
  subprocess.run(['curl','-sLf','--retry','2','--max-time','60',url,'-o',str(temporary)],check=True,capture_output=True)
  temporary.replace(path);marker.write_text(url)
 return path.read_bytes()
def clean(s):return ' '.join(s.replace('\x02','-').split())
def odds_pdf(path):
 result=[];formats=[];raw=[];issues=[];previous_labels=[];previous_bounds=[];previous_width=None
 with pdfplumber.open(path) as pdf:
  for pn,page in enumerate(pdf.pages,1):
   raw.append({'page':pn,'text':page.extract_text() or ''});words=page.extract_words(x_tolerance=0.1 if any(term in path.name for term in ['flagship-football','series-1-baseball','series-2-baseball']) else 3)
   ratio=lambda w:bool(re.fullmatch(r'[\d,]+(?::[\d,]+)+|-',w['text']))
   values=sorted([w for w in words if re.fullmatch(r'[\d,]+(?::[\d,]+)+',w['text'])],key=lambda w:w['top'])
   groups=[]
   for w in values:
    if not groups or abs(w['top']-groups[-1][0]['top'])>3:groups.append([w])
    else:groups[-1].append(w)
   if not groups:continue
   for group in groups:
    y=group[0]['top'];group.extend(w for w in words if w['text']=='-' and abs(w['top']-y)<=3)
    group.sort(key=lambda w:w['x0'])
   dense=max(groups,key=len);centers=[(w['x0']+w['x1'])/2 for w in dense]
   if len(centers)==1:
    clusters=[]
    for x in sorted(w['x1'] for w in values):
     if not clusters or x-clusters[-1][-1]>25:clusters.append([x])
     else:clusters[-1].append(x)
    if len(clusters)>1:centers=[sum(xs)/len(xs)-8 for xs in clusters]
   boundary=min(w['x0'] for group in groups for w in group)-2
   bounds=[boundary]+[(a+b)/2 for a,b in zip(centers,centers[1:])]+[page.width]
   markers=[w for w in words if w['text'].rstrip(':').lower() in ['card','subset'] and w['top']<groups[0][0]['top']]
   header_top=markers[-1]['top'] if markers else 0
   first_top=min(w['top'] for w in groups[0]);labels=[]
   marker_words=[w for w in words if abs(w['top']-header_top)<3]
   simple_headers=[w for w in marker_words if w['text'].rstrip(':').lower() in ['hobby','jumbo','breaker','value','mega','bulk','blaster','retail','fdi','mania']]
   if len(simple_headers)>=len(centers) and len(simple_headers)>=2 and not any(w['text'].rstrip(':').lower()=='odds' for w in marker_words):
    centers=[(w['x0']+w['x1'])/2 for w in simple_headers]
    bounds=[boundary]+[(a+b)/2 for a,b in zip(centers,centers[1:])]+[page.width]
   # Many Topps sheets right-align both headings and values, rather than center them.
   # Physical right edges preserve those headings without mixing adjacent formats.
   column_values=[[w for group in groups for w in group if bounds[i]<=(w['x0']+w['x1'])/2<bounds[i+1]] for i in range(len(centers))]
   right_edges=[max((w['x1'] for w in col),default=centers[i]+10) for i,col in enumerate(column_values)]
   right_aligned=all(not col or max(w['x1'] for w in col)-min(w['x1'] for w in col)<3 for col in column_values)
   header_chars=sorted([ch for ch in page.chars if abs(ch['top']-header_top)<3],key=lambda ch:ch['x0'])
   header_line=''.join(ch['text'] for ch in header_chars)
   codes=list(re.finditer(r'\d{4}(?=\s*-)',header_line))
   if codes:
    first_code_x=header_chars[codes[0].start()]['x0'];clusters=[]
    for v in sorted([v for group in groups for v in group if v['x1']>=first_code_x-5],key=lambda w:w['x1']):
     if not clusters or v['x1']-clusters[-1][-1]['x1']>8:clusters.append([v])
     else:clusters[-1].append(v)
    if len(codes)<=len(clusters)<=len(codes)+2:
     clusters=clusters[:len(codes)];right_edges=[max(v['x1'] for v in cluster) for cluster in clusters];centers=right_edges
     bounds=[0]+[edge+0.5 for edge in right_edges[:-1]]+[page.width]
   heading_count=len(codes) or sum(w['text'].rstrip(':').lower()=='odds' for w in marker_words)
   if previous_bounds and heading_count==len(previous_labels) and heading_count>len(centers) and page.width==previous_width:
    bounds=previous_bounds;centers=[(a+b)/2 for a,b in zip(bounds,bounds[1:])]
   elif len(codes)==len(centers) or right_aligned:
    bounds=[0]+[edge+0.5 for edge in right_edges[:-1]]+[page.width]
   def header_text(left,right):
    chars=[ch for ch in page.chars if header_top-1<=ch['top']<first_top-1 and left<=(ch['x0']+ch['x1'])/2<right]
    lines=[]
    for ch in sorted(chars,key=lambda ch:(round(ch['top']/3),ch['x0'])):
     if not lines or abs(ch['top']-lines[-1][0])>3:lines.append((ch['top'],[]))
     lines[-1][1].append(ch)
    return clean(' '.join(''.join(ch['text'] for ch in sorted(line,key=lambda ch:ch['x0'])) for _,line in lines))
   for i in range(len(centers)):
    label=header_text(bounds[i],bounds[i+1])
    if i==0:label=re.sub(r'^(?:Card|Subset:?)\s*','',label)
    if previous_labels and len(previous_labels)==len(centers):label=previous_labels[i]
    if not label:label=f'Official column {i+1}'
    labels.append(label)
    if label not in formats:formats.append(label)
   previous_labels=labels;previous_bounds=bounds;previous_width=page.width
   rects=[]
   for t in page.find_tables():
    for row in t.rows:
     if row.bbox[3]>row.bbox[1]:rects.append((row.bbox[1],row.bbox[3]))
   for index,group in enumerate(groups):
    y=min(w['top'] for w in group);bottom=max(w['bottom'] for w in group)
    containing=[rect for rect in rects if rect[0]<=y and rect[1]>=bottom and rect[1]-rect[0]<80]
    if containing:top,end=min(containing,key=lambda r:r[1]-r[0])
    else:
     top=(max(w['bottom'] for w in groups[index-1])+y)/2 if index else first_top-2
     end=(bottom+min(w['top'] for w in groups[index+1]))/2 if index+1<len(groups) else min(page.height,bottom+10)
    name=clean(page.crop((0,top,boundary,end)).extract_text() or '')
    vals={f:None for f in labels};seen=set()
    for v in group:
     x=(v['x0']+v['x1'])/2;i=next((i for i in range(len(centers)) if bounds[i]<=x<bounds[i+1]),None)
     if i is None:issues.append({'page':pn,'row':name,'reason':'Unmapped physical odds column'});continue
     if i in seen:
      if v['text']=='-':continue
      if vals[labels[i]] is not None:issues.append({'page':pn,'row':name,'reason':'Ambiguous physical odds column'});continue
     seen.add(i);vals[labels[i]]=v['text'] if v['text']!='-' else None
    if not name:issues.append({'page':pn,'row':'','reason':'Empty row label'});continue
    result.append({'name':name,'values':vals,'page':pn})
 return result,formats,raw,issues

def run(r):
 if r['page'] in ['allen-ginter-2026.html','bowman-football-2026.html']:return r
 # Dedicated physical-column parsing preserves the National PDF's numbering tables.
 if r.get('importKind') in ['panini-pdf','topps-grid-pdf']:return r
 try:
  if r['manufacturer']=='Topps / Bowman' or r['manufacturer']=='Panini':
   path=CACHE/(r['slug']+'.pdf');blob=fetch(r['checklistUrl'],path);rows=[];raw=[];headings=[];section='Checklist';notes=[]
   with pdfplumber.open(path) as pdf:
    for pn,page in enumerate(pdf.pages,1):
     txt=page.extract_text() or '';raw.append({'page':pn,'text':txt})
     for line in txt.splitlines():
      line=clean(line)
      if line.startswith(('Checklists provided','product at','that product','contents and','**Checklists','Checklists and')):continue
      match=re.match(r'^(\d{1,5}|[A-Z]{1,6}\d+[A-Z]?|[A-Za-z0-9]+[-–][A-Za-z0-9-]+)\s+(.+)$',line)
      if match and not re.match(r'^20\d\d\s+(?:Topps|Bowman|Panini|FIFA)',line):
       number,desc=match.groups();rows.append([section,number,desc,str(pn)])
      elif line and line.upper()==line and re.search('[A-Z]',line) and len(line)<180 and not re.fullmatch(r'[A-Z][a-z]*',line):
       section=line
       if section not in headings:headings.append(section)
      elif line:notes.append({'page':pn,'text':line})
   if len(rows)<5:raise ValueError('PDF layout needs dedicated parser; insufficient recognized card rows')
   payload={'title':r['title'],'headers':['Checklist section','Card number','Official description (player / team / notes)','Source page'],'rows':rows,'source':r['checklistUrl'],'sha256':hashlib.sha256(blob).hexdigest(),'rawPages':raw,'unclassifiedLines':notes,'importKind':'pdf','sectionColumn':0}
   odd=ODDS.get(norm(r['title']))
   if odd:
    op=CACHE/(r['slug']+'-odds.pdf');ob=fetch(odd['url'],op);entries,formats,oraw,issues=odds_pdf(op)
    payload.update(odds=entries,formats=formats,oddsSource=odd['url'],oddsRawPages=oraw,oddsIssues=issues,oddsSha256=hashlib.sha256(ob).hexdigest())
    r.update(odds=len(entries),formats=len(formats),oddsUrl=odd['url'],oddsImportIssues=len(issues))
   r.update(status='Source table',rowCount=len(rows),tableData='data/imports/'+r['slug']+'.json',sections=len(set(row[0] for row in rows)),importKind='pdf')
  elif r['manufacturer']=='Wild Card':
   path=CACHE/(r['slug']+'.html');blob=fetch(r['checklistUrl'],path);text=blob.decode();
   if 'Page not found. This page is no longer available.' in text:r['sourceUnavailable']=True;raise ValueError('Official catalog link returns a missing page')
   m=re.search(r'const\s+C\s*=\s*',text)
   if not m:raise ValueError('Embedded checklist schema unavailable')
   data,_=json.JSONDecoder().raw_decode(text[m.end():]);data.pop('images',None)
   rows=[]
   for key,items in data.items():
    if key in ['subsets','sets','groups'] or not isinstance(items,list):continue
    for item in items:
     if isinstance(item,str):rows.append([key,item,''])
     elif isinstance(item,dict):rows.append([key,item.get('name',item.get('player','')),json.dumps({k:v for k,v in item.items() if k not in ['name','player']},ensure_ascii=False)])
   for subset in data.get('subsets',[]):
    for key in ['roster_names','roster_names_base']:
     for item in subset.get(key,[]):
      name=item if isinstance(item,str) else item.get('name',json.dumps(item,ensure_ascii=False))
      rows.append([subset.get('name','Subset')+' · '+key.replace('_',' '),name,''])
   if rows:r.pop('rosterPublished',None)
   if not rows and data.get('subsets'):
    for subset in data['subsets']:rows.append([subset.get('name','Official subset'),'Roster not published',subset.get('note','')])
    r['rosterPublished']=False
   if not rows:raise ValueError('No recognized subject roster')
   payload={'title':r['title'],'headers':['Official roster','Player / subjects','Source notes'],'rows':rows,'source':r['checklistUrl'],'sha256':hashlib.sha256(blob).hexdigest(),'officialStructure':data,'importKind':'wildcard','sectionColumn':0}
   r.update(status='Source table',rowCount=len(rows),tableData='data/imports/'+r['slug']+'.json',importKind='wildcard',parallelData=bool(data.get('subsets')),sections=len(data.get('subsets',[])))
  elif r['manufacturer']=='Upper Deck':
   if not r.get('tableData'):
    path=CACHE/(r['slug']+'.html');blob=fetch(r['checklistUrl'],path);text=blob.decode();t=re.search(r'<table\b.*?</table>',text,re.S|re.I)
    if not t:raise ValueError('No published checklist table')
    parsed=[]
    for row in re.findall(r'<tr\b.*?</tr>',t.group(),re.S|re.I):
     values=[clean(html.unescape(re.sub('<[^>]+>',' ',cell))) for cell in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>',row,re.S|re.I)]
     if any(values):parsed.append(values)
    headers=parsed.pop(0);assert all(len(row)==len(headers) for row in parsed)
    r.update(tableData='data/imports/'+r['slug']+'.json',status='Source table',rowCount=len(parsed))
    (ROOT/r['tableData']).write_text(json.dumps({'title':r['title'],'headers':headers,'rows':parsed,'source':r['checklistUrl'],'sha256':hashlib.sha256(blob).hexdigest()},ensure_ascii=False))
   payload=json.loads((ROOT/r['tableData']).read_text());payload.update(importKind='html',sectionColumn=0)
   oi=next((i for i,h in enumerate(payload['headers']) if 'odds' in h.lower()),None)
   si=next((i for i,h in enumerate(payload['headers']) if "#'d" in h or 'serial' in h.lower()),None)
   payload['oddsColumn']=oi;payload['serialColumn']=si
   r.update(importKind='html',parallelData=True,publishedOdds=oi is not None and any(row[oi] for row in payload['rows']),sections=len(set(row[0] for row in payload['rows'])))
  else:return r
  (ROOT/r['tableData']).write_text(json.dumps(payload,ensure_ascii=False)+'\n');r.pop('importIssue',None)
  r['dataAudit']='Official fields imported; missing manufacturer odds or serial numbering are not estimated.'
 except Exception as e:r['importIssue']=str(e)[:220]
 print(r['title'],r.get('rowCount',0),r.get('odds',0),r.get('importIssue',''),flush=True);return r
if __name__=='__main__':
 catalog=json.loads((ROOT/'data/set-catalog.json').read_text())
 with concurrent.futures.ProcessPoolExecutor(max_workers=6) as pool:catalog['sets']=list(pool.map(run,catalog['sets']))
 (ROOT/'data/set-catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 print('Imported',sum(bool(r.get('tableData')) for r in catalog['sets']),'source datasets')
