"""Import the official ruled six-column F1 PDF, including blank Name cells."""
import json,re,hashlib,subprocess
from pathlib import Path
import pdfplumber
from import_topps_tribute_2026 import acquire
from import_topps_f1_odds_2026 import enrich
ROOT=Path(__file__).resolve().parents[1];SLUG='topps-bowman-2026-topps-chrome-formula-1'
URL='https://cdn.shopify.com/s/files/1/0662/9749/5709/files/26TCF1_CHECKLIST.xlsx_-_Read-Only.pdf?v=1791482940'
PAGE='https://www.topps.com/pages/topps-chrome-formula-1'
VALUE='https://www.topps.com/products/2026-topps-chrome-formula-1%C2%AE-value-box'
def build():
 path=ROOT/'data/catalog-sources/downloads'/f'{SLUG}.pdf';acquire(URL,path);blob=path.read_bytes();rows=[];raw=[]
 with pdfplumber.open(path) as pdf:
  assert len(pdf.pages)==7
  for pn,page in enumerate(pdf.pages,1):
   raw.append({'page':pn,'text':page.extract_text()})
   for table in page.extract_tables():
    for r in table:
     assert len(r)==6;r=[v or '' for v in r]
     if r[0]=='Card Number':assert r==['Card Number','Name','Team','Subset','Rookie','1st Logo'];continue
     assert re.fullmatch(r'\d+|[A-Z0-9]+-[A-Z0-9]+',r[0]),r
     assert r[3] and (r[1] or r[2]),r
     rows.append([r[3],*r,str(pn)])
 assert len(rows)==604
 base=[r for r in rows if r[0].startswith('BASE CARDS')];assert sorted(int(r[1]) for r in base)==list(range(1,201))
 assert len([r for r in rows if not r[2]])==12
 assert next(r for r in rows if r[0]=='BASE CARDS - F1® DRIVERS' and r[1]=='12')[5]=='Rookie'
 assert next(r for r in rows if r[0]=='BASE CARDS - F2™ DRIVERS' and r[1]=='29')[6]=='1st Logo'
 specs=[{'name':'BASE CARDS','headers':['Parallel / variation','Published numbering','Manufacturer qualification','Official source'],'rows':[[n,'Numbered; exact value not stated','Product overview; individual-card eligibility is not guaranteed',PAGE] for n in ['Blue','Green','Purple','Gold','Orange','Black','Red']]+[['Refractors','Not stated','Product overview',PAGE],['Full Grid Refractors','# to 22','Featuring the current F1 driver line-up',PAGE],['SuperFractors','1/1','Product overview',PAGE],['Printing Plates','Not stated','Product overview',PAGE]]},{'name':'F1® DEBUT PATCH AUTOGRAPHS','headers':['Published card','Published numbering','Official source'],'rows':[["Arvid Lindblad's F1 Debut Patch Autograph",'1/1',PAGE]]},{'name':'Value box published contents','headers':['Published item','Published quantity / description','Basis','Official source'],'rows':[['Packs','7','Per box',VALUE],['Cards','4','Per pack',VALUE],['B&W RayWave Refractors','4','Per box',VALUE],['Refractors','2','Per box',VALUE],['Retail-exclusive inserts','2','Per box',VALUE],['Additional inserts','3','Per box',VALUE],['RayWave parallels','Exclusive content','Product description',VALUE],['Suit Up','Exclusive content','Product description',VALUE],['Home Straight','Exclusive content','Product description',VALUE],['Art Du Grand Prix','Returning design','Product description',VALUE]]}]
 payload={'title':'2026 Topps Chrome Formula 1','headers':['Checklist section','Card Number','Name','Team','Subset','Rookie','1st Logo','Source page'],'rows':rows,'source':URL,'sha256':hashlib.sha256(blob).hexdigest(),'importKind':'topps-grid-pdf','sectionColumn':0,'rawPages':raw,'publishedSpecifications':specs,'specificationSources':[PAGE,VALUE]}
 dest=f'data/imports/{SLUG}.json'
 r={'title':payload['title'],'manufacturer':'Topps / Bowman','sport':'racing','year':'2026','slug':SLUG,'page':f'sets/{SLUG}.html','sourcePage':PAGE,'checklistUrl':URL,'releaseStatus':'Upcoming','releaseDate':'2026-10-15','verified':'2026-10-11','status':'Source table','tableData':dest,'rowCount':604,'sections':len(set(row[0] for row in rows)),'parallelData':True,'publishedOdds':False,'importKind':'topps-grid-pdf','sha256':payload['sha256'],'catalogEvidence':'Official product pages announce October 15, 2026. The seven-page PDF publishes 604 card rows, including 12 intentionally blank Name cells (11 team-logo cards and card 150); original names, teams, subsets, rookie markers and first-logo markers remain intact. Product-page parallel numbering and value-box contents are separate from pack odds; individual parallel eligibility is not inferred. Pack-odds documents were not found on the product pages or global odds catalog.','dataAudit':'All six original PDF columns imported by ruled-cell boundaries; every base number 1–200 verified.'}
 payload,r=enrich(payload,r);(ROOT/dest).write_text(json.dumps(payload,ensure_ascii=False)+'\n')
 p=ROOT/'data/topps-product-official-catalog.json';inventory=json.loads(p.read_text());inventory=[{**x,**r} if x['slug']==SLUG else x for x in inventory] if any(x['slug']==SLUG for x in inventory) else inventory+[r];p.write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
 p=ROOT/'data/set-catalog.json';c=json.loads(p.read_text());c['sets']=[{**x,**r} if x['slug']==SLUG else x for x in c['sets']] if any(x['slug']==SLUG for x in c['sets']) else c['sets']+[r];p.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n');print('Imported 604 ruled F1 cards,',r['sections'],'sections, 174 literal odds categories / seven columns and five exact scoped guide joins.')
if __name__=='__main__':build()
