"""Preserve the physical columns of Topps' 2026 Midnight Football PDF."""
import json,re,hashlib,subprocess
from pathlib import Path
import pdfplumber
import import_official_catalog as generic
ROOT=Path(__file__).resolve().parents[1]
SLUG='topps-bowman-2026-topps-midnight-football'
URL='https://cdn.shopify.com/s/files/1/0662/9749/5709/files/2026_Topps_Midnight_Football_checklist_ae614b15-64bd-4427-bebc-baa904c7368c.pdf?v=1791410806'
PAGE='https://www.topps.com/pages/topps-midnight-football'
def build():
 record={'title':'2026 Topps Midnight Football','manufacturer':'Topps / Bowman','sport':'football','year':'2026','slug':SLUG,'page':f'sets/{SLUG}.html','sourcePage':PAGE,'checklistUrl':URL,'releaseStatus':'Upcoming','releaseDate':'2026-11-13','verified':'2026-10-11'}
 # First use the catalog importer; reconcile every row against physical columns.
 path=ROOT/'data/catalog-sources/downloads'/f'{SLUG}.pdf'
 subprocess.run(['curl','-sLf','--retry','2','--max-time','30',URL,'-o',str(path)],check=True)
 path.with_suffix('.pdf.url').write_text(URL)
 record=generic.run(record);baseline=json.loads((ROOT/record['tableData']).read_text())
 rows=[];section='Checklist';raw=[]
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==10
  for pn,page in enumerate(pdf.pages,1):
   raw.append({'page':pn,'text':page.extract_text()})
   lines={}
   for w in page.extract_words():lines.setdefault(round(w['top'],1),[]).append(w)
   for y,ws in sorted(lines.items()):
    ws.sort(key=lambda w:w['x0']);text=' '.join(w['text'] for w in ws)
    if pn==1 and y<75:continue # Manufacturer disclaimer above checklist on page one.
    if re.fullmatch(r'\d+|[A-Z]+-[A-Z0-9]+',ws[0]['text']) and len(ws)>2:
     cols=[' '.join(w['text'] for w in ws if lo<=w['x0']<hi) for lo,hi in [(0,75),(75,224),(224,364),(364,page.width)]]
     assert cols[0] and cols[1] and cols[2] and cols[3] in ('','Rookie'),cols
     rows.append([section,*cols,str(pn)])
    elif text==text.upper() and re.search('[A-Z]',text):section=text
 assert len(rows)==636,len(rows)
 assert [(r[0],r[1],r[-1]) for r in rows]==[(r[0],r[1],r[-1]) for r in baseline['rows']]
 base=[r for r in rows if r[0]=='BASE CARDS'];assert [int(r[1]) for r in base]==list(range(1,101))
 assert sum(r[4]=='Rookie' for r in base)==37
 assert next(r for r in rows if r[0]=='CONSTELLATIONS' and r[1]=='C-2')[2:4]==['Warren Moon/Cam Ward','Houston Oilers/Tennessee Titans']
 payload={'title':record['title'],'headers':['Checklist section','Card number','Name','Team','Rookie','Source page'],'rows':rows,'source':URL,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'rawPages':raw,'importKind':'topps-grid-pdf','sectionColumn':0}
 (ROOT/record['tableData']).write_text(json.dumps(payload,ensure_ascii=False)+'\n')
 record.update(importKind='topps-grid-pdf',rowCount=len(rows),sections=len(set(r[0] for r in rows)),parallelData=False,publishedOdds=False,sha256=payload['sha256'],catalogEvidence='Official product page now announces November 13, 2026 availability; October 12 was the preorder date. All 636 PDF rows retain names, teams and rookie markers, including dual-subject names and teams. Parallel specifications and pack odds are not published in the checked official checklist, product pages or global odds catalog.',dataAudit='Every physical-column row reconciled with the catalog importer; base numbers 1–100 and 37 published base rookie flags verified.')
 for name in ['topps-product-official-catalog.json','set-catalog.json']:
  p=ROOT/'data'/name;c=json.loads(p.read_text());items=c['sets'] if isinstance(c,dict) else c
  items[:]=[r for r in items if r['slug']!=SLUG]+[record]
  p.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
 print('Imported',len(rows),'rows across',record['sections'],'sections with original names, teams and rookie fields.')
if __name__=='__main__':build()
