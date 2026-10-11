"""Parse and validate the five-column official 2026 National Silver Packs PDF."""
import json,re,hashlib,urllib.request
from pathlib import Path
import pdfplumber
ROOT=Path(__file__).resolve().parents[1]
URL='https://blog.paniniamerica.net/wp-content/uploads/2026/07/National-checklist26.pdf'
PAGE='https://blog.paniniamerica.net/shine-bright-panini-silver-packs-return-to-the-national-sports-collectors-convention/'
SLUG='panini-2026-panini-national-silver-packs'
if __name__=='__main__':
 blob=urllib.request.urlopen(URL,timeout=30).read();path=ROOT/'data/catalog-sources/downloads'/f'{SLUG}.pdf';path.write_bytes(blob)
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==1;page=pdf.pages[0];assert abs(page.width-720)<1
  rows=[];specifications={'Commons':[],'National Insert':[['Standard / original','# to 50','Not published']]};raw=[]
  for left,right in [(0,164),(164,295),(295,425),(425,560),(560,720)]:
   text=page.crop((left,0,right,page.height)).extract_text();raw.append(text)
   for line in text.splitlines():
    line=line.strip();match=re.match(r'^[\uf0a3□]\s*((?:NIL|RC|MKT)?\d+)\s+(.+)$',line)
    if match:
     number,subject=match.groups();family='National Insert' if number.startswith('MKT') else 'Commons';rows.append([family,number,subject,'1']);continue
    if line.startswith('Commons ') or line.startswith('National Insert '):
     family='Commons' if line.startswith('Commons ') else 'National Insert';label=re.sub(r'\s*\(# to.*','',line);n=re.search(r'\((# to[^)]+)\)',line);specifications[family].append([label,n[1] if n else 'Not published','Not published'])
  expected={str(i) for i in range(1,66)}|{f'NIL{i}' for i in range(1,26)}|{f'RC{i}' for i in range(1,11)}|{f'MKT{i}' for i in range(1,14)}
  assert len(rows)==113 and {r[1] for r in rows}==expected
  assert len(specifications['Commons'])==12 and len(specifications['National Insert'])==4
  def order(row):return (['Commons','National Insert'].index(row[0]),0 if row[1].isdigit() else 1 if row[1].startswith('NIL') else 2 if row[1].startswith('RC') else 3,int(re.search(r'\d+',row[1]).group()))
  rows.sort(key=order)
  payload={'title':'2026 Panini National Silver Packs','headers':['Checklist section','Card number','Player / subjects','Source page'],'rows':rows,'source':URL,'sha256':hashlib.sha256(blob).hexdigest(),'importKind':'panini-pdf','sectionColumn':0,'rawPages':[{'page':1,'text':'\n\n'.join(raw)}],'publishedSpecifications':[{'name':family,'worksheet':'Official PDF page 1','headers':['Parallel / variation','Published numbering','Pack odds'],'rows':values} for family,values in specifications.items()]}
  dest='data/imports/'+SLUG+'.json';(ROOT/dest).write_text(json.dumps(payload,ensure_ascii=False)+'\n')
  record={'title':payload['title'],'manufacturer':'Panini','sport':'multi-sport','year':'2026','sourcePage':PAGE,'checklistUrl':URL,'releaseStatus':'Unverified','releaseDate':None,'catalogEvidence':'Official Panini Silver Packs announcement published July 29, 2026. Exact release date has not been independently verified. Card numbers and names are preserved as printed, including apparent source spelling errors. Numbering is not pack odds.','slug':SLUG,'page':'sets/'+SLUG+'.html','verified':'2026-10-11','status':'Source table','tableData':dest,'rowCount':113,'sections':2,'parallelData':True,'publishedOdds':False,'importKind':'panini-pdf','sha256':payload['sha256'],'dataAudit':'All 113 printed numbered cards and 16 published numbering specifications imported from the official PDF.'}
  inventory=ROOT/'data/panini-official-catalog.json';records=json.loads(inventory.read_text()) if inventory.exists() else [];records=[r for r in records if r['slug']!=SLUG]+[record];inventory.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
  catalog=json.loads((ROOT/'data/set-catalog.json').read_text());catalog['sets']=[r for r in catalog['sets'] if r['slug']!=SLUG]+[record];(ROOT/'data/set-catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n');print('Imported 113 numbered cards and 16 published numbering rows.')
