"""Backfill 2025-season MLS releases sold in 2026 from official physical fields."""
import json,re,hashlib,subprocess
from pathlib import Path
import pdfplumber
import import_official_catalog as generic
from import_topps_october_inventory import lines
ROOT=generic.ROOT;BASE='https://cdn.shopify.com/s/files/1/0662/9749/5709/files/'
CONFIG=[
 ('2025 Topps Chrome MLS','topps-bowman-2025-topps-chrome-mls','https://www.topps.com/products/topps-chrome-mls-2025-hobby-box','Topps_Chrome_MLS_2025_Checklist.pdf?v=1787962193','2025_MLS_Chrome_Odds.pdf?v=1787967049','2026-02-19'),
 ('2025 Topps Chrome MLS Sapphire Edition','topps-bowman-2025-topps-chrome-mls-sapphire-edition','https://www.topps.com/products/topps-chrome%C2%AE-mls-2025-sapphire-edition-hobby-box','CheckList_25MLSC_SAPPHIRE_1.pdf?v=1787963932','2026_Topps_MLS_Chrome_Sapphire_Odds.pdf?v=1787963938','2026-03-26')]
def acquire(url,path):
 subprocess.run(['curl','-sLf','--retry','2','--max-time','45',url,'-o',str(path)],check=True)
 path.with_suffix('.pdf.url').write_text(url)
 return hashlib.sha256(path.read_bytes()).hexdigest()
def parse_checklist(path):
 rows=[];raw=[];notes=[];section='Checklist'
 with pdfplumber.open(path) as pdf:
  for pn,page in enumerate(pdf.pages,1):
   raw.append({'page':pn,'text':page.extract_text()})
   for y,ws in lines(page):
    text=' '.join(w['text'] for w in ws)
    font=next(c['fontname'] for c in page.chars if abs(c['top']-ws[0]['top'])<.3 and abs(c['x0']-ws[0]['x0'])<.3)
    cols=[' '.join(w['text'] for w in ws if lo<=w['x0']<hi) for lo,hi in [(0,132),(132,284),(284,425),(425,page.width)]]
    if text in ['BASE','INSERT','AUTOGRAPH','RELIC','AUTOGRAPH-RELIC','HOBBY-EXCLUSIVE AUTOGRAPH-RELICS']:
     if 'EXCLUSIVE' in text:notes.append(['Official configuration heading',text,str(pn)])
    elif text.startswith('*'):notes.append([section,text,str(pn)])
    elif text.startswith('HOBBY-EXCLUSIVE'):notes.append(['Official configuration heading',text,str(pn)])
    elif 'Bold' in font or 'Italic' in font:section=text
    elif re.fullmatch(r'\d+|[A-Z0-9]+-[A-Z0-9]+',cols[0]):
     assert cols[3] in ('','Rookie'),(pn,cols)
     rows.append([section,*cols,str(pn)])
    elif text==text.upper() and ws[0]['x0']<100:
     section=text
    else:raise ValueError(('Unclassified physical checklist row',pn,text))
 assert [int(r[1]) for r in rows if r[0] in ('BASE CARDS','PITCH PRODIGIES')]==list(range(1,201))
 return rows,raw,notes
def build():
 catalog=json.loads((ROOT/'data/set-catalog.json').read_text());inventory=json.loads((ROOT/'data/topps-product-official-catalog.json').read_text());registry=json.loads((ROOT/'data/topps-official-odds.json').read_text())
 for title,slug,page,cl,od,date in CONFIG:
  cp=generic.CACHE/(slug+'.pdf');op=generic.CACHE/(slug+'-odds.pdf');ch=acquire(BASE+cl,cp);oh=acquire(BASE+od,op)
  rows,raw,notes=parse_checklist(cp);odds,formats,oraw,issues=generic.odds_pdf(op);assert not issues
  assert len(odds)==186 and len(formats)==5
  # The Sapphire download is a combined table whose title says 2026,
  # linked by the official 2025-season product. Preserve that discrepancy
  # and all five physical columns; only its Sapphire column is public here.
  odds=[{**o,'values':dict(zip(['Hobby','Value','Hanger','Mania','Sapphire'],o['values'].values()))} for o in odds]
  for odd in odds:
   if odd['name'].startswith('Base Cards ' ) or odd['name']=='Base Cards':odd.update(family='BASE CARDS',familyAliases=['PITCH PRODIGIES'])
   for prefix,family in [('Sapphire Selections Autograph Cards','SAPPHIRE SELECTIONS AUTOGRAPH VARIATION'),('Topps 1995 Autograph Cards','TOPPS 1995 AUTOGRAPH VARIATION'),('MLS Renaissance Autograph Cards','MLS RENAISSANCE AUTOGRAPHS')]:
    if odd['name'].startswith(prefix):odd['family']=family
  full=odds
  sapphire='Sapphire' in title
  if sapphire:
   odds=[{**o,'values':{'Sapphire':o['values']['Sapphire']}} for o in full if o['values']['Sapphire'] is not None];formats=['Sapphire']
   assert len(odds)==29
   notes.append(['Official odds document','The 2025-season product links a combined odds document titled 2026 Topps MLS Chrome Sapphire. All original columns are retained in officialOddsTable; this page shows the 29 categories with published Sapphire values. Other configurations are not assigned to this checklist.',''])
  else:formats=['Hobby','Value','Hanger','Mania','Sapphire']
  data={'title':title,'headers':['Checklist section','Card number','Name','Team','Rookie','Source page'],'rows':rows,'rawPages':raw,'sourceSheets':[{'name':'Official checklist and odds notes','notes':notes}],'source':BASE+cl,'sha256':ch,'importKind':'pdf','sectionColumn':0,'dedicatedParser':'scripts/import_topps_mls_2025.py','odds':odds,'formats':formats,'oddsSource':BASE+od,'oddsSha256':oh,'oddsRawPages':oraw,'oddsIssues':[]}
  if sapphire:data.update(officialOddsTable=full,officialOddsFormats=['Hobby','Value','Hanger','Mania','Sapphire'],oddsScope='Sapphire')
  dest='data/imports/'+slug+'.json';(ROOT/dest).write_text(json.dumps(data,ensure_ascii=False)+'\n')
  note='Official 2025-season product, sold in 2026. Store Product Year is 2026; checklist/season label is 2025. Physical Name, Team and Rookie cells are preserved. '+('The linked combined odds document is titled 2026; only literal Sapphire values are assigned to this page.' if sapphire else 'The official checklist spotlight independently states the February 19, 2026 release. The checklist explicitly excludes Lionel Messi from TOPPS 1995 Black Donut Holes /10; this card-specific exclusion is retained.')
  record={'title':title,'slug':slug,'page':'sets/'+slug+'.html','manufacturer':'Topps / Bowman','sport':'soccer','year':'2025','productYear':'2026','sourcePage':page,'checklistUrl':BASE+cl,'releaseStatus':'Released','releaseDate':date if not sapphire else None,'availableFrom':date,'releaseEvidence':'https://ripped.topps.com/topps-chrome-mls-2025-checklist/' if not sapphire else page,'verified':'2026-10-13','status':'Source table','tableData':dest,'rowCount':len(rows),'sections':len(set(r[0] for r in rows)),'importKind':'pdf','dedicatedParser':data['dedicatedParser'],'sha256':ch,'coverageComplete':False,'parallelData':True,'publishedOdds':True,'odds':len(odds),'formats':len(formats),'oddsUrl':BASE+od,'catalogEvidence':note,'dataAudit':'All physical columns and 200 base numbers reconciled. Published category values are retained; exhaustive parallel and numbering review remains pending.'}
  for items in [catalog['sets'],inventory]:
   old=next((r for r in items if r['slug']==slug),None)
   if old:old.update(record)
   else:items.append(record)
  registry[:]=[r for r in registry if r['title']!=title]+[{'title':title,'url':BASE+od}]
  print(title,len(rows),'rows',len(odds),'odds')
 for name,data in [('set-catalog.json',catalog),('topps-product-official-catalog.json',inventory),('topps-official-odds.json',registry)]:
  (ROOT/'data'/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':build()
